# Colab Evidence Lab

Approved direction: the user approved the standalone notebook experiment in chat on 2026-10-11 and requested a Git project suitable for sharing.

The user subsequently authorized public GitHub publication as `Demetri65/aurevion-knowledge-graph`.

## Purpose

Investigate whether Microsoft GraphRAG helps connect fitness and nutrition research to reviewable product decisions. Keep the experiment independent of Aurevion's active `codex/tokens-grid` refactor.

## Scope

- A reproducible Colab/Jupyter notebook, local Python package, Git history, project README and license.
- Five attributed, CC-BY research articles fetched through Europe PMC's permitted full-text XML API, with cached source snapshots.
- A key-free walkthrough of source metadata, draft annotations and decision links. Label these as human-authored examples, never generated GraphRAG results.
- An opt-in Gemini smoke test and Standard GraphRAG indexing over two abstracts initially. Preserve a full-text expansion option.
- Interactive graph inspection, basic/vector and local/graph query comparison, source context inspection, and a ten-question evaluation sheet.
- Portable exports, persistent Colab storage, model-response caching, source hashes and run metadata.

## Boundaries

The corpus is a historical pipeline test set, not a current comprehensive literature review. Draft links are not approved Aurevion policies. No user health data, live Aurevion database access, autonomous recommendations or production integration are included. Live API execution requires an explicit notebook flag and a Gemini key entered through Colab Secrets or an environment variable. Keys and live run outputs stay out of Git.

## Success criteria

The key-free notebook runs from start to finish; every source has a verified license and identity; corpus preparation is deterministic; model configuration validates against the pinned GraphRAG release; citations resolve through document/text-unit IDs; generated citations and retrieved context remain distinguishable; evaluation rows start unscored; and clean exports can be reopened without an API key.

## Future integration

The verified `codex/tokens-grid` integration boundary is `apps/api/app/features/evidence_knowledge`. Only portable, reviewed records and evaluated retrieval behavior should cross this boundary in a separate integration pass.
