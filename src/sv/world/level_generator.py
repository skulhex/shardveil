"""Процедурный генератор уровней BSP с использованием tcod."""
import random
from typing import Any
import tcod.bsp
import tcod.los
from .tiles import FLOOR, STAIRS, WALL


def _tunnel_between(
    start: tuple[int, int], end: tuple[int, int]
) -> list[tuple[int, int]]:
    """Возвращает координаты L-образного туннеля между двумя точками."""
    x1, y1 = start
    x2, y2 = end
    if random.random() < 0.5:
        corner_x, corner_y = x2, y1
    else:
        corner_x, corner_y = x1, y2
    points: list[tuple[int, int]] = []
    for pt in tcod.los.bresenham((x1, y1), (corner_x, corner_y)).tolist():
        points.append((pt[0], pt[1]))
    for pt in tcod.los.bresenham((corner_x, corner_y), (x2, y2)).tolist():
        points.append((pt[0], pt[1]))
    return points


class LevelGenerator:
    def __init__(
        self,
        width: int = 80,
        height: int = 50,
        *,
        bsp_depth: int = 5,
        room_min_size: int = 3,
        room_max_size_ratio: float = 0.8,
    ):
        self.width = width
        self.height = height
        self.bsp_depth = bsp_depth
        self.room_min_size = room_min_size
        self.room_max_size_ratio = room_max_size_ratio

    def generate(self) -> tuple[list[list[int]], tuple[int, int], tuple[int, int]]:
        """
        Генерирует уровень BSP. Возвращает (level, player_spawn_xy, stairs_xy).
        level[y][x]: 0=void, 1=floor, 2=wall, 3=stairs.
        """
        level: list[list[int]] = [
            [WALL for _ in range(self.width)] for _ in range(self.height)
        ]

        bsp = tcod.bsp.BSP(x=0, y=0, width=self.width, height=self.height)
        bsp.split_recursive(
            depth=self.bsp_depth,
            min_width=self.room_min_size + 2,
            min_height=self.room_min_size + 2,
            max_horizontal_ratio=1.5,
            max_vertical_ratio=1.5,
        )

        # Список (x1, y1, x2, y2) границ комнат для спавна/лестниц
        rooms: list[tuple[int, int, int, int]] = []

        def _carve_room(
            node: Any, x1: int, y1: int, x2: int, y2: int
        ) -> tuple[int, int]:
            for y in range(y1, y2 + 1):
                for x in range(x1, x2 + 1):
                    if 0 <= y < self.height and 0 <= x < self.width:
                        level[y][x] = FLOOR
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            return (cx, cy)

        def _process_node(node: Any) -> tuple[int, int] | None:
            if node.children:
                left, right = node.children
                c1 = _process_node(left)
                c2 = _process_node(right)
                if c1 is not None and c2 is not None:
                    for x, y in _tunnel_between(c1, c2):
                        if 0 <= y < self.height and 0 <= x < self.width:
                            level[y][x] = FLOOR
                return c1 if c1 is not None else c2

            # Leaf: вырезаем комнату с отступом 1 от краев разделителя
            # node: x, y, width, height
            w = max(0, node.width - 2)
            h = max(0, node.height - 2)
            if w < self.room_min_size or h < self.room_min_size:
                return None
            high_rw = min(int(w * self.room_max_size_ratio) or self.room_min_size, w)
            high_rh = min(int(h * self.room_max_size_ratio) or self.room_min_size, h)
            if high_rw < self.room_min_size or high_rh < self.room_min_size:
                return None
            rw = random.randint(self.room_min_size, high_rw)
            rh = random.randint(self.room_min_size, high_rh)
            # позиция внутри узла с отступом 1
            rx = node.x + 1 + random.randint(0, w - rw) if w > rw else node.x + 1
            ry = node.y + 1 + random.randint(0, h - rh) if h > rh else node.y + 1
            x1, y1 = rx, ry
            x2, y2 = rx + rw - 1, ry + rh - 1
            center = _carve_room(node, x1, y1, x2, y2)
            rooms.append((x1, y1, x2, y2))
            return center

        _process_node(bsp)

        if not rooms:
            # fallback: одна комната в центре
            cx, cy = self.width // 2, self.height // 2
            for y in range(cy - 2, cy + 3):
                for x in range(cx - 2, cx + 3):
                    if 0 <= y < self.height and 0 <= x < self.width:
                        level[y][x] = FLOOR
            spawn_xy = (cx, cy)
            stairs_xy = (cx + 1, cy)
            sx, sy = stairs_xy
            if 0 <= sy < self.height and 0 <= sx < self.width:
                level[sy][sx] = STAIRS
            return (level, spawn_xy, stairs_xy)

        # Спавн в центре первой комнаты
        x1, y1, x2, y2 = rooms[0]
        spawn_xy = ((x1 + x2) // 2, (y1 + y2) // 2)

        # Лестница в другой комнате (не спавн-комнате)
        stairs_xy = spawn_xy
        other_rooms = rooms[1:]
        if other_rooms:
            sr = random.choice(other_rooms)
            sx1, sy1, sx2, sy2 = sr
            # случайный пол в этой комнате
            sx = random.randint(sx1, sx2)
            sy = random.randint(sy1, sy2)
            level[sy][sx] = STAIRS
            stairs_xy = (sx, sy)
        else:
            # если комнатa одна — разместим лестницу внутри неё, но не в точке спавна
            placed = False
            for y in range(y1, y2 + 1):
                for x in range(x1, x2 + 1):
                    if (x, y) == spawn_xy:
                        continue
                    level[y][x] = STAIRS
                    stairs_xy = (x, y)
                    placed = True
                    break
                if placed:
                    break

        return (level, spawn_xy, stairs_xy)
