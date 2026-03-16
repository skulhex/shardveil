import sys
from pathlib import Path
import unittest
from importlib.util import find_spec


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sv.world.tiles import WALKABLE, STAIRS

HAS_TCOD = find_spec("tcod") is not None

class LevelGeneratorTests(unittest.TestCase):
    @unittest.skipUnless(HAS_TCOD, "tcod is required for level generation tests")
    def test_generate_returns_valid_level_and_points(self):
        from sv.world.level_generator import LevelGenerator

        gen = LevelGenerator(width=40, height=30)
        level, spawn_xy, stairs_xy = gen.generate()

        self.assertEqual(len(level), 30)
        self.assertEqual(len(level[0]), 40)

        sx, sy = spawn_xy
        tx, ty = stairs_xy
        self.assertTrue(0 <= sx < 40 and 0 <= sy < 30)
        self.assertTrue(0 <= tx < 40 and 0 <= ty < 30)

        self.assertIn(level[sy][sx], WALKABLE)
        self.assertIn(level[ty][tx], WALKABLE)
        self.assertEqual(level[ty][tx], STAIRS)


if __name__ == "__main__":
    unittest.main()
