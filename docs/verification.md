# Verification record

Verified on October 11, 2026.

## Local and GitHub checks

- 50 unit tests pass, covering corpus identity/license/hash checks, refresh history, GraphRAG adapter configuration and citation resolution, live-probe cache isolation, interrupted notebook rebuild recovery, graph reference integrity and usage-record privacy. Runtime credential tests also verify that offline execution never requests a key, unsupported Secrets access falls back to hidden input, and an unmasked frontend stops before provider calls. An explicit source ZIP cannot silently reuse an existing checkout.
- The committed source notebook passes nbformat validation and Python compilation with top-level await enabled. It contains no execution outputs and defaults to live inference disabled.
- The whole key-free notebook executed successfully locally under Python 3.12 with GraphRAG 3.3.0.
- Dependency consistency and a credential-pattern scan passed. The source ZIP excludes environment files, virtual environments and run caches.
- The initial GitHub Actions run for commit `0ed9d09` passed on Ubuntu/Python 3.12, including the complete key-free notebook. [Run](https://github.com/Demetri65/aurevion-knowledge-graph/actions/runs/38189069105)

## Hosted Colab

Opened the public GitHub notebook in Colab and confirmed CPU hardware with High-RAM disabled. The first installation replaced preloaded dependencies; the notebook's guard stopped execution. After **Runtime → Restart session and run all**, all nine code cells completed.

Observed source tables, the interactive human-authored graph, draft decision dependencies, evaluation coverage, successful GraphRAG configuration validation and the final artifact ZIP. The final status was `offline_demo_verified_live_inference_not_run`. No Gemini key was read and no model API calls were made.

## Local VS Code workspace

The local Git folder is `aurevion-knowledge-graph`. Its relocated Python 3.12 environment and editable package installation were repaired; `pip check` passes. The revised notebook's nine lab sections render in VS Code, and Google's Colab extension 0.9.7 is already installed. The complete revised key-free notebook also passes local execution.

No kernel was selected or executed through the VS Code extension during this check. Remote file transfer, hidden-input UI and live Gemini calls through that extension remain unverified. The earlier browser Colab check applies to the previous notebook revision.

## Remaining evidence

A credentialed Gemini completion/embedding probe and actual GraphRAG indexing/query run are still required before making model-compatibility or retrieval-quality claims. Evaluation scores remain empty. The five-paper historical test corpus does not establish current scientific consensus or approve Aurevion product policies.
