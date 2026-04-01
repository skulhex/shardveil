"""Типы тайлов для уровня."""

from collections.abc import Iterable

VOID = 0
FLOOR = 1
WALL = 2
STAIRS = 3

WALKABLE = (FLOOR, STAIRS)
TRANSPARENT = (FLOOR, STAIRS)


def is_tile_in(level, tx: int, ty: int, allowed: Iterable[int]) -> bool:
    """Проверяет, что тайл существует и входит в указанный набор значений."""
    if level is None:
        return False
    max_y = len(level)
    if max_y == 0:
        return False
    max_x = len(level[0])
    if not (0 <= tx < max_x and 0 <= ty < max_y):
        return False
    return level[ty][tx] in tuple(allowed)


def is_tile_walkable(level, tx: int, ty: int) -> bool:
    """Возвращает True, если тайл проходим для движения."""
    return is_tile_in(level, tx, ty, WALKABLE)


def is_tile_transparent(level, tx: int, ty: int) -> bool:
    """Возвращает True, если тайл не блокирует линию обзора."""
    return is_tile_in(level, tx, ty, TRANSPARENT)


def build_tile_mask(level, allowed: Iterable[int]) -> list[list[bool]]:
    """Строит булеву матрицу по набору разрешённых типов тайлов."""
    if not level:
        return []
    allowed_values = tuple(allowed)
    return [[tile in allowed_values for tile in row] for row in level]


def build_walkable_mask(level) -> list[list[bool]]:
    """Строит булеву матрицу проходимости."""
    return build_tile_mask(level, WALKABLE)


def build_transparency_mask(level) -> list[list[bool]]:
    """Строит булеву матрицу прозрачности для проверки видимости."""
    return build_tile_mask(level, TRANSPARENT)
