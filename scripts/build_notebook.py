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
# Aurevion Knowledge Graph · Research lab

**Question:** Does graph-assisted retrieval make fitness and nutrition evidence easier to
trace and interpret than passage/vector retrieval?

**Hypothesis:** Explicit relationships may help connect interventions, populations and outcomes.
They may also add errors or cost. We compare both methods on the same small corpus.

**Workflow:** open the local project in VS Code and select a Google Colab kernel.
The kernel runs remotely; local files are not automatically synchronized. See
[VS Code + Colab](../docs/vscode-colab.md) for connection, upload and download steps.
Local Jupyter and browser Colab are alternatives.

The offline track uses **human-authored draft links**. The live track uses **unreviewed Gemini
outputs**. Five historical papers test the pipeline; they do not establish current guidance or
personal prescriptions.

**Lab outline**

1. [Connect the project](#1-connect-the-project)
2. [Choose the experiment](#2-choose-the-experiment)
3. [Inspect the corpus](#3-inspect-the-corpus)
4. [Explore draft decision links](#4-explore-draft-decision-links)
5. [Prepare evaluation](#5-prepare-evaluation)
6. [Probe model access](#6-probe-model-access)
7. [Build the extracted graph](#7-build-the-extracted-graph)
8. [Compare retrieval](#8-compare-retrieval)
9. [Export and review](#9-export-and-review)
""")
md("""
<a id="1-connect-the-project"></a>
## 1 · Connect the project

**Purpose:** locate source files and install GraphRAG 3.3.0 with Python 3.11–3.13.
**Checkpoint:** the cell prints the project path and dependency version.
**Interpretation:** `/content/...` is the remote runtime; a local path is local execution.

A fresh Colab runtime clones the public repository. For unpublished source, use VS Code
**Upload to Colab** in a fresh runtime, then set `PROJECT_BUNDLE` to the uploaded ZIP path. Browser Colab's
Files panel is another upload route. Build the ZIP with `python scripts/package_colab.py`.
Clear `PROJECT_BUNDLE` after extraction, including before rerunning after a kernel restart.

For local edits already committed and pushed, opt into `PULL_RUNTIME_SOURCE`; it allows only a
clean, fast-forward runtime update. Restart the kernel if source or loaded dependencies change.
""")
code('''
import sys, os, json, subprocess, zipfile, stat
from pathlib import Path

REPOSITORY_URL = "https://github.com/Demetri65/aurevion-knowledge-graph.git"
PROJECT_BUNDLE = None  # Example: '/content/aurevion-knowledge-graph-colab.zip' after manual upload.
PULL_RUNTIME_SOURCE = False  # Remote clone only; local changes must first be committed and pushed.
RUNTIME_PROJECT = Path('/content/aurevion-knowledge-graph')
IS_COLAB_RUNTIME = Path('/content').is_dir()

if not (3, 11) <= sys.version_info[:2] < (3, 14):
    raise RuntimeError("Select a Python 3.11–3.13 kernel before installing GraphRAG 3.3.0.")

def find_project():
    for candidate in [Path.cwd(), *Path.cwd().parents, RUNTIME_PROJECT]:
        if (candidate / 'pyproject.toml').is_file() and (candidate / 'corpus/manifest.jsonl').is_file():
            return candidate.resolve()

PROJECT_ROOT = find_project()
if PROJECT_BUNDLE and PROJECT_ROOT is not None:
    raise RuntimeError('PROJECT_BUNDLE cannot replace an existing checkout. Use a fresh runtime for new source, or clear it to reuse the existing source.')
if PROJECT_ROOT is None and PROJECT_BUNDLE:
    if not IS_COLAB_RUNTIME:
        raise RuntimeError('Extract the project locally, then open its folder in VS Code or Jupyter.')
    archive_path = Path(PROJECT_BUNDLE)
    if not archive_path.is_file():
        raise FileNotFoundError('Upload the project ZIP to the runtime before setting PROJECT_BUNDLE.')
    with zipfile.ZipFile(archive_path) as archive:
        if sum(item.file_size for item in archive.infolist()) > 15_000_000:
            raise ValueError('Project archive exceeds the 15 MB limit.')
        for item in archive.infolist():
            target = (Path('/content') / item.filename).resolve()
            if not target.is_relative_to(RUNTIME_PROJECT) or stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError('Unexpected archive path or symbolic link.')
        archive.extractall('/content')
    PROJECT_ROOT = find_project()
if PROJECT_ROOT is None and IS_COLAB_RUNTIME and REPOSITORY_URL:
    from urllib.parse import urlparse
    parsed = urlparse(REPOSITORY_URL)
    if parsed.scheme != 'https' or parsed.netloc != 'github.com' or parsed.query or parsed.fragment:
        raise ValueError('Use a plain HTTPS GitHub repository URL.')
    subprocess.run(['git', 'clone', '--depth', '1', REPOSITORY_URL, str(RUNTIME_PROJECT)], check=True)
    PROJECT_ROOT = find_project()
if PROJECT_ROOT is None:
    raise RuntimeError('Open the local project folder, or clone/upload it into the Colab runtime. See docs/vscode-colab.md.')

if PULL_RUNTIME_SOURCE:
    if not IS_COLAB_RUNTIME or not (PROJECT_ROOT / '.git').is_dir():
        raise RuntimeError('PULL_RUNTIME_SOURCE requires a Git clone in the Colab runtime.')
    dirty = subprocess.check_output(['git', '-C', str(PROJECT_ROOT), 'status', '--porcelain'], text=True)
    if dirty.strip():
        raise RuntimeError('The runtime clone has local changes. Preserve them before pulling; no files were discarded.')
    before = subprocess.check_output(['git', '-C', str(PROJECT_ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    subprocess.run(['git', '-C', str(PROJECT_ROOT), 'pull', '--ff-only'], check=True)
    after = subprocess.check_output(['git', '-C', str(PROJECT_ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    if before != after and any(name.startswith('aurevion_knowledge_lab') for name in sys.modules):
        raise RuntimeError('Runtime source updated. Restart the kernel and rerun from section 1 to load it.')

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
            raise RuntimeError('Dependencies changed. Restart the kernel, then rerun from section 1.')
sys.path.insert(0, str(PROJECT_ROOT / 'src'))
source_commit = 'source_bundle_without_git_metadata'
if (PROJECT_ROOT / '.git').exists():
    head = subprocess.run(['git', '-C', str(PROJECT_ROOT), 'rev-parse', 'HEAD'], capture_output=True, text=True)
    source_commit = head.stdout.strip() if head.returncode == 0 else 'uncommitted_initial_project'
print({'project': str(PROJECT_ROOT), 'source_commit': source_commit,
       'python': sys.version.split()[0], 'graphrag': version('graphrag')})
''')
md("""
<a id="2-choose-the-experiment"></a>
## 2 · Choose the experiment

**Purpose:** fix the corpus, models and workspace before comparing retrieval.
**Checkpoint:** live inference is disabled; two abstracts are selected.
**Interpretation:** this is a bounded starting point, not full-literature coverage.

Keep `RUN_LIVE = False` for a key-free Run All. Enable it only after checking project quota and
billing in [Google setup](../docs/google-setup.md). Full-text mode retains headings, excludes the
bibliography and records truncation. Drive persistence is optional and may need browser authorization.
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
    WORKSPACE = Path('/content/drive/MyDrive/aurevion-knowledge-graph/runs')
WORKSPACE.mkdir(parents=True, exist_ok=True)
print({'live_inference': RUN_LIVE, 'content_mode': CONTENT_MODE, 'documents': MAX_DOCUMENTS})
''')
md("""
<a id="3-inspect-the-corpus"></a>
## 3 · Inspect the corpus

**Purpose:** inspect licensed papers and the exact text selected for this run.
**Checkpoint:** source IDs, CC-BY licenses, hashes and truncation status are visible.
**Interpretation:** an abstract supports less detail than a full-text study; retain that limit.

Europe PMC snapshots are cached. `fetch_corpus` can refresh them deliberately; it does not run here.
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
<a id="4-explore-draft-decision-links"></a>
## 4 · Explore draft decision links

**Purpose:** inspect how research, claims and proposed product decisions could connect.
**Checkpoint:** a graph and the decisions affected by a changed source appear.
**Interpretation:** these links are human-authored examples, not generated or approved evidence.

Blue = paper; gray = topic; amber = draft claim; purple = population; orange = proposed decision.
`SOURCE_TO_REVIEW` marks a candidate link. This demo includes all five papers; the live corpus uses the
selection from section 2. Click a node to inspect its status.
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
<a id="5-prepare-evaluation"></a>
## 5 · Prepare evaluation

**Purpose:** define useful questions before inspecting model answers.
**Checkpoint:** coverage flags appear; scores remain empty.
**Interpretation:** missing sources or full text are corpus limits, not necessarily retrieval failures.

Assess passage fidelity, citation traceability and population fit using the
[evaluation guide](../docs/evaluation-guide.md). Model confidence is not scientific certainty.
""")
code('''
questions = [json.loads(line) for line in (PROJECT_ROOT / 'evaluations/questions.jsonl').read_text().splitlines() if line.strip()]
evaluation = evaluation_rows(questions, {d['id'] for d in documents}, CONTENT_MODE)
display(pd.DataFrame(evaluation)[['id', 'question', 'corpus_covered', 'mode_covered']])
write_json(WORKSPACE / 'demo' / 'evaluation-unscored.json', evaluation)
''')
md("""
<a id="6-probe-model-access"></a>
## 6 · Probe model access

**Purpose:** validate configuration, then test model access only when live execution is enabled.
**Checkpoint:** offline runs print a skip; live runs must pass schema, exact-quote and embedding checks.
**Interpretation:** the tiny probe establishes format/access compatibility, not extraction quality.

Credentials are read from the environment, then Colab Secrets, then a **masked runtime prompt**.
The key is never printed or saved. Do not display `config`. Set Colab secret notebook access if using it.
Smoke probes bypass response caching; index responses are cached. Usage estimates are not spend limits
or billing records. See [Google setup](../docs/google-setup.md).
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
            api_key = None
    if not api_key:
        import getpass, warnings
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', getpass.GetPassWarning)
                api_key = getpass.getpass('Gemini API key (runtime only): ')
        except (getpass.GetPassWarning, EOFError):
            raise RuntimeError('This kernel cannot mask input. Use GEMINI_API_KEY in the environment or Colab Secrets.') from None
    if not api_key or not api_key.strip():
        raise RuntimeError('No Gemini API key was supplied; indexing has not started.')
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
<a id="7-build-the-extracted-graph"></a>
## 7 · Build the extracted graph

**Purpose:** extract semantic relationships with Standard GraphRAG.
**Checkpoint:** six table row counts and an extracted graph appear after a successful live run.
**Interpretation:** generated relationships and community summaries still require evidence review.

This run uses one concurrent request and no extra gleanings. Partial runs are not marked complete.
Matching completed indexes can be reused; `REUSE_COMPLETED_INDEX = False` forces a checked rebuild.
Use persistent storage before indexing if you want to retain results across remote sessions.
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
<a id="8-compare-retrieval"></a>
## 8 · Compare retrieval

**Purpose:** ask one question through both methods using the same documents and completion model.
**Checkpoint:** basic/vector and local/graph answers appear with passages and marker-to-paper paths.
**Interpretation:** inspect which answer is faithful and useful; no winner is assumed.

Retrieved context and generated `[Data: ...]` markers are separate. Resolved IDs establish provenance,
not claim correctness. Derived community summaries are labeled; unresolved IDs remain visible.
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
<a id="9-export-and-review"></a>
## 9 · Export and review

**Purpose:** save reproducible artifacts for inspection and deliberate scoring.
**Checkpoint:** the cell prints the export ZIP path and its offline/live status.
**Interpretation:** evaluations remain unscored; live answers are unreviewed.

For a remote VS Code kernel, use the Colab extension's **Contents** view to download the ZIP.
Browser Colab's Files panel is an alternative. A local kernel writes into this project's `runs/` folder.
Raw caches, logs and keys are excluded. Keep source attributions; review live outputs before sharing.
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
if IS_COLAB_RUNTIME:
    print('Download this ZIP through the Colab extension Contents view or browser Colab Files panel.')
else:
    print('The ZIP is available in the local runs folder.')
''')
md("""
### Record the finding

- Which covered questions benefited from graph context?
- Did each cited passage support its claim and studied population?
- Were the added extraction cost and complexity useful for those questions?

Keep scores empty until reviewed. Current-literature coverage, approved policies and Aurevion
integration require separate work. The future API boundary is `apps/api/app/features/evidence_knowledge`.
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
