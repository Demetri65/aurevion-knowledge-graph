"""Exercise the actual notebook cell's failure recovery without provider calls."""
import ast
import json
from pathlib import Path
import tempfile
import unittest

from aurevion_knowledge_lab.artifacts import write_json

ROOT = Path(__file__).resolve().parents[1]


class NotebookRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_forced_rebuild_cannot_reuse_old_completion_marker(self):
        notebook = json.loads((ROOT / 'notebooks/01_graphrag_colab.ipynb').read_text())
        sources = [''.join(cell['source']) for cell in notebook['cells'] if cell['cell_type'] == 'code']
        source = next(text for text in sources if 'completed = RUN_DIR' in text)

        async def fail_build(*args):
            raise RuntimeError('simulated interrupted build')

        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            marker = run / 'completed.json'
            marker.write_text('{"experiment": {"old": true}}')
            namespace = {'RUN_LIVE': True, 'smoke_ok': True, 'RUN_DIR': run,
                         'REUSE_COMPLETED_INDEX': False, 'experiment': {'new': True},
                         'config': object(), 'documents': [], 'write_json': write_json,
                         'build_graph': fail_build, 'tables': {'stale': True}, 'answers': {'stale': True}}
            cell = compile(source, 'index-cell', 'exec', flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
            with self.assertRaisesRegex(RuntimeError, 'simulated interrupted'):
                await eval(cell, namespace)
            self.assertFalse(marker.exists())
            self.assertIsNone(namespace['tables'])
            self.assertEqual(namespace['answers'], {})


if __name__ == '__main__':
    unittest.main()
