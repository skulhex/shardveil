import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sv.core.movement_input import MovementInputState


LEFT = 1
RIGHT = 2
UP = 3
DOWN = 4

HORIZONTAL = {LEFT: -1, RIGHT: 1}
VERTICAL = {UP: 1, DOWN: -1}


class MovementInputStateTests(unittest.TestCase):
    def setUp(self):
        self.state = MovementInputState(HORIZONTAL, VERTICAL, diagonal_window=0.12)

    def test_single_axis_press_resolves_cardinal_move(self):
        self.state.press(RIGHT, 1.0)

        self.assertIsNone(self.state.resolve_move(1.05))
        self.assertEqual(self.state.resolve_move(1.12), (1, 0))

    def test_held_single_axis_repeats_after_first_move(self):
        self.state.press(RIGHT, 1.0)

        self.assertEqual(self.state.resolve_move(1.12), (1, 0))
        self.assertEqual(self.state.resolve_move(2.0), (1, 0))

    def test_near_simultaneous_two_axis_press_resolves_diagonal(self):
        self.state.press(UP, 1.0)
        self.assertIsNone(self.state.resolve_move(1.05))

        self.state.press(RIGHT, 1.08)

        self.assertEqual(self.state.resolve_move(1.08), (1, 1))

    def test_pressing_second_axis_while_holding_transitions_directly_to_diagonal(self):
        self.state.press(UP, 1.0)

        self.assertEqual(self.state.resolve_move(1.12), (0, 1))

        self.state.press(RIGHT, 1.5)

        self.assertEqual(self.state.resolve_move(1.5), (1, 1))
        self.assertEqual(self.state.resolve_move(2.0), (1, 1))

    def test_last_pressed_key_wins_on_same_axis_until_release(self):
        self.state.press(LEFT, 1.0)
        self.state.press(RIGHT, 1.05)

        self.assertEqual(self.state.resolve_move(1.17), (1, 0))

        self.state.release(RIGHT, 1.3)

        self.assertEqual(self.state.resolve_move(1.3), (-1, 0))

    def test_blocked_hold_requires_input_change_before_retry(self):
        self.state.press(RIGHT, 1.0)

        self.assertEqual(self.state.resolve_move(1.12), (1, 0))
        self.state.mark_blocked(1, 0)

        self.assertIsNone(self.state.resolve_move(2.0))

        self.state.release(RIGHT, 2.1)
        self.state.press(RIGHT, 2.2)

        self.assertEqual(self.state.resolve_move(2.33), (1, 0))


if __name__ == "__main__":
    unittest.main()
