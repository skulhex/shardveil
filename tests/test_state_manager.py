import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sv.core.state_manager import AppView, GamePhase, StateManager


class StateManagerTests(unittest.TestCase):
    def test_defaults_to_main_menu_without_phase(self):
        state = StateManager()

        self.assertEqual(state.view, AppView.MAIN_MENU)
        self.assertIsNone(state.phase)
        self.assertTrue(state.is_main_menu())
        self.assertFalse(state.is_in_game())

    def test_enter_game_sets_in_game_player_turn(self):
        state = StateManager()

        state.enter_game()

        self.assertEqual(state.view, AppView.IN_GAME)
        self.assertEqual(state.phase, GamePhase.PLAYER_TURN)
        self.assertTrue(state.is_player_turn())

    def test_set_phase_is_no_op_outside_game(self):
        state = StateManager()

        state.set_phase(GamePhase.ENEMY_TURN)

        self.assertIsNone(state.phase)
        self.assertTrue(state.is_main_menu())

    def test_set_phase_changes_phase_in_game(self):
        state = StateManager()
        state.enter_game()

        state.set_phase(GamePhase.ENEMY_TURN)

        self.assertEqual(state.phase, GamePhase.ENEMY_TURN)
        self.assertTrue(state.is_enemy_turn())

    def test_enter_main_menu_clears_game_phase(self):
        state = StateManager()
        state.enter_game(GamePhase.ENEMY_TURN)

        state.enter_main_menu()

        self.assertEqual(state.view, AppView.MAIN_MENU)
        self.assertIsNone(state.phase)
        self.assertTrue(state.is_main_menu())

    def test_toggle_pause_is_no_op_in_main_menu(self):
        state = StateManager()

        changed = state.toggle_pause()

        self.assertFalse(changed)
        self.assertEqual(state.view, AppView.MAIN_MENU)
        self.assertIsNone(state.phase)

    def test_toggle_pause_round_trips_player_turn(self):
        state = StateManager()
        state.enter_game()

        paused = state.toggle_pause()
        resumed = state.toggle_pause()

        self.assertTrue(paused)
        self.assertTrue(resumed)
        self.assertEqual(state.phase, GamePhase.PLAYER_TURN)

    def test_toggle_pause_restores_previous_phase(self):
        state = StateManager()
        state.enter_game(GamePhase.ENEMY_TURN)

        state.toggle_pause()
        state.toggle_pause()

        self.assertEqual(state.phase, GamePhase.ENEMY_TURN)


if __name__ == "__main__":
    unittest.main()
