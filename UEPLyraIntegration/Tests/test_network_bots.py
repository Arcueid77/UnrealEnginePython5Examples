"""Pin reflected out-parameter handling and the test-isolation write boundary."""

from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Overlay' / 'Content' / 'Scripts'))
from uep_lyra_network_bots import isolate_bots  # noqa: E402


class Brain:
    def __init__(self, running=True):
        self.running = running
        self.stops = 0

    def is_valid(self):
        return True

    def get_path_name(self):
        return 'test-brain'

    def call_function(self, name, *args):
        if name == 'IsRunning':
            return self.running
        if name == 'StopLogic':
            self.stops += 1
            self.running = False
            return
        raise AssertionError('Unexpected bot write: ' + name)


class NetworkBotTests(unittest.TestCase):
    def test_single_out_tuple_is_unpacked_and_only_ai_is_stopped(self):
        brain = Brain()
        controller = Mock(BrainComponent=brain)
        controller.get_path_name.return_value = 'bot'
        statics = Mock()
        statics.call_function.return_value = ([controller],)
        result = isolate_bots(statics, 'world', 'LyraPlayerBotController')
        statics.call_function.assert_called_once_with('GetAllActorsOfClass', 'world', 'LyraPlayerBotController')
        controller.call_function.assert_called_once_with('StopMovement')
        self.assertEqual(result, [dict(controller='bot', brain='test-brain', running=False)])
        self.assertEqual(brain.stops, 1)

    def test_stopped_brain_is_not_restarted_or_repeatedly_modified(self):
        brain = Brain(False)
        controller = Mock(BrainComponent=brain)
        statics = Mock()
        statics.call_function.return_value = ([controller],)
        isolate_bots(statics, 'world', 'bot-class')
        self.assertEqual(brain.stops, 0)
        controller.call_function.assert_not_called()

    def test_uninitialized_brain_cannot_count_as_isolated(self):
        statics = Mock()
        statics.call_function.return_value = ([Mock(BrainComponent=None)],)
        self.assertEqual(isolate_bots(statics, 'world', 'bot-class'), [])

    def test_unexpected_reflection_return_shape_fails(self):
        statics = Mock()
        statics.call_function.return_value = ()
        with self.assertRaises(ValueError):
            isolate_bots(statics, 'world', 'bot-class')


if __name__ == '__main__':
    unittest.main()
