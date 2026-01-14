from enum import Enum


class MoveResult(Enum):
    MOVED = "moved"
    BLOCKED_WALL = "blocked_wall"
    BLOCKED_ENTITY = "blocked_entity"


def is_tile_walkable(level, tx: int, ty: int) -> bool:
    """Возвращает True, если тайл проходим (в пределах уровня и != 0).
    Предположение: level[y][x] — 0 = стена, !=0 = проходимо.
    """
    if level is None:
        return False
    max_y = len(level)
    if max_y == 0:
        return False
    max_x = len(level[0])
    if not (0 <= tx < max_x and 0 <= ty < max_y):
        return False
    try:
        return level[ty][tx] != 0
    except Exception:
        return False


def get_blocking_entity(scene, tx: int, ty: int, ignore=None):
    """Ищет и возвращает первую блокирующую сущность на указанном тайле.
    Ищем по всем спискам спрайтов в scene (если есть атрибут sprite_lists) или через known names.
    """
    if scene is None:
        return None

    # Если Scene имеет атрибут sprite_lists (dict), используем его
    sprite_lists = getattr(scene, "sprite_lists", None)
    if sprite_lists:
        for name, sp in sprite_lists.items():
            try:
                for s in sp:
                    if s is ignore:
                        continue
                    if getattr(s, "tile_x", None) == tx and getattr(s, "tile_y", None) == ty:
                        if getattr(s, "blocking", True):
                            return s
            except Exception:
                continue
        return None

    # Fallback: попробуем некоторые известные списки
    for name in ("Player", "Skeleton"):
        try:
            sp = scene.get_sprite_list(name)
        except Exception:
            sp = None
        if not sp:
            continue
        for s in sp:
            if s is ignore:
                continue
            if getattr(s, "tile_x", None) == tx and getattr(s, "tile_y", None) == ty:
                if getattr(s, "blocking", True):
                    return s
    return None


def can_move(entity, dx: int, dy: int, level, scene) -> tuple[MoveResult, object | None, int | None, int | None]:
    """Проверяет возможность перемещения сущности на (dx,dy) в тайлах.
    Важно: НЕ изменяет tile_x/tile_y и НЕ изменяет мировые координаты.
    Возвращает (MoveResult, blocker, target_tx, target_ty).
    """
    if entity is None:
        return MoveResult.BLOCKED_WALL, None, None, None

    try:
        cur_x = int(getattr(entity, "tile_x"))
        cur_y = int(getattr(entity, "tile_y"))
    except Exception:
        return MoveResult.BLOCKED_WALL, None, None, None

    target_tx = cur_x + int(dx)
    target_ty = cur_y + int(dy)

    if not is_tile_walkable(level, target_tx, target_ty):
        return MoveResult.BLOCKED_WALL, None, target_tx, target_ty

    blocker = get_blocking_entity(scene, target_tx, target_ty, ignore=entity)
    if blocker is not None:
        return MoveResult.BLOCKED_ENTITY, blocker, target_tx, target_ty

    return MoveResult.MOVED, None, target_tx, target_ty


def commit_tile(entity, tx: int, ty: int) -> bool:
    """
    Резервирует тайл для сущности — обновляет tile_x/tile_y без изменения center_x/center_y.
    Это позволяет начать анимацию перемещения, при этом тайл считается занятым.
    """
    if entity is None:
        return False
    try:
        entity.tile_x = int(tx)
        entity.tile_y = int(ty)
        return True
    except Exception:
        return False


def attempt_move(entity, dx: int, dy: int, level, scene) -> tuple[MoveResult, object | None]:
    """
    Попытка перемещения сущности на (dx,dy) в тайлах.
    Возвращает (MoveResult, blocker).
    Эта функция оставлена для обратной совместимости: она сразу обновляет мировые координаты.
    """
    # Используем can_move для проверки
    res, blocker, target_tx, target_ty = can_move(entity, dx, dy, level, scene)
    if res != MoveResult.MOVED:
        return res, blocker

    # Коммит перемещения: обновим tile и мировые координаты
    try:
        entity.tile_x = target_tx
        entity.tile_y = target_ty
        # Пытаемся получить TILE_SIZE из Settings
        try:
            from sv.core import Settings
            TILE_SIZE = Settings.TILE_SIZE
        except Exception:
            TILE_SIZE = 32
        entity.center_x = target_tx * TILE_SIZE + TILE_SIZE // 2
        entity.center_y = target_ty * TILE_SIZE + TILE_SIZE // 2
    except Exception:
        return MoveResult.BLOCKED_WALL, None

    return MoveResult.MOVED, None
