# Colab Evidence Lab Implementation Plan

> **For agentic workers:** Use subagent-driven-development for independent corpus and GraphRAG adapter tasks, with root-owned notebook assembly and final review.

**Goal:** Deliver a shareable Git project with a runnable offline notebook and opt-in Gemini GraphRAG experiment.

**Architecture:** A small Python package owns reproducible corpus preparation, graph inspection and retrieval adapters. The notebook composes those functions and separates key-free examples from live inference. Source snapshots and scientific provenance are versioned; credentials, caches and live run outputs are ignored.

**Tech Stack:** Python 3.11-3.13, GraphRAG 3.3.0, Gemini through LiteLLM, Jupyter/Colab, pandas, NetworkX, matplotlib and PyVis.

## Tasks

- [x] 1. Initialize standalone Git project and save approved design. Create package metadata, MIT license, ignore rules and dependency instructions. Verify `git status --short` and the package's Python range.
- [x] 2. Implement source manifest, bounded JATS parsing and deterministic document exports in `src/aurevion_knowledge_lab/corpus.py`. Download five CC-BY snapshots through Europe PMC. Test license rejection, ID mismatch, abstract/full-text selection and retained source hashes.
- [x] 3. Implement the pinned GraphRAG/Gemini adapter in `src/aurevion_knowledge_lab/graphrag_runner.py`. Validate configuration without a key or network call; test singular document-ID citation joins and explicit pipeline error handling.
- [x] 4. Implement source/decision graph inspection and question evaluation exports. Keep draft annotation status explicit and evaluation scores empty. Test missing-source references and stable artifact export.
- [x] 5. Assemble `notebooks/01_graphrag_colab.ipynb` with installation, persistent workspace, corpus inspection, key-free graph, opt-in credentials/smoke test/index/query comparison and export cells. Use `RUN_LIVE = False` by default.
- [x] 6. Run unit tests, dependency/config checks and execute the entire notebook with live inference disabled. Inspect the rendered graph asset, run independent review and repair findings.
- [x] 7. Write README with exact Colab/local instructions, architecture, evidence boundaries, verification results and Google subscription distinctions. Commit the completed project and provide the notebook and ZIP handoff. Publishing to GitHub remains a final reviewable action.

## Validation commands

```bash
python -m unittest discover -s tests -v
python scripts/validate_notebook.py
python scripts/run_offline_notebook.py
python scripts/package_colab.py
git status --short
```

Live API results must be reported as unverified unless a credentialed run actually succeeds. The offline demonstration must never be presented as model-generated evidence.
