import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sv.ai.enemy_ai import build_path_to_target, can_enemy_notice_player, decide_enemy_action


class DummyScene:
    def __init__(self, entities):
        self.sprite_lists = {"Entities": entities}


class DummyPlayer:
    def __init__(self, tile_x: int, tile_y: int):
        self.tile_x = tile_x
        self.tile_y = tile_y
        self.blocking = True


class DummyEnemy:
    def __init__(self, tile_x: int, tile_y: int):
        self.tile_x = tile_x
        self.tile_y = tile_y
        self.blocking = True
        self.notice_radius = 8
        self.search_turn_limit = 3
        self.is_alerted = False
        self.last_seen_player_tile = None
        self.search_turns_left = 0


class DummyBlocker:
    def __init__(self, tile_x: int, tile_y: int):
        self.tile_x = tile_x
        self.tile_y = tile_y
        self.blocking = True


class EnemyAITests(unittest.TestCase):
    def _apply_move(self, enemy: DummyEnemy, action) -> None:
        if action.kind == "move":
            enemy.tile_x += action.dx
            enemy.tile_y += action.dy

    def test_enemy_waits_when_player_is_outside_radius(self):
        level = [[1 for _ in range(12)] for _ in range(12)]
        enemy = DummyEnemy(0, 0)
        player = DummyPlayer(10, 10)
        scene = DummyScene([enemy, player])

        action = decide_enemy_action(enemy, player, level, scene)

        self.assertEqual(action.kind, "wait")
        self.assertFalse(enemy.is_alerted)

    def test_enemy_does_not_notice_player_through_wall(self):
        level = [
            [1, 1, 1, 1, 1],
            [1, 1, 2, 1, 1],
            [1, 1, 2, 1, 1],
            [1, 1, 2, 1, 1],
            [1, 1, 1, 1, 1],
        ]
        enemy = DummyEnemy(1, 2)
        player = DummyPlayer(3, 2)

        self.assertFalse(can_enemy_notice_player(enemy, player, level))

    def test_enemy_notices_player_in_clear_line_of_sight(self):
        level = [[1 for _ in range(6)] for _ in range(6)]
        enemy = DummyEnemy(1, 1)
        player = DummyPlayer(4, 1)
        scene = DummyScene([enemy, player])

        action = decide_enemy_action(enemy, player, level, scene)

        self.assertEqual(action.kind, "move")
        self.assertTrue(enemy.is_alerted)
        self.assertEqual(enemy.last_seen_player_tile, (4, 1))
        self.assertEqual(enemy.search_turns_left, 3)

    def test_pathfinding_goes_around_wall(self):
        level = [
            [1, 1, 1, 1, 1],
            [1, 1, 2, 1, 1],
            [1, 1, 2, 1, 1],
            [1, 1, 2, 1, 1],
            [1, 1, 1, 1, 1],
        ]
        enemy = DummyEnemy(1, 2)
        player = DummyPlayer(3, 2)
        scene = DummyScene([enemy, player])

        path = build_path_to_target(enemy, (player.tile_x, player.tile_y), level, scene)

        self.assertTrue(path)
        self.assertNotEqual(path[0], (2, 2))

    def test_enemy_remembers_last_seen_position_for_three_turns(self):
        level = [[1 for _ in range(12)] for _ in range(12)]
        enemy = DummyEnemy(0, 0)
        player = DummyPlayer(2, 0)
        scene = DummyScene([enemy, player])

        first_action = decide_enemy_action(enemy, player, level, scene)
        self._apply_move(enemy, first_action)

        player.tile_x = 11
        player.tile_y = 11

        second_action = decide_enemy_action(enemy, player, level, scene)
        self._apply_move(enemy, second_action)
        self.assertEqual(second_action.kind, "move")
        self.assertEqual(enemy.search_turns_left, 2)

        third_action = decide_enemy_action(enemy, player, level, scene)
        self._apply_move(enemy, third_action)
        self.assertEqual(third_action.kind, "wait")
        self.assertTrue(enemy.is_alerted)
        self.assertEqual(enemy.search_turns_left, 1)

        fourth_action = decide_enemy_action(enemy, player, level, scene)
        self._apply_move(enemy, fourth_action)
        self.assertEqual(fourth_action.kind, "wait")
        self.assertFalse(enemy.is_alerted)
        self.assertEqual(enemy.search_turns_left, 0)

    def test_enemy_attacks_when_adjacent(self):
        level = [[1 for _ in range(4)] for _ in range(4)]
        enemy = DummyEnemy(1, 1)
        player = DummyPlayer(2, 2)
        scene = DummyScene([enemy, player])

        action = decide_enemy_action(enemy, player, level, scene)

        self.assertEqual(action.kind, "attack")

    def test_pathfinding_avoids_blocking_entities(self):
        level = [[1 for _ in range(5)] for _ in range(5)]
        enemy = DummyEnemy(0, 2)
        player = DummyPlayer(4, 2)
        blocker = DummyBlocker(1, 2)
        scene = DummyScene([enemy, player, blocker])

        path = build_path_to_target(enemy, (player.tile_x, player.tile_y), level, scene)

        self.assertTrue(path)
        self.assertNotEqual(path[0], (1, 2))


if __name__ == "__main__":
    unittest.main()
