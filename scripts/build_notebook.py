"""Build the source notebook with deterministic cell IDs and no live outputs."""

from pathlib import Path
import hashlib
import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
cells = []


def md(text):
    cells.append(nbf.v4.new_markdown_cell(text.strip()))


def code(text):
    cells.append(nbf.v4.new_code_cell(text.strip()))


md("""
# Aurevion Knowledge Graph
### Research passages → evidence context → reviewable product decisions

An inspectable experiment with **Microsoft GraphRAG + Gemini**, built for Colab and Jupyter.

**Two distinct tracks:** the key-free walkthrough uses licensed papers and clearly labelled,
human-authored draft links. The live track extracts a graph with Gemini and compares graph-assisted
retrieval against a passage/vector baseline. Model outputs remain unreviewed.

The five-paper corpus is a **historical pipeline test set**, not a current comprehensive review.
This project does not supply personal medical or nutritional prescriptions.

**Start here:** open this notebook in Colab; cell 1 loads the public project repository.
Alternatively, clear `REPOSITORY_URL` and upload the supplied project ZIP when prompted. Locally, start Jupyter
from the cloned project. See `README.md`, `docs/google-setup.md` and `docs/evaluation-guide.md`.
""")
md("""
## 1 · Load the project and install its pinned GraphRAG release

The notebook uses Python **3.11–3.13**. The project source is separate from Colab's runtime.
The ZIP contains the notebook, source code, licensed article snapshots and evaluation questions;
it excludes credentials and run caches. Package installation can take several minutes.
""")
code('''
import sys, os, json, subprocess, zipfile, stat
from pathlib import Path

REPOSITORY_URL = "https://github.com/Demetri65/aurevion-knowledge-graph.git"
if not (3, 11) <= sys.version_info[:2] < (3, 14):
    raise RuntimeError("Select a Python 3.11–3.13 runtime before installing GraphRAG 3.3.0.")

def find_project():
    for candidate in [Path.cwd(), *Path.cwd().parents, Path('/content/aurevion-knowledge-lab')]:
        if (candidate / 'pyproject.toml').is_file() and (candidate / 'corpus/manifest.jsonl').is_file():
            return candidate.resolve()

PROJECT_ROOT = find_project()
if PROJECT_ROOT is None and REPOSITORY_URL:
    from urllib.parse import urlparse
    parsed = urlparse(REPOSITORY_URL)
    if parsed.scheme != 'https' or parsed.netloc != 'github.com' or parsed.query or parsed.fragment:
        raise ValueError('Use a plain HTTPS GitHub repository URL.')
    subprocess.run(['git', 'clone', '--depth', '1', REPOSITORY_URL, '/content/aurevion-knowledge-lab'], check=True)
    PROJECT_ROOT = find_project()
if PROJECT_ROOT is None:
    try:
        from google.colab import files
    except ImportError:
        raise RuntimeError('Start Jupyter from the project directory, or use the Colab ZIP workflow.') from None
    print('Upload aurevion-knowledge-lab-colab.zip (the project bundle).')
    uploaded = files.upload()
    archives = [name for name in uploaded if name.endswith('.zip')]
    if len(archives) != 1:
        raise ValueError('Upload exactly one project ZIP.')
    destination = Path('/content').resolve()
    with zipfile.ZipFile(archives[0]) as archive:
        if sum(item.file_size for item in archive.infolist()) > 15_000_000:
            raise ValueError('Project archive exceeds the 15 MB limit.')
        for item in archive.infolist():
            target = (destination / item.filename).resolve()
            if not target.is_relative_to(destination / 'aurevion-knowledge-lab') or stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError('Unexpected archive path or symbolic link.')
        archive.extractall(destination)
    PROJECT_ROOT = find_project()
if PROJECT_ROOT is None:
    raise RuntimeError('The project bundle did not contain the expected source files.')

from importlib.metadata import version, PackageNotFoundError
try:
    installed = version('graphrag') == '3.3.0' and version('aurevion-knowledge-lab') == '0.1.0'
except PackageNotFoundError:
    installed = False
if not installed:
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '-e', str(PROJECT_ROOT)], check=True)
    for dependency in ['numpy', 'pandas', 'pydantic']:
        loaded = sys.modules.get(dependency)
        if loaded is not None and getattr(loaded, '__version__', None) != version(dependency):
            raise RuntimeError('Dependencies changed. Restart the Colab session, then rerun from cell 1.')
sys.path.insert(0, str(PROJECT_ROOT / 'src'))
print({'project': str(PROJECT_ROOT), 'python': sys.version.split()[0], 'graphrag': version('graphrag')})
''')
md("""
## 2 · Configure a bounded experiment

Defaults use **two abstracts**, one inexpensive completion model and one embedding model.
`RUN_LIVE = False` keeps Run All key-free. Enable the live track only after checking the API
project's quota/billing. Google AI Pro's AI Studio quota is distinct from notebook API quota;
eligible Cloud credits may help. See the linked setup guide for current subscription details.

To expand, change the corpus settings deliberately and rerun from this cell.
Full-text mode retains section headings and excludes the bibliography. Truncation is recorded.
""")
code('''
RUN_LIVE = False
CONTENT_MODE = 'abstract'  # 'abstract' or 'full_text'
MAX_DOCUMENTS = 2
MAX_CHARS_PER_DOCUMENT = 12_000
COMPLETION_MODEL = 'gemini-3.1-flash-lite'
EMBEDDING_MODEL = 'gemini-embedding-001'
PERSIST_TO_DRIVE = False  # Enable to keep index/cache/output across Colab sessions.
REUSE_COMPLETED_INDEX = True

WORKSPACE = PROJECT_ROOT / 'runs'
if PERSIST_TO_DRIVE:
    from google.colab import drive
    drive.mount('/content/drive')
    WORKSPACE = Path('/content/drive/MyDrive/aurevion-knowledge-lab/runs')
WORKSPACE.mkdir(parents=True, exist_ok=True)
print({'live_inference': RUN_LIVE, 'content_mode': CONTENT_MODE, 'documents': MAX_DOCUMENTS})
''')
md("""
## 3 · Inspect sources and provenance

All five snapshots came from Europe PMC's permitted full-text XML API and carry explicit CC-BY
licenses. Source IDs and license statements are validated before preparation. `fetch_corpus`
can refresh the cached sources; it is deliberately separate from this offline walkthrough.
""")
code('''
import pandas as pd
from IPython.display import display, HTML
from aurevion_knowledge_lab.corpus import load_manifest, prepare_documents, fetch_corpus
from aurevion_knowledge_lab.artifacts import example_graph, graph_from_index, write_interactive_graph, write_json, evaluation_rows, impacted_decisions

manifest = load_manifest(PROJECT_ROOT)
display(pd.DataFrame(manifest)[['id', 'year', 'title', 'license', 'source_url']])
documents = prepare_documents(PROJECT_ROOT, content_mode=CONTENT_MODE,
                              max_documents=MAX_DOCUMENTS, max_chars_per_document=MAX_CHARS_PER_DOCUMENT)
display(pd.DataFrame(documents)[['id', 'content_mode', 'char_count', 'truncated', 'sha256']])
print('First prepared passage:')
print(documents[0]['text'][:1200])
# Optional refresh: fetch_corpus(PROJECT_ROOT, refresh=True)
''')
md("""
## 4 · Explore a source-to-decision graph without an API key

Blue nodes are papers; gray nodes are topic tags; amber nodes are draft claims; purple nodes
retain population context; orange nodes are proposed product decisions.

**This is a human-authored demonstration.** `SOURCE_TO_REVIEW` means a proposed evidence link,
not verified scientific support. The demo uses metadata from all five papers even when the live
index selects only two abstracts. Inspect a node to see its status. Scientific appraisal and
product approval are separate future review steps.
""")
code('''
annotations = json.loads((PROJECT_ROOT / 'decisions/examples.json').read_text())
demo_graph = example_graph(manifest, annotations)
demo_path = write_interactive_graph(demo_graph, WORKSPACE / 'demo' / 'evidence-graph.html')
write_json(WORKSPACE / 'demo' / 'graph.json', demo_graph)
print({'status': demo_graph['status'], 'nodes': len(demo_graph['nodes']), 'edges': len(demo_graph['edges'])})
display(HTML(demo_path.read_text()))
display(pd.DataFrame(annotations['decisions'])[['title', 'status', 'rationale']])
print('If PMC3879660 changes, these explicit draft dependencies need review:')
display(pd.DataFrame(impacted_decisions(demo_graph, 'PMC3879660')))
''')
md("""
## 5 · Prepare an honest evaluation sheet

Scores start empty. Coverage checks distinguish an absent source or missing full text from a
retrieval failure. Compare fidelity to passages, citation traceability, population fit and useful
question coverage. The guide explains each measure; do not convert model confidence into
scientific certainty.
""")
code('''
questions = [json.loads(line) for line in (PROJECT_ROOT / 'evaluations/questions.jsonl').read_text().splitlines() if line.strip()]
evaluation = evaluation_rows(questions, {d['id'] for d in documents}, CONTENT_MODE)
display(pd.DataFrame(evaluation)[['id', 'question', 'corpus_covered', 'mode_covered']])
write_json(WORKSPACE / 'demo' / 'evaluation-unscored.json', evaluation)
''')
md("""
## 6 · Validate configuration; opt into credentials and model probes

Add `GEMINI_API_KEY` to **Colab Secrets** (key icon) and grant this notebook access. Locally,
provide it through an environment variable. The key is never printed, saved in the notebook,
or included in exported configuration. Key-free runs still validate the pinned configuration.

The live probe tests one small structured response and one embedding. Passing it verifies
basic provider compatibility, not scientific extraction quality. Successful LiteLLM callbacks
record usage without retaining prompts. Cost estimates do not enforce a hard spend ceiling or
account for promotional credits; provider billing remains the authoritative record.
""")
code('''
import hashlib
from aurevion_knowledge_lab.graphrag_runner import make_config, smoke_test, build_graph, load_index, ask
from aurevion_knowledge_lab.usage import install_usage_ledger

experiment = {'version': 1, 'graphrag': '3.3.0', 'completion_model': COMPLETION_MODEL,
              'embedding_model': EMBEDDING_MODEL, 'content_mode': CONTENT_MODE,
              'documents': [{'id': d['id'], 'sha256': d['sha256'], 'text_sha256': hashlib.sha256(d['text'].encode()).hexdigest()} for d in documents]}
if (PROJECT_ROOT / '.git').exists():
    experiment['source_commit'] = subprocess.check_output(['git', '-C', str(PROJECT_ROOT), 'rev-parse', 'HEAD'], text=True).strip() if subprocess.run(['git', '-C', str(PROJECT_ROOT), 'rev-parse', '--verify', 'HEAD'], capture_output=True).returncode == 0 else 'uncommitted_initial_project'
else:
    experiment['source_commit'] = 'source_zip_without_git_metadata'
fingerprint = hashlib.sha256(json.dumps(experiment, sort_keys=True).encode()).hexdigest()[:16]
RUN_DIR = WORKSPACE / fingerprint
RUN_DIR.mkdir(parents=True, exist_ok=True)
config = make_config(RUN_DIR, api_key='not-configured', completion_model=COMPLETION_MODEL, embedding_model=EMBEDDING_MODEL)
smoke_ok = False
ledger = None
tables = None
answers = {}
print({'config_valid': True, 'run_fingerprint': fingerprint, 'live_inference': RUN_LIVE})
if RUN_LIVE:
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        try:
            from google.colab import userdata
            api_key = userdata.get('GEMINI_API_KEY')
        except Exception:
            raise RuntimeError('Add GEMINI_API_KEY to Colab Secrets or the local environment.') from None
    if not api_key:
        raise RuntimeError('GEMINI_API_KEY is empty.')
    config = make_config(RUN_DIR, api_key, COMPLETION_MODEL, EMBEDDING_MODEL)
    del api_key
    ledger = install_usage_ledger()
    probe = await smoke_test(config)
    display(probe)
    smoke_ok = probe['ok']
    if not smoke_ok:
        raise RuntimeError('Provider smoke test failed; indexing has not started.')
else:
    print('Live probes skipped. Demo outputs remain human-authored; Gemini compatibility is unverified.')
''')
md("""
## 7 · Build the actual extracted graph

Standard GraphRAG extracts entities and relationship descriptions and writes community reports.
The lower-cost Fast mode creates co-occurrence links and is a different experiment. This run
uses Standard with one concurrent request and no extra extraction gleanings. Each pipeline
result is checked; a partial run is not marked complete.

API responses are cached within the run directory. Reuse applies only to this corpus/model
fingerprint. Move the workspace to Drive before live indexing to preserve it across sessions.
""")
code('''
if RUN_LIVE and smoke_ok:
    completed = RUN_DIR / 'completed.json'
    tables = None
    answers = {}
    if REUSE_COMPLETED_INDEX and completed.is_file():
        saved = json.loads(completed.read_text())
        if saved['experiment'] != experiment:
            raise RuntimeError('Completed-index metadata differs from this experiment.')
        tables = load_index(config)
        print('Loaded matching completed index.')
    else:
        completed.unlink(missing_ok=True)
        write_json(RUN_DIR / 'experiment.json', experiment)
        tables = await build_graph(config, documents)
        write_json(completed, {'experiment': experiment, 'status': 'index_completed'})
    display(pd.DataFrame([{'table': name, 'rows': len(table)} for name, table in tables.items()]))
    extracted_graph = graph_from_index(tables)
    extracted_path = write_interactive_graph(extracted_graph, RUN_DIR / 'extracted-graph.html')
    display(HTML(extracted_path.read_text()))
    write_json(RUN_DIR / 'extracted-graph.json', extracted_graph)
else:
    print('GraphRAG indexing skipped. Enable RUN_LIVE and pass the provider probes to generate a graph.')
''')
md("""
## 8 · Ask the same question through passage/vector and graph retrieval

Both methods use the same prepared documents and completion model. Basic search is the
passage/vector baseline; local search adds graph context. The comparison is inspectable, not
an automatic claim that one method wins.

Generated `[Data: ...]` markers are displayed separately from retrieved context. A retrieved
passage is not automatically a citation used by the answer. Text-unit IDs are resolved back
to document IDs and source metadata so you can inspect the original paper.
""")
code('''
QUESTION = 'What do the included sources say about protein timing versus total protein intake, and what limits those conclusions?'
if RUN_LIVE and tables is not None:
    for method in ['basic', 'local']:
        result = await ask(config, tables, QUESTION, method=method)
        answers[method] = result
        print(f'\\n{method.upper()} ANSWER\\n{result["answer"]}')
        display(pd.DataFrame(result['retrieved_source_context']))
        print('Generated markers:', result['citation_markers'])
        print('Marker-to-paper provenance (resolution does not verify claim correctness):')
        display(pd.DataFrame(result['resolved_citation_markers']))
        write_json(RUN_DIR / f'{method}-answer.json', result)
else:
    print('Live question answering skipped. No generated answer or performance score is claimed.')
''')
md("""
## 9 · Export reproducible artifacts and review results

Export files contain source metadata, graph records, answers/context and an unscored evaluation
sheet. Fill scores only after inspecting passages. Keep source XML attributions when sharing.
The project bundle and key-free demo can be shared immediately; live outputs should be reviewed
before publication. Raw model cache/logs stay private and are not included in the export ZIP.

To evaluate more questions, select covered rows from `evaluation`, run both methods, and record
the results deliberately. Avoid an unbounded batch while exploring a free API quota.
""")
code('''
from datetime import datetime, timezone
import shutil
export_dir = RUN_DIR / 'exports' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
export_dir.mkdir(parents=True)
write_json(export_dir / 'source-manifest.json', manifest)
write_json(export_dir / 'prepared-document-provenance.json', [{k: v for k, v in d.items() if k not in ['text', 'raw_data']} for d in documents])
write_json(export_dir / 'experiment.json', experiment)
write_json(export_dir / 'draft-decision-graph.json', demo_graph)
write_json(export_dir / 'evaluation-unscored.json', evaluation)
write_json(export_dir / 'answers.json', answers)
shutil.copyfile(demo_path, export_dir / 'draft-graph.html')
shutil.copyfile(PROJECT_ROOT / 'corpus/README.md', export_dir / 'source-attribution.md')
if ledger is not None:
    # Give asynchronous usage callbacks a moment to settle before taking a snapshot.
    import asyncio
    await asyncio.sleep(0.2)
    usage = {'summary': ledger.summary(), 'requests': ledger.records}
    write_json(export_dir / 'usage.json', usage)
    display(usage['summary'])
if tables is not None:
    for name, table in tables.items():
        table.to_parquet(export_dir / f'{name}.parquet', index=False)
    write_json(export_dir / 'extracted-graph.json', extracted_graph)
    shutil.copyfile(extracted_path, export_dir / 'extracted-graph.html')
    status = 'live_index_completed_answers_unreviewed'
else:
    status = 'offline_demo_verified_live_inference_not_run'
write_json(export_dir / 'status.json', {'status': status, 'evaluation_scored': False})
bundle = RUN_DIR / 'research-artifacts.zip'
with zipfile.ZipFile(bundle, 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(export_dir.iterdir()):
        archive.write(path, arcname=path.name)
print({'status': status, 'export': str(bundle)})
if 'google.colab' in sys.modules:
    from google.colab import files
    print('Download with: files.download(str(bundle))')
''')
md("""
## What this experiment establishes

- Source identity, licensing, reproducible preparation and graph inspection can be tested without credentials.
- A credentialed run can establish whether the selected Gemini models work with this GraphRAG release.
- Comparing answers and tracing citations can reveal whether graph context improves the selected tasks.
- Research appraisal, current-literature coverage, claim approval and production Aurevion integration remain separate work.

Future integration targets the refactored `apps/api/app/features/evidence_knowledge` boundary.
Keep the experiment's portable records and evaluation evidence; promote only behavior that has been reviewed.
""")

for index, cell in enumerate(cells):
    cell['id'] = f"lab-{index:02d}-{hashlib.sha256(cell['source'].encode()).hexdigest()[:8]}"
notebook = nbf.v4.new_notebook(cells=cells, metadata={
    'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
    'language_info': {'name': 'python', 'version': '3.12'},
    'colab': {'name': '01_graphrag_colab.ipynb', 'provenance': []},
})
nbf.write(notebook, ROOT / 'notebooks/01_graphrag_colab.ipynb')
print(f'Built {len(cells)} cells.')
