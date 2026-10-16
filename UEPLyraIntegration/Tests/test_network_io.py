"""Exercise Windows message races without starting UE."""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Overlay' / 'Content' / 'Scripts'))
from uep_lyra_network_io import atomic_write, read_json, sharing_retry, open_shared_text  # noqa: E402


class NetworkIOTests(unittest.TestCase):
    def test_sharing_violation_retries_then_succeeds(self):
        operation = Mock(side_effect=[PermissionError(), PermissionError(), 'complete'])
        with patch('uep_lyra_network_io.time.sleep') as sleep:
            self.assertEqual(sharing_retry(operation), 'complete')
            self.assertEqual(sleep.call_count, 2)

    def test_permanent_permission_error_is_not_hidden(self):
        operation = Mock(side_effect=PermissionError())
        with patch('uep_lyra_network_io.time.sleep'), self.assertRaises(PermissionError):
            sharing_retry(operation)
        self.assertEqual(operation.call_count, 10)

    def test_replace_file_remove_conflict_retries_then_succeeds(self):
        conflict = OSError('destination is temporarily held')
        conflict.winerror = 1175
        operation = Mock(side_effect=[conflict, conflict, 'complete'])
        with patch('uep_lyra_network_io.time.sleep') as sleep:
            self.assertEqual(sharing_retry(operation), 'complete')
        self.assertEqual(operation.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    def test_persistent_replace_file_conflict_remains_failure(self):
        conflict = OSError('destination remains held')
        conflict.winerror = 1175
        operation = Mock(side_effect=conflict)
        with patch('uep_lyra_network_io.time.sleep') as sleep, self.assertRaises(OSError):
            sharing_retry(operation)
        self.assertEqual(operation.call_count, 10)
        self.assertLess(sum(call.args[0] for call in sleep.call_args_list), 0.6)

    def test_partial_replace_and_unrelated_os_errors_are_not_retried(self):
        for code in (1176, 1177, 112):
            with self.subTest(winerror=code):
                error = OSError('non-retryable filesystem error')
                error.winerror = code
                operation = Mock(side_effect=error)
                with patch('uep_lyra_network_io.time.sleep') as sleep, self.assertRaises(OSError):
                    sharing_retry(operation)
                operation.assert_called_once()
                sleep.assert_not_called()

    def test_atomic_roundtrip_and_missing_message(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'nested' / 'ack.json'
            self.assertIsNone(read_json(path))
            atomic_write(path, {'phase': 1})
            atomic_write(path, {'phase': 2})
            self.assertEqual(read_json(path), {'phase': 2})

    def test_invalid_json_is_not_hidden(self):
        path = Mock()
        with patch('uep_lyra_network_io.read_text', return_value='{broken'), self.assertRaises(json.JSONDecodeError):
            read_json(path)

    def test_open_reader_allows_real_atomic_replacement_and_keeps_old_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'snapshot.json'
            atomic_write(path, {'phase': 'old'})
            with open_shared_text(path) as reader:
                atomic_write(path, {'phase': 'new'})
                self.assertEqual(json.loads(reader.read()), {'phase': 'old'})
            self.assertEqual(read_json(path), {'phase': 'new'})

    def test_retry_backoff_is_bounded_and_permanent_errors_still_fail(self):
        operation = Mock(side_effect=PermissionError())
        with patch('uep_lyra_network_io.time.sleep') as sleep, self.assertRaises(PermissionError):
            sharing_retry(operation)
        self.assertEqual(operation.call_count, 10)
        self.assertLess(sum(call.args[0] for call in sleep.call_args_list), 0.6)


if __name__ == '__main__':
    unittest.main()
