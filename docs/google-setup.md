# Google setup

## Start without a key

Keep `RUN_LIVE = False` for the source, draft-graph and evaluation walkthrough. It needs no Gemini API credit or GPU. Enable live inference only after inspecting your API project's quota and billing.

## API access and subscription benefits

Gemini notebook calls use an **API project and key**, with that project's quotas, billing and data-use terms. Google AI Pro's AI Studio interface allowances are separate. Eligible Cloud credits or Colab compute benefits depend on your account; check your actual entitlement rather than assuming subscription access transfers to API calls.

Current references: [Google AI plans](https://ai.google.dev/gemini-api/docs/google-ai-plans), [AI Pro benefits](https://support.google.com/googleone/answer/14534406?hl=en), [API billing](https://ai.google.dev/gemini-api/docs/billing), [active rate limits](https://ai.google.dev/gemini-api/docs/rate-limits). These were checked on October 11, 2026; benefits and quotas can change.

## Models and bounded defaults

| Role | Model |
|---|---|
| Extraction and answers | `gemini-3.1-flash-lite` |
| Text embeddings | `gemini-embedding-001`, 3,072 dimensions |

The lab pins GraphRAG **3.3.0** and starts with two abstracts and one concurrent request. Keep the supplied chunk limits; embedding 001 accepts up to 2,048 input tokens. Changing the embedding model or dimensions requires a new vector index.

See [Flash-Lite capabilities](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite), [embedding specifications](https://ai.google.dev/gemini-api/docs/embeddings), [pricing and data use](https://ai.google.dev/gemini-api/docs/pricing) and [GraphRAG model configuration](https://microsoft.github.io/graphrag/config/models/). The usage ledger records observed token counts and available cost estimates; it does not enforce a spend ceiling.

## Provide credentials at runtime

1. In [AI Studio](https://aistudio.google.com/apikey), choose a project, inspect its billing tier and quotas, and create or reuse a key.
2. In **browser Colab**, add `GEMINI_API_KEY` to the Secrets panel and grant notebook access.
3. In the **VS Code Colab extension**, use the notebook's masked live-key prompt or an environment variable on the remote kernel. `userdata.get()` is currently unsupported there; see [the VS Code guide](vscode-colab.md).
4. With a **local kernel**, provide `GEMINI_API_KEY` in that process's environment through your secret manager or private shell session.
5. Set `RUN_LIVE = True`, then run the smoke test before indexing. Keep the key out of source files, saved outputs and Git.

## Read the smoke test

The probe checks one structured completion with an exact synthetic source quote, then a finite embedding with the expected dimensions. Passing establishes basic provider compatibility, not reliable scientific extraction. If it fails, resolve the reported model, quota or credential issue before rerunning; the notebook stops before indexing.

Live calls use selected public, licensed research. Free-tier input may be used to improve Google's products; the API project's terms govern notebook calls. Clear live notebook outputs and restore the live-disabled default before sharing the source notebook.
