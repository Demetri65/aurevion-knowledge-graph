# Historical research test corpus

These five papers are a deliberately small corpus for testing GraphRAG ingestion,
retrieval, citations, and population qualifiers. They were published between 2013
and 2018. This collection is not a comprehensive or current evidence review and
must not become an authoritative set of fitness recommendations.

| Order | Paper | Type | Full-text license |
| --- | --- | --- | --- |
| 1 | [Protein and exercise position stand](https://pmc.ncbi.nlm.nih.gov/articles/PMC5477153/) | Position stand, 2017 | CC BY 4.0 |
| 2 | [Protein timing meta-analysis](https://pmc.ncbi.nlm.nih.gov/articles/PMC3879660/) | Meta-analysis, 2013 | CC BY 2.0 |
| 3 | [Diets and body composition position stand](https://pmc.ncbi.nlm.nih.gov/articles/PMC5470183/) | Position stand, 2017 | CC BY 4.0 |
| 4 | [Training frequency and strength meta-analysis](https://pmc.ncbi.nlm.nih.gov/articles/PMC6081873/) | Meta-analysis, 2018 | CC BY 4.0 |
| 5 | [Resistance training motivation and adherence cohort](https://pmc.ncbi.nlm.nih.gov/articles/PMC4362642/) | Prospective cohort, 2015 | CC BY 4.0 |

The final paper concerns previously sedentary, post-menopausal South African
women. Its observational design and population are useful tests of whether an
answer preserves limits on generalization. The frequency meta-analysis also
tests whether answers retain the distinction between training frequency and
weekly volume. Position stands and pooled studies can cite the same underlying
research; they should not be counted as independent replications.

## Source access and attribution

`manifest.jsonl` records the DOI, PMID, PMCID, exact full-text download route,
license, authors, fetch time, and SHA-256 for each original XML file. The files in
`papers/` are unmodified downloads from the permitted
[Europe PMC full-text API](https://europepmc.org/RestfulWebService). Citation URLs
point to PMC article pages, but automated retrieval uses only the explicit API
routes, without redirects or scraping article pages.

The article-front XML contains the actual license statements. These sources use
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) or
[CC BY 2.0](https://creativecommons.org/licenses/by/2.0/), which permit commercial
reuse subject to their attribution requirements. Keep authors, source links and
license links with reused material, and identify changes. These articles do not
become public domain merely because they are openly accessible. Article content
and source metadata are kept together; separate publisher abstracts are not
downloaded or assumed to have the same reuse terms. Review any item-specific
exception before reusing a separately credited illustration or other material.

## Reproducible ingestion

- `load_manifest(project_root)` reads the local allowlist with no network calls.
- `fetch_corpus(project_root)` verifies and reuses existing XML. Missing files
  can be downloaded only from the five approved routes. Each download has a
  30-second timeout and a 4 MiB byte cap.
- `fetch_corpus(project_root, refresh=True)` explicitly refreshes the XML and
  recorded hashes. All downloads are validated before writes. Individual XML
  files and the manifest are saved atomically; an interrupted multi-file update
  is detectable through hash verification.
- `prepare_documents(project_root)` reads verified local files and prepares the
  first two abstracts, with a 12,000-character cap per document. It makes no
  network or model calls. IDs, DOI, PMID, licenses, and hashes are checked against
  the XML rather than trusted from a filename alone.
- `content_mode="full_text"` adds body content to the front abstract. Back matter
  and reference-list entries are excluded so cited paper titles do not become
  standalone evidence claims. Section text, tables, and captions are retained;
  PDF layout, images and mathematical formatting are not reconstructed.

Prepared document provenance includes the content mode, source hash, character
count, truncation flag, authors, and a historical-corpus flag. The `raw_data`
field is JSON text for compatibility with the pinned GraphRAG input schema.
Changing a document's input limit changes which source text is indexed, even
when its original XML hash is unchanged. Record these settings with each run.

The initial authors, IDs, licenses and download routes were verified against
the XML. Reproducibility checks are separate from scientific quality appraisal;
the corpus loader does not assign evidence certainty or validate conclusions.
