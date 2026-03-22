from dataclasses import dataclass

import numpy as np
import tcod.map
import tcod.path
from tcod import libtcodpy

from sv.core.collision import iter_blocking_entities
from sv.world.tiles import build_transparency_mask, build_walkable_mask


@dataclass(slots=True)
class EnemyAction:
    kind: str
    dx: int = 0
    dy: int = 0

def _is_adjacent(enemy, player) -> bool:
    return max(abs(enemy.tile_x - player.tile_x), abs(enemy.tile_y - player.tile_y)) == 1


def _build_cost_map(level, scene, actor, goal_tile: tuple[int, int] | None) -> np.ndarray:
    walkable_mask = np.array(build_walkable_mask(level), dtype=np.int8, order="C")
    if walkable_mask.size == 0:
        return walkable_mask

    goal_x, goal_y = goal_tile if goal_tile is not None else (None, None)
    for entity in iter_blocking_entities(scene, ignore=actor):
        ex = getattr(entity, "tile_x", None)
        ey = getattr(entity, "tile_y", None)
        if ex is None or ey is None:
            continue
        if goal_tile is not None and (ex, ey) == (goal_x, goal_y):
            continue
        if 0 <= ey < walkable_mask.shape[0] and 0 <= ex < walkable_mask.shape[1]:
            walkable_mask[ey, ex] = 0

    if goal_tile is not None and 0 <= goal_y < walkable_mask.shape[0] and 0 <= goal_x < walkable_mask.shape[1]:
        walkable_mask[goal_y, goal_x] = 1

    return walkable_mask


def can_enemy_notice_player(enemy, player, level) -> bool:
    if enemy is None or player is None:
        return False

    radius = max(0, int(getattr(enemy, "notice_radius", 0)))
    if max(abs(enemy.tile_x - player.tile_x), abs(enemy.tile_y - player.tile_y)) > radius:
        return False

    transparency = np.array(build_transparency_mask(level), dtype=bool, order="C")
    if transparency.size == 0:
        return False

    visible = tcod.map.compute_fov(
        transparency,
        (enemy.tile_y, enemy.tile_x),
        radius=radius,
        light_walls=True,
        algorithm=libtcodpy.FOV_RESTRICTIVE,
    )
    return bool(visible[player.tile_y, player.tile_x])


def build_path_to_target(enemy, goal_tile: tuple[int, int], level, scene) -> list[tuple[int, int]]:
    cost = _build_cost_map(level, scene, enemy, goal_tile)
    if cost.size == 0:
        return []

    goal_x, goal_y = goal_tile
    if not (0 <= goal_y < cost.shape[0] and 0 <= goal_x < cost.shape[1]):
        return []
    if cost[goal_y, goal_x] <= 0:
        return []

    graph = tcod.path.SimpleGraph(cost=cost, cardinal=2, diagonal=3)
    pathfinder = tcod.path.Pathfinder(graph)
    pathfinder.add_root((goal_y, goal_x))

    raw_path = pathfinder.path_from((enemy.tile_y, enemy.tile_x))[1:].tolist()
    return [(step_x, step_y) for step_y, step_x in raw_path]


def choose_movement_action(enemy, goal_tile: tuple[int, int], level, scene) -> EnemyAction:
    path = build_path_to_target(enemy, goal_tile, level, scene)
    if not path:
        return EnemyAction("wait")

    next_x, next_y = path[0]
    return EnemyAction("move", dx=next_x - enemy.tile_x, dy=next_y - enemy.tile_y)


def _reset_alert(enemy) -> None:
    enemy.is_alerted = False
    enemy.last_seen_player_tile = None
    enemy.search_turns_left = 0


def decide_enemy_action(enemy, player, level, scene) -> EnemyAction:
    if enemy is None or player is None:
        return EnemyAction("wait")

    if _is_adjacent(enemy, player):
        enemy.is_alerted = True
        enemy.last_seen_player_tile = (player.tile_x, player.tile_y)
        enemy.search_turns_left = int(getattr(enemy, "search_turn_limit", 0))
        return EnemyAction("attack")

    if can_enemy_notice_player(enemy, player, level):
        enemy.is_alerted = True
        enemy.last_seen_player_tile = (player.tile_x, player.tile_y)
        enemy.search_turns_left = int(getattr(enemy, "search_turn_limit", 0))
        return choose_movement_action(enemy, enemy.last_seen_player_tile, level, scene)

    if enemy.is_alerted and enemy.last_seen_player_tile is not None and enemy.search_turns_left > 0:
        enemy.search_turns_left -= 1
        action = choose_movement_action(enemy, enemy.last_seen_player_tile, level, scene)
        if enemy.search_turns_left <= 0 and action.kind == "wait":
            _reset_alert(enemy)
        elif enemy.search_turns_left <= 0 and (enemy.tile_x, enemy.tile_y) == enemy.last_seen_player_tile:
            _reset_alert(enemy)
        return action

    _reset_alert(enemy)
    return EnemyAction("wait")
