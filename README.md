# Aurevion Knowledge Graph

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Demetri65/aurevion-knowledge-graph/blob/main/notebooks/01_graphrag_colab.ipynb)
[![Offline checks](https://github.com/Demetri65/aurevion-knowledge-graph/actions/workflows/verify.yml/badge.svg)](https://github.com/Demetri65/aurevion-knowledge-graph/actions/workflows/verify.yml)

**Research passages → evidence context → reviewable product decisions.**

This standalone lab asks whether Microsoft GraphRAG adds useful context when inspecting fitness and nutrition research. Start with a key-free walkthrough, then opt into Gemini indexing and compare passage retrieval with graph-assisted retrieval.

## Start in VS Code

1. Open the local `aurevion-knowledge-graph` folder in VS Code and install the recommended **Google Colab** extension.
2. Open [`notebooks/01_graphrag_colab.ipynb`](notebooks/01_graphrag_colab.ipynb).
3. Choose **Select Kernel → Colab → Auto Connect**, or **New Colab Server** with a CPU runtime. This lab needs no GPU.
4. Keep `RUN_LIVE = False` and run the notebook from the top. If installation changes loaded dependencies, restart the kernel and rerun from the top.
5. Inspect the sources, draft graph, coverage sheet and export ZIP before enabling live inference.

Your notebook edits stay local; the Colab kernel executes on Google's runtime. See [the VS Code workflow](docs/vscode-colab.md) for source refresh, credentials and runtime files. The badge above opens the same lab in browser Colab.

## The lab

| Track | What it demonstrates |
|---|---|
| Key-free | Five licensed source snapshots, provenance checks, a human-authored draft decision graph and ten unscored evaluation questions |
| Live, opt-in | Gemini completion/embedding probes, Standard GraphRAG indexing, basic/local query comparison and citation-to-paper inspection |

Live defaults use **two abstracts**, GraphRAG **3.3.0**, `gemini-3.1-flash-lite`, `gemini-embedding-001`, one concurrent request, response caching and no extraction gleanings. Check your API project's quota and billing before setting `RUN_LIVE = True`. A Google AI Pro subscription does not automatically supply notebook API quota; [Google setup](docs/google-setup.md) explains the distinction.

Basic search retrieves passages through vectors. Local search adds extracted entities and relationships. Both query the same prepared documents. Generated citation markers and retrieved context are shown separately; resolving a marker to a paper still requires checking whether its passage supports the claim.

![Human-authored demonstration of research-to-decision traceability](assets/evidence-graph.png)

This preview is a **human-authored demonstration**, not a generated GraphRAG result. Decision links remain draft examples. Evaluation scores start empty, and no retrieval advantage or clinical benefit is claimed.

## Files and guides

| Path | Purpose |
|---|---|
| [Notebook](notebooks/01_graphrag_colab.ipynb) | Guided experiment and portable JSON, Parquet, HTML and ZIP exports |
| [Lab notes](docs/lab-notes.md) | Questions, observations and next experiments |
| [VS Code + Colab](docs/vscode-colab.md) | Local editing, remote execution and iteration |
| [Google setup](docs/google-setup.md) | Models, API access and credentials |
| [Evaluation guide](docs/evaluation-guide.md) | Coverage checks, citation review and scoring |
| [Corpus](corpus/README.md) | Source attribution, licenses and preparation |
| [Verification](docs/verification.md) | Recorded checks and remaining evidence |
| `src/aurevion_knowledge_lab/` | Corpus, GraphRAG adapter and artifact helpers |
| `decisions/examples.json` | Explicit human-authored claim and decision links |

`scripts/build_notebook.py` generates the output-free source notebook. Update this generator when changing the lab, then rebuild the notebook. Runtime outputs and caches belong under ignored `runs/`; source bundles are built with `python scripts/package_colab.py`. The internal Python package retains the name `aurevion-knowledge-lab`.

## Local checks

Use Python **3.11–3.13**; the pinned GraphRAG release excludes 3.14.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
python scripts/validate_notebook.py
python scripts/run_offline_notebook.py
```

To use a local kernel instead, select this environment in VS Code, or install JupyterLab and run `python -m jupyterlab notebooks/01_graphrag_colab.ipynb`. The notebook runner writes its executed copy under `runs/`.

## Status and boundaries

- **Verified:** local source/configuration/adapter checks and the complete key-free notebook; the key-free track also ran in browser Colab on CPU. Details are in [the verification record](docs/verification.md).
- **Pending:** execution through the VS Code Colab extension, credentialed Gemini probes, live indexing/queries and scored retrieval comparisons.
- **Scope:** five papers from 2013–2018 form a historical pipeline test corpus. They do not establish current scientific consensus or approve Aurevion policies.

The lab is independent of Aurevion's application dependencies. Future integration at `apps/api/app/features/evidence_knowledge` should consume reviewed records and evaluated retrieval behavior in a separate pass.

Original code is MIT licensed. Article XML retains its individual CC-BY license. Preserve attribution, license links and transformation notices when sharing derived material.
