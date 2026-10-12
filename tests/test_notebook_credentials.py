"""Exercise runtime-only credential input without contacting a provider."""

import ast
from contextlib import redirect_stdout
import getpass
import io
import json
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import AsyncMock, Mock, patch

from aurevion_knowledge_lab import graphrag_runner, usage


ROOT = Path(__file__).resolve().parents[1]


class NotebookCredentialsTests(unittest.IsolatedAsyncioTestCase):
    async def execute_probe(self, *, live, input_result=None, input_error=None):
        notebook = json.loads((ROOT / 'notebooks/01_graphrag_colab.ipynb').read_text())
        source = next(''.join(cell['source']) for cell in notebook['cells']
                      if cell['cell_type'] == 'code'
                      and 'probe = await smoke_test(config)' in ''.join(cell['source']))
        userdata = Mock()
        userdata.get.side_effect = RuntimeError('Secrets unavailable in this frontend')
        colab = types.ModuleType('google.colab')
        colab.userdata = userdata
        probe = AsyncMock(return_value={'ok': True, 'embedding_dimensions': 3072})
        make_config = Mock(return_value=object())
        ledger = Mock(return_value=object())
        prompt = Mock(return_value=input_result, side_effect=input_error)
        output = io.StringIO()
        displays = []
        with tempfile.TemporaryDirectory() as temporary:
            namespace = {
                'RUN_LIVE': live, 'PROJECT_ROOT': Path(temporary),
                'WORKSPACE': Path(temporary), 'documents': [],
                'COMPLETION_MODEL': 'test-completion', 'EMBEDDING_MODEL': 'test-embedding',
                'CONTENT_MODE': 'abstract', 'os': os, 'json': json,
                'display': displays.append,
            }
            compiled = compile(source, 'credentials-cell', 'exec', flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
            error = None
            with patch.dict(os.environ, {}, clear=True), \
                    patch.dict('sys.modules', {'google.colab': colab}), \
                    patch.object(graphrag_runner, 'make_config', make_config), \
                    patch.object(graphrag_runner, 'smoke_test', probe), \
                    patch.object(usage, 'install_usage_ledger', ledger), \
                    patch.object(getpass, 'getpass', prompt), redirect_stdout(output):
                try:
                    await eval(compiled, namespace)
                except RuntimeError as caught:
                    error = caught
        return namespace, output.getvalue(), displays, userdata, prompt, probe, ledger, error

    async def test_offline_run_never_reads_or_prompts_for_credentials(self):
        namespace, _, displays, userdata, prompt, probe, ledger, error = await self.execute_probe(live=False)
        self.assertIsNone(error)
        userdata.get.assert_not_called()
        prompt.assert_not_called()
        probe.assert_not_awaited()
        ledger.assert_not_called()
        self.assertFalse(namespace['smoke_ok'])
        self.assertEqual(displays, [])

    async def test_unsupported_secrets_fall_back_to_masked_runtime_input(self):
        secret = 'example-test-credential'
        namespace, output, displays, userdata, prompt, probe, _, error = await self.execute_probe(
            live=True, input_result=secret)
        self.assertIsNone(error)
        userdata.get.assert_called_once_with('GEMINI_API_KEY')
        prompt.assert_called_once()
        probe.assert_awaited_once()
        self.assertTrue(namespace['smoke_ok'])
        self.assertNotIn('api_key', namespace)
        self.assertNotIn(secret, output + json.dumps(displays) + json.dumps(namespace['experiment']))

    async def test_unmasked_frontend_stops_before_provider_calls(self):
        namespace, _, _, _, _, probe, ledger, error = await self.execute_probe(
            live=True, input_error=getpass.GetPassWarning('Input cannot be masked'))
        self.assertRegex(str(error), 'cannot mask input')
        probe.assert_not_awaited()
        ledger.assert_not_called()
        self.assertFalse(namespace['smoke_ok'])


if __name__ == '__main__':
    unittest.main()
