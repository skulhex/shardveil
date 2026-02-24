import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sv.core.collision import MoveResult, can_move


class DummyEntity:
    def __init__(self, tile_x, tile_y, blocking=True):
        self.tile_x = tile_x
        self.tile_y = tile_y
        self.blocking = blocking


class NonBlockingEntity:
    def __init__(self, tile_x, tile_y):
        self.tile_x = tile_x
        self.tile_y = tile_y


class DummyScene:
    def __init__(self, entities):
        self.sprite_lists = {"Entities": entities}


class CollisionTests(unittest.TestCase):
    def setUp(self):
        # 2x2 all-walkable map
        self.level = [
            [1, 1],
            [1, 1],
        ]

    def test_can_move_to_empty_walkable_tile(self):
        mover = DummyEntity(0, 0, blocking=True)
        scene = DummyScene([mover])

        res, blocker, tx, ty = can_move(mover, 1, 0, self.level, scene)
        self.assertEqual(res, MoveResult.MOVED)
        self.assertIsNone(blocker)
        self.assertEqual((tx, ty), (1, 0))

    def test_non_blocking_entity_does_not_block(self):
        mover = DummyEntity(0, 0, blocking=True)
        item = NonBlockingEntity(1, 0)
        scene = DummyScene([mover, item])

        res, blocker, _, _ = can_move(mover, 1, 0, self.level, scene)
        self.assertEqual(res, MoveResult.MOVED)
        self.assertIsNone(blocker)

    def test_blocking_entity_blocks_move(self):
        mover = DummyEntity(0, 0, blocking=True)
        walling_entity = DummyEntity(1, 0, blocking=True)
        scene = DummyScene([mover, walling_entity])

        res, blocker, _, _ = can_move(mover, 1, 0, self.level, scene)
        self.assertEqual(res, MoveResult.BLOCKED_ENTITY)
        self.assertIs(blocker, walling_entity)


if __name__ == "__main__":
    unittest.main()
