from pathlib import Path
import json
import sys
import tempfile
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager

root = Path(__file__).resolve().parents[1]
notebook = nbformat.read(root / 'notebooks/01_graphrag_colab.ipynb', as_version=4)
with tempfile.TemporaryDirectory() as temporary:
    spec = Path(temporary) / 'lab-offline'
    spec.mkdir()
    (spec / 'kernel.json').write_text(json.dumps({'argv': [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}'],
                                                'display_name': 'Lab offline', 'language': 'python'}))
    manager = KernelManager(kernel_name='lab-offline', kernel_spec_manager=KernelSpecManager(kernel_dirs=[temporary]))
    client = NotebookClient(notebook, timeout=180, kernel_name='lab-offline', km=manager,
                            resources={'metadata': {'path': str(root)}})
    client.execute()
output = root / 'runs/offline.executed.ipynb'
output.parent.mkdir(exist_ok=True)
nbformat.write(notebook, output)
print(f'Executed every notebook cell with live inference disabled: {output}')
