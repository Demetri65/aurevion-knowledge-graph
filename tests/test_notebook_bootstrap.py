"""Prevent uploaded source selections from silently using an older checkout."""

import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


class NotebookBootstrapTests(unittest.TestCase):
    def test_explicit_bundle_cannot_silently_reuse_existing_source(self):
        notebook = json.loads((ROOT / 'notebooks/01_graphrag_colab.ipynb').read_text())
        source = next(''.join(cell['source']) for cell in notebook['cells']
                      if cell['cell_type'] == 'code'
                      and 'PROJECT_BUNDLE = None' in ''.join(cell['source']))
        source = source.replace('PROJECT_BUNDLE = None', "PROJECT_BUNDLE = '/content/uploaded.zip'", 1)
        with patch.object(Path, 'cwd', return_value=ROOT), patch.object(subprocess, 'run') as run:
            with self.assertRaisesRegex(RuntimeError, 'cannot replace an existing checkout'):
                exec(compile(source, 'bootstrap-cell', 'exec'), {})
        run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
