import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sv.ui.overlay import OverlayScreenId, ScreenStack, ViewScreenId


class ScreenStackTests(unittest.TestCase):
    def test_push_sets_current_screen(self):
        stack = ScreenStack()

        stack.push(OverlayScreenId.PAUSE)

        self.assertEqual(stack.current(), OverlayScreenId.PAUSE)
        self.assertEqual(stack.depth(), 1)

    def test_pop_restores_previous_screen(self):
        stack = ScreenStack()
        stack.push(OverlayScreenId.PAUSE)
        stack.push(OverlayScreenId.SETTINGS)

        popped = stack.pop()

        self.assertEqual(popped, OverlayScreenId.SETTINGS)
        self.assertEqual(stack.current(), OverlayScreenId.PAUSE)
        self.assertEqual(stack.depth(), 1)

    def test_clear_empties_stack(self):
        stack = ScreenStack()
        stack.push(OverlayScreenId.PAUSE)
        stack.push(OverlayScreenId.SETTINGS)

        stack.clear()

        self.assertTrue(stack.is_empty())
        self.assertIsNone(stack.current())
        self.assertEqual(stack.depth(), 0)

    def test_stack_accepts_view_screen_ids(self):
        stack = ScreenStack()

        stack.push(ViewScreenId.MAIN_MENU)

        self.assertEqual(stack.current(), ViewScreenId.MAIN_MENU)


if __name__ == "__main__":
    unittest.main()
