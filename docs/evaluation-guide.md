# Evaluate the retrieval experiment

## Check coverage first

The ten questions in [`evaluations/questions.jsonl`](../evaluations/questions.jsonl) describe expected source handling, not medical answer keys. Scores start as `null`: **not evaluated**.

The default index contains the first **two abstracts**. Check each question's `required_source_ids` and `minimum_document_mode` against `corpus_covered`, `mode_covered` and the prepared documents' truncation flags. A downloaded paper may be absent from the index; selecting full-text mode does not guarantee a character-capped document contains the needed methods or tables.

Mark missing sources or passages **not run: missing evidence**, leaving scores empty. Do not count unavailable input as a retrieval failure or fill the gap from model memory. Evidence-gap answers must stay bounded to the declared corpus, without claiming no relevant research exists elsewhere.

## Compare the same experiment

Run each covered question through **basic** passage/vector search and **local** graph-assisted search with identical documents and model settings. Preserve the question, answers, context, citation identifiers, source hashes and run settings. Record latency and token usage when available; a longer answer alone does not demonstrate better retrieval.

## Inspect claims and citations

For each substantive assertion:

1. Trace its generated marker through `resolved_citation_markers` to the text-unit/document IDs and original source passage. Treat unresolved markers as gaps; report markers identify derived community summaries.
2. Check whether the passage supports the assertion and preserves population, study design, intervention, comparator, outcome and duration where available.
3. Keep reported findings, model interpretations and human-authored draft decisions distinct. Record disagreement, missing details and unsupported claims.

Retrieved context is separate from generated citations, and a resolved citation does not prove correctness. Observational findings do not establish randomized causal evidence. The five historical papers do not establish current consensus or justify universal recommendations.

## Score after inspection

Use the four nullable scores already present in each question record:

| Score | 0 | 1 | 2 |
|---|---|---|---|
| `citation_traceability` | Unresolvable or fabricated citations | Some resolve; gaps remain | Every sourced assertion resolves to intended text |
| `evidence_fidelity` | Material unsupported or contradictory claims | Mostly grounded; some omissions | Claims and uncertainty match available text |
| `applicability` | Population, design or causal scope misrepresented | Limits mentioned incompletely | Relevant limits and design preserved |
| `question_coverage` | Question unanswered | Partly addressed | Addressed, including appropriate evidence gaps |

Attach concise reviewer notes explaining each score. Do not fill scores from model confidence or another model's opinion alone.

## Review changes and decide what follows

For source revisions, compare IDs and hashes and trace explicit draft decision dependencies. Preserve the earlier snapshot and run evidence. The lab retains changed XML and manifest history; detecting upstream corrections and approving policy changes remain separate work.

Expand beyond two abstracts after citations and answers are useful and inspectable. Diagnose missing input, bad joins, malformed extraction and synthesis errors separately. Integration with Aurevion requires reviewed decision links and reproducible evidence of an advantage over basic retrieval for actual research questions. Live quality remains unverified until a credentialed run succeeds and its outputs are inspected.
