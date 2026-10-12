# VS Code with a Colab runtime

This guide was checked against Google's official extension documentation on 2026-10-11. The project's key-free browser Colab run is recorded in [verification.md](verification.md); a VS Code Colab extension kernel has **not been tested** for this project.

## Local source and remote execution

Open your local `aurevion-knowledge-graph` folder in VS Code, then open `notebooks/01_graphrag_colab.ipynb`. Your notebook and source edits remain local. Selecting a Colab kernel sends cell execution to Google's remote runtime; its files live under `/content`. The bootstrap prepares a separate checkout at `/content/aurevion-knowledge-graph` from [the public repository](https://github.com/Demetri65/aurevion-knowledge-graph) and prints its project path and Git commit.

Local file changes, shell environment variables and installed packages do not automatically appear in that runtime. The internal distribution and import names remain `aurevion-knowledge-lab` and `aurevion_knowledge_lab`; the public repository name does not change those Python names.

## Connect and run

1. Install Google's [Colab extension](https://marketplace.visualstudio.com/items?itemName=google.colab), which uses VS Code's Jupyter extension.
2. In the notebook, choose **Select Kernel → Colab → Auto Connect** and complete Google sign-in. For an explicit hardware choice, choose **New Colab Server** and select **CPU**. See Google's [User Guide](https://github.com/googlecolab/colab-vscode/wiki/User-Guide).
3. Run the bootstrap, leaving `RUN_LIVE = False`. If its dependency guard requests a session restart, restart the kernel and rerun the notebook from the top.
4. Run the key-free track and inspect the source tables, labeled draft graph, coverage checks and artifact export before enabling API calls.

## Refresh source while iterating

Edit the local source, validate it, then commit and push the intended changes to the public repository. If editing the generated notebook, update `scripts/build_notebook.py` and regenerate `notebooks/01_graphrag_colab.ipynb` before committing.

In the bootstrap cell, set `PULL_RUNTIME_SOURCE = True` and rerun it to explicitly refresh the runtime checkout. It permits a fast-forward update of a clean clone. If helper source changed, restart the kernel and rerun from the top so imports use the new code. Return the flag to `False` for ordinary runs. Saving a local file alone does not refresh the remote source; a fresh runtime also needs the bootstrap. The exported experiment records the source commit.

For unpublished edits, build the source ZIP, upload it into a fresh runtime and set `PROJECT_BUNDLE` to its remote path. Clear the flag after extraction before rerunning, including after a kernel restart. The notebook refuses to replace an existing checkout with a ZIP. If you change dependencies, reinstall the project in the executing kernel and restart it.

## Supply a key to the remote kernel

Keep the default key-free mode until you are ready for live inference. The notebook reads `GEMINI_API_KEY` from the **executing kernel's environment** first. In browser Colab, it can also read the Secrets panel through `google.colab.userdata.get` after you grant notebook access.

Google currently lists `userdata.get()` as unsupported in the extension. For VS Code, set `RUN_LIVE = True` and use the notebook's masked key prompt in section 6. It stops if the kernel cannot provide hidden input; key-free execution is unaffected. Never put the key in cell source, outputs or tracked files. A key set in your Mac's terminal does not set the remote kernel's environment. See [Google setup](google-setup.md) for API project quotas and billing; pass the smoke test before indexing.

## Runtime files and downloads

Use the extension's **Colab → Contents** panel to inspect the server's `/content` directory. After export, follow the notebook's printed ZIP path, refresh Contents if needed, then right-click the file and choose **Download…**. This command is provided by the extension's [runtime file UI](https://github.com/googlecolab/colab-vscode/blob/main/package.json).

Google lists `google.colab.files.upload()` and `files.download()` as unsupported in VS Code. As an optional upload route, right-click local files or folders in VS Code Explorer and choose **Upload to Colab**; verify their remote paths before using them. Download artifacts before removing the server or ending the runtime. See the [Known Issues and Workarounds](https://github.com/googlecolab/colab-vscode/wiki/Known-Issues-and-Workarounds) and [file controls](https://github.com/googlecolab/colab-vscode/wiki/User-Guide#working-with-files).
