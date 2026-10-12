# Overnight goal: build a useful fitness evidence graph

## Objective

Turn this lab into a growing, source-grounded research library for Aurevion. Deliver a working graph that connects inspected research to provisional claims and concrete product questions, with retrieval tests and an honest coverage report.

Use up to eight hours. Treat the targets below as a work plan, not a reason to invent evidence. Finish earlier only if the acceptance checks pass. At the time limit, save a partial report, remaining queue and exact restart instructions. A time-limited partial result is not full completion of the research objective.

Reserve the final 60–90 minutes for verification and reporting. If setup or source inspection takes longer, reduce collection breadth and queue unfinished topics rather than cutting the evidence audit.

## Workspace and operating rules

- Work in `/Users/demetrilopez/dev/aurevion-knowledge-graph`. Inspect the existing code, notebook and evaluation guide first. Preserve the five-paper historical corpus and its passing checks as fixtures.
- Use GPT-6.1 Sol for research, synthesis and review through Codex. Browse and use public research APIs; do not require a separately billed model API or Colab session. Live Gemini/GraphRAG inference remains a later experiment unless separately requested.
- Keep changes inside this project. Save local commits at completed milestones. Leave new research and full-text artifacts local for review.
- Use at most two research subagents at a time. Give each separate topic files; one agent owns shared schemas and graph assembly. Reuse the project's environment and helpers where they fit.
- Keep an incremental work queue and checkpoint after each completed batch. Continue independent work when one source or topic is blocked. Report inaccessible evidence instead of substituting model memory.

## Research coverage

| Lane | Questions the app needs to explain |
| --- | --- |
| Strength training | Volume, frequency, load, progression, exercise selection and hypertrophy |
| Aerobic and concurrent training | Endurance dose, intensity, strength/cardio tradeoffs and scheduling |
| Nutrition | Energy intake, protein, meal timing, dietary quality and hydration |
| Weight and body composition | Fat loss, maintenance, plateaus and measurement uncertainty |
| Recovery | Sleep, fatigue, soreness, deloads and limits of readiness signals |
| Adherence | Habit formation, barriers, logging burden, reminders and feedback |
| Personalization | Beginners versus trained adults, age, sex and goal-specific applicability |
| Measurement and supplements | Wearable estimates, body-composition measures, supplement efficacy and uncertainty |

Start with generally healthy adults. Record population-specific evidence explicitly; flag questions requiring clinical expertise. This first pass maps coverage and gaps rather than claiming an exhaustive review.

## Work in this order

### 1. Build the collection and record format

Audit the current fixed-corpus loader. Add a separate expandable library/manifest path so discovery can grow without weakening its fixture checks. Write a short implementation plan, then implement the smallest ingestion path needed for this run.

Record stable source IDs, DOI/PMID/PMCID when present, authors, publication date, source URL, topic, study type, population, access/license status, retrieval time and inspection depth. Deduplicate identifiers and retain version/hash provenance for stored text. Keep search queries and inclusion/exclusion reasons.

Use PubMed/Europe PMC for discovery, publisher or society sources for original publications, and Crossref when metadata needs reconciliation. Respect API limits and download full text only through permitted routes with suitable reuse terms. Catalog inaccessible sources without claiming to have read them. Separate recent syntheses from foundational research and check correction/retraction notices when available.

Track reading access separately from storage and redistribution rights. Lawfully accessible browser full text can support attributable notes even when retaining or publishing its full text is not permitted.

### 2. Collect and inspect evidence

Target roughly 80–120 distinct candidate records and 30–40 closely inspected sources across the lanes. Prioritize systematic reviews, meta-analyses, evidence-based guidelines and relevant primary studies. Track abstract-only versus full-text inspection. Do not pad counts with weak or duplicate sources; syntheses sharing underlying trials are not independent replications.

Produce short evidence notes with findings, population, intervention/comparator, outcomes, study design, limitations and passage/section locators. Distinguish what a source reports from your interpretation. Preserve disagreement and null findings. Store attributable summaries; retain full-text reuse restrictions alongside the source.

### 3. Make the graph useful

Create at least 24 provisional claim records and 8 product-question records where the inspected evidence permits it. Useful questions include progression rules, flexible training frequency, protein explanations, plateau handling, recovery feedback and reminder timing.

Connect papers → specific evidence passages → claims → population/outcome context → proposed decisions. Every substantive claim needs a resolvable supporting passage; topic similarity is not support. Encode opposing evidence and missing context explicitly. Label Codex-created records `codex_synthesis_unreviewed`; independent agent review does not imply human or scientific approval.

Reuse the existing graph renderer and dependency traversal where appropriate. Add a real-data notebook walkthrough: inspect one question, follow its evidence paths, see applicability limits, and identify which proposed decisions need review if a source changes. Keep the imported evidence graph distinct from Microsoft's model-generated GraphRAG index. Prepare stable, attributable documents for that future indexing step.

### 4. Test usefulness and challenge the result

Create 20 concrete research questions spanning source lookup, population fit, conflicting findings, cross-source synthesis, missing evidence and source-change impact. Include questions the library cannot answer.

Freeze these questions before testing retrieval. Record independently checked relevant passage IDs or expected abstention for each; label this reference set as agent-reviewed and provisional. Returning any passage does not count as retrieving supporting evidence.

Implement a reproducible key-free passage baseline and graph-assisted retrieval over the collected records. Compare them on the same questions and corpus. Return passages and graph paths; leave answer quality unscored when no answer was produced. A lexical baseline must be labeled lexical, and vector/model retrieval must be labeled unrun unless actually executed.

Use Codex to draft passage-grounded answers to ten of these questions from the saved retrieval context, including explicit abstentions where evidence is missing. Preserve answer-to-passage links and label these as agent-authored research outputs; the notebook must not imply it generated them through a live model call.

Have a separate review pass check the claim-to-passage links, citation identities, unsupported conclusions, population generalization and duplicate evidence. Correct problems and record remaining uncertainty. Measure observed retrieval coverage and unresolved references; do not assert that graph retrieval wins without results.

## Deliverables

- `research/`: source catalog, topic map, short evidence notes, provisional claims/decision questions and search/inclusion log. Choose simple JSONL/Markdown schemas and document them.
- `runs/`: raw permitted source snapshots, derived graph files and reproducible retrieval results; keep caches and restricted material out of published source.
- A notebook section using the expanded library and a rendered interactive graph with attributable links.
- `docs/research-progress.md`: completed batches, counts by lane, blockers and the next queue; update at every checkpoint.
- `docs/research-report.md`: what the library can answer, strongest findings, contradictions, weak coverage, retrieval results and the next five useful tasks. Keep it concise and link to details.

## Acceptance and verification

The library must load reproducibly, reject invalid references, distinguish source inspection depth, and resolve graph claims back to actual inspected passages. Demonstrate source-to-decision impact tracing and useful retrieval on the evaluation questions. Report achieved counts and missing coverage against the targets.

Run relevant tests for ingestion, deduplication, graph integrity and retrieval behavior. Run the existing suite, notebook validation and complete offline notebook after structural changes. Preserve live-disabled defaults and output-free committed notebooks. Record exactly which checks passed and which paths remain untested.

Completion requires the final evidence audit and report, not just elapsed time or collected URLs. If the eight-hour limit or an external usage limit prevents completion, checkpoint the partial work and explain what remains. Do not spin waiting for inaccessible sources or quota resets.
