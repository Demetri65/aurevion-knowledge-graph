# Google setup for the notebook

Checked against Google's official documentation on 2026-10-11. Account benefits, availability and quotas can change; this guide does not verify your account's entitlement.

## What Google AI Pro contributes

Google AI Pro now offers higher subscription limits in the **Google AI Studio web interface**, including Playground and Build. Those allowances are distinct from the Gemini API project tiers used by a Python notebook. A Colab notebook calling Gemini needs an API key and follows the associated project's API quotas and billing settings. [Google AI plans](https://ai.google.dev/gemini-api/docs/google-ai-plans).

The current Google One help page lists **$10 in monthly Google Cloud credits** through developer benefits. An active eligible AI Pro membership must be linked to a Google Developer profile. Eligible Cloud credits can cover Gemini API usage after they are applied to a Cloud Billing account. This is a finite credit benefit, not unlimited subscription API usage. [AI Pro benefits](https://support.google.com/googleone/answer/14534406?hl=en), [Google Developer Program FAQ](https://developers.google.com/profile/help/faq).

Some accounts use prepaid API billing. Google requires an active paid balance greater than zero before eligible promotional Cloud credits can be consumed, and currently documents a $5 minimum credit purchase. Eligible promotional credits are consumed before prepaid funds. Check your billing screen before opting into paid usage; this project never enables billing or buys credits. Google One AI credits are a separate system from Google Cloud credits. [Gemini API billing](https://ai.google.dev/gemini-api/docs/billing), [subscription compatibility](https://ai.google.dev/gemini-api/docs/google-ai-plans).

AI Pro also currently lists **200 Colab compute units (CCUs)**. The help page restricts that benefit to eligible Google One family plan managers aged 18 or older, and excludes trial memberships. A student promotional trial should therefore not be assumed to include those units. Check the Colab account's actual balance and plan. Hardware and runtime availability still vary. [AI Pro Colab benefits](https://support.google.com/googleone/answer/14534406?hl=en), [Colab resource limits](https://research.google.com/colaboratory/faq.html).

## Choose a project and model

The lab pins GraphRAG **3.3.0**. Use the project's pinned dependencies rather than combining configuration snippets from older releases. Configuration validation is performed offline; provider access, quotas and live compatibility are confirmed only by a successful smoke test in your account.

The initial candidates are:

| Role | Gemini model ID | Reason for the initial choice |
| --- | --- | --- |
| Extraction and answer generation | `gemini-3.1-flash-lite` | Stable model with structured output and a free API tier. Current paid standard text rates are $0.25 per million input tokens and $1.50 per million output tokens, including thinking tokens. |
| Text embeddings | `gemini-embedding-001` | Stable text embedding model used in Microsoft's Gemini configuration example. It accepts up to 2,048 input tokens and defaults to 3,072 dimensions. |

Sources: [3.1 Flash-Lite capabilities](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite), [current pricing](https://ai.google.dev/gemini-api/docs/pricing), [embedding specifications](https://ai.google.dev/gemini-api/docs/embeddings), [GraphRAG model selection](https://microsoft.github.io/graphrag/config/models/).

Use the conservative document/chunk limits supplied by the lab for embedding 001. Changing embedding models or dimensions requires rebuilding the relevant vector index; vectors from different embedding spaces cannot be mixed. Free-tier API access is quota-limited. Google directs you to [AI Studio's active rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) for your project rather than providing a guaranteed universal allowance.

## Colab credentials

1. Run the key-free notebook first. Installation, source inspection, the labeled draft graph and evaluation preparation do not require a Gemini key.
2. In [Google AI Studio](https://aistudio.google.com/apikey), choose a project and inspect its billing tier and active quotas. Use a free-tier project if you intend to test without enabling usage-based billing.
3. Create or reuse a Gemini key for that project. In Colab, open the key-shaped **Secrets** panel, add the name `GEMINI_API_KEY`, and enable notebook access for that secret.
4. Leave the key out of code cells, saved outputs, Markdown, Git, screenshots and chat. The notebook reads the secret at runtime; do not paste it into the `.ipynb` file.
5. Set the notebook's explicit live-execution flag only when you are ready to use that key. Run the smoke-test cell before enabling indexing.

On a local Jupyter runtime, provide `GEMINI_API_KEY` as a process environment variable through your preferred local secret manager or private shell session. Never save its value in the notebook or a tracked file. Use the notebook's default live-disabled mode when sharing it, and clear any live outputs before publishing.

## Interpret the smoke test

The smoke test should make one small, non-streaming schema-shaped completion and a bounded embedding request. Confirm JSON schema validation, vector dimensions and finite values before indexing. A valid JSON response establishes format compatibility; it does not establish reliable scientific extraction.

If the smoke test fails, inspect the sanitized error category and model/project settings. A quota error can occur with a valid key; an unavailable model can occur with an otherwise working project. Resolve that specific condition before rerunning indexing. Do not switch automatically to a paid project or a more expensive model.

This lab sends only the selected public, licensed research text. Google's pricing page distinguishes free-tier data use for product improvement from paid-tier data handling. Subscription UI benefits do not establish the handling of notebook API calls; the API project's settings and applicable terms govern those calls. [Gemini pricing and data-use table](https://ai.google.dev/gemini-api/docs/pricing).
