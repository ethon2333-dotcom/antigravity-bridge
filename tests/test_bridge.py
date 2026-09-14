import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('bridge', Path(__file__).resolve().parents[1] / 'connector/antigravity_bridge.py')
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)


class Tests(unittest.TestCase):
    def test_loopback_only(self):
        for value in ('evil.example:12', '0.0.0.0:80', '127.0.0.1:99999', 'localhost:0'):
            with self.assertRaises(b.BridgeError):
                b.address(value)
        self.assertEqual(b.address('127.0.0.1:1234'), '127.0.0.1:1234')

    def test_redaction(self):
        self.assertNotIn('secret-value', b.redact('token secret-value', ['secret-value']))

    def test_new_needs_project(self):
        a = b.parse(['new', '--prompt-file', '/not/read'])
        a.project_id = None
        with self.assertRaises(b.BridgeError):
            b.build_action(a)

    def test_dry_run_no_process_or_network(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'prompt.txt'
            p.write_text('A harmless test', encoding='utf8')
            with patch.object(b, 'run', side_effect=AssertionError('must not launch')), patch.object(b, 'emit') as out:
                self.assertEqual(b.main(['new', '--project-id', 'test-project', '--prompt-file', str(p)]), 0)
                self.assertFalse(out.call_args.args[0]['will_send'])

    def test_multiple_servers_fail_closed(self):
        result = subprocess.CompletedProcess([], 0,
            '1 /Applications/Antigravity.app/Contents/Resources/bin/language_server\n'
            '2 /Applications/Antigravity.app/Contents/Resources/bin/language_server\n', '')
        with patch.object(b, 'run', return_value=result):
            with self.assertRaises(b.BridgeError):
                b.discover()
            self.assertEqual(b.discover(2), 2)

    def test_failed_write_is_not_retried(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'task.txt'
            p.write_text('test', encoding='utf8')
            with patch.object(b, 'cli_path', return_value='/fake/agentapi'), patch.dict(b.os.environ, {'ANTIGRAVITY_CSRF_TOKEN': 'private-token'}), patch.object(b, 'run', return_value=subprocess.CompletedProcess([], 1, json.dumps({'error': 'project_id required'}), '')) as command:
                with self.assertRaises(b.BridgeError):
                    b.main(['--address', '127.0.0.1:1234', 'new', '--project-id', 'test-project', '--prompt-file', str(p), '--execute'])
                self.assertEqual(command.call_count, 1)
                self.assertEqual(command.call_args.kwargs['env']['ANTIGRAVITY_PROJECT_ID'], 'test-project')
                self.assertNotIn('private-token', str(command.call_args.args))


if __name__ == '__main__':
    unittest.main()
