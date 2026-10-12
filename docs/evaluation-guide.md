# Evaluate the retrieval experiment

The ten fixed questions in `evaluations/questions.jsonl` are a test sheet, not a medical recommendation answer key. Expected behaviors describe source handling, applicability and evidence gaps. Each score starts as `null`, meaning **not evaluated**, rather than zero or failure.

The five papers form a historical pipeline test corpus. They do not establish a comprehensive or current fitness/nutrition literature review. Every draft decision link and human-authored example is labeled separately from live GraphRAG output.

## Start with the indexed corpus

The live experiment initially indexes **the first two documents' abstracts**. For each question, compare `required_source_ids` with the enabled indexing selection. A downloaded paper is not necessarily an indexed paper. A paper present only as an abstract cannot support an answer that requires unavailable full-text methods or tables.

If a question requires a source that was not indexed, mark it **not run: missing enabled sources**. Record the source IDs and document mode before evaluating. Do not count that question as a retrieval failure, assign a zero, or silently answer from model memory. After extending the corpus, rerun indexing and evaluate against that newly recorded run.

Questions about absent evidence can be tested only for the declared corpus: an answer may say the indexed sources do not establish something. It must not claim no research exists anywhere.

## Compare retrieval methods

Run the same question against the same document set and model settings through:

- Basic/vector retrieval, which retrieves related text without requiring graph traversal.
- Local/graph retrieval, which also uses extracted entities and relationships.

Document-specific questions test whether either method can recover a precise source. Questions spanning several studies test whether graph retrieval adds useful context or a defensible connection. Global synthesis can be explored later; a longer answer alone is not evidence of better retrieval.

Record each method's raw answer, retrieved context, citation identifiers, latency and reported token usage. These fields are observations, not ratings. Preserve the provider/model versions and source hashes with the run.

## Check citations and claims

Inspect the source text before scoring. Generated answer citations and retrieved-context rows are different things: retrieval of a paper does not prove the answer cited it, and citation of a paper does not prove it supports the assertion.

For each substantive assertion:

1. Resolve its document/text-unit identifiers back to the source manifest and cached text.
2. Find the relevant passage and determine whether the assertion is supported.
3. Check studied population, intervention, comparator, outcome and duration where available.
4. Keep reported findings, proposed interpretations and Aurevion's draft decision separate.
5. Identify disagreement, unavailable detail or missing evidence explicitly.

For observational findings, check that the answer does not imply randomized causal evidence. For a population-specific paper, check that the answer does not generalize to all users without justification. For a missing-source or missing-outcome question, a well-bounded statement of insufficient evidence can be a strong answer.

## Score after inspection

The question records reserve four nullable scores:

| Score | 0 | 1 | 2 |
| --- | --- | --- | --- |
| `citation_traceability` | Sources cannot be resolved or citations are fabricated | Some citations resolve; substantive gaps remain | Every substantive sourced assertion resolves to the intended source text |
| `evidence_fidelity` | Material unsupported or contradictory claims | Mostly grounded with an omission or imprecise qualification | Claims and uncertainty match the available text |
| `applicability` | Population, study design or causal scope is materially misrepresented | Applicability is mentioned but incomplete | Relevant limits and study design are preserved |
| `question_coverage` | Does not address the question | Addresses part of it | Addresses the question, including an appropriate evidence-gap response where needed |

Attach short reviewer notes explaining the score. There are no prefilled gold answers or required numeric scientific conclusions. Do not fill scores from another model's opinion alone.

## Source correction and decision review

The source-change question evaluates engineering traceability. Check whether the exported manifest can identify a changed source hash and whether explicit draft decision links identify dependent decisions. A fresh research graph should not be credited with automatic policy-change detection unless the implementation actually demonstrates it.

Record a correction as a new source snapshot or revision rather than modifying historical run evidence in place. Re-extraction can propose changed claims; a reviewer must still decide whether a draft product decision should change.

## Decide whether to expand

Inspect failures first: missing enabled sources, missing full-text detail, bad source joins, malformed extraction, unsupported relationships and synthesis errors require different repairs. Fix the relevant stage and rerun only the affected checks.

Expand beyond the first two abstracts when citation joins work and the notebook provides useful, inspectable answers. Integrate with Aurevion only after reproducible runs show an advantage for actual research/decision questions over basic retrieval and after decision links have been reviewed. Report live model results as unverified until a credentialed run has succeeded and been inspected.
