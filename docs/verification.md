# Verification record

Verified on October 11, 2026.

## Local and GitHub checks

- 46 unit tests pass, covering corpus identity/license/hash checks, refresh history, GraphRAG adapter configuration and citation resolution, live-probe cache isolation, interrupted notebook rebuild recovery, graph reference integrity and usage-record privacy.
- The committed source notebook passes nbformat validation and Python compilation with top-level await enabled. It contains no execution outputs and defaults to live inference disabled.
- The whole key-free notebook executed successfully locally under Python 3.12 with GraphRAG 3.3.0.
- Dependency consistency and a credential-pattern scan passed. The source ZIP excludes environment files, virtual environments and run caches.
- The initial GitHub Actions run for commit `0ed9d09` passed on Ubuntu/Python 3.12, including the complete key-free notebook. [Run](https://github.com/Demetri65/aurevion-knowledge-graph/actions/runs/38189069105)

## Hosted Colab

Opened the public GitHub notebook in Colab and confirmed CPU hardware with High-RAM disabled. The first installation replaced preloaded dependencies; the notebook's guard stopped execution. After **Runtime → Restart session and run all**, all nine code cells completed.

Observed source tables, the interactive human-authored graph, draft decision dependencies, evaluation coverage, successful GraphRAG configuration validation and the final artifact ZIP. The final status was `offline_demo_verified_live_inference_not_run`. No Gemini key was read and no model API calls were made.

## Remaining evidence

A credentialed Gemini completion/embedding probe and actual GraphRAG indexing/query run are still required before making model-compatibility or retrieval-quality claims. Evaluation scores remain empty. The five-paper historical test corpus does not establish current scientific consensus or approve Aurevion product policies.
