import random
import sys
import time
from collections import deque
from pathlib import Path
import arcade
from arcade import gui
from arcade import gl
from arcade.future.light import Light, LightLayer
from sv.core import (
    CameraController,
    GamePhase,
    MovementInputState,
    Settings,
    StateManager,
    snap_world_point,
)
from sv.world import LevelGenerator
from sv.entities import Player, Skeleton
from sv.ai import decide_enemy_action
from sv.core.collision import MoveResult
from sv.ui import GameUI, HUDLayer, OverlayScreenId, ViewScreenId

TILE_SIZE = Settings.TILE_SIZE
PLAYER_INPUT_DIAGONAL_WINDOW = 0.02
PLAYER_HORIZONTAL_KEYS = {
    arcade.key.A: -1,
    arcade.key.LEFT: -1,
    arcade.key.D: 1,
    arcade.key.RIGHT: 1,
}
PLAYER_VERTICAL_KEYS = {
    arcade.key.W: 1,
    arcade.key.UP: 1,
    arcade.key.S: -1,
    arcade.key.DOWN: -1,
}
PLAYER_DIRECTION_KEYS = tuple(PLAYER_HORIZONTAL_KEYS) + tuple(PLAYER_VERTICAL_KEYS)

# Путь к папке assets
asset_dir = Path(sys.argv[0]).resolve().parents[1] / "assets"
# Регистрируем ресурс-хэндл для удобной загрузки ассетов
arcade.resources.add_resource_handle("assets", asset_dir)

# отключение сглаживания для пиксельной графики
arcade.SpriteList.DEFAULT_TEXTURE_FILTER = gl.NEAREST, gl.NEAREST

class Game(arcade.Window):
    def __init__(self):
        self.settings = Settings()
        super().__init__(
            width=self.settings.screen_width,
            height=self.settings.screen_height,
            title=self.settings.title
        )

        self.ui_manager = gui.UIManager()
        self.ui = GameUI(
            self.ui_manager,
            HUDLayer(),
            on_resume=self._resume_game,
            on_main_menu=self._return_to_main_menu,
            on_new_game=self.start_new_game,
            on_exit_game=self.close,
        )
        
        self.level = None
        self.scene = None
        self.player_sprite = None
        self.camera = None
        self.camera_controller = None
        self.light_layer = None
        self.player_light = None
        self.state = StateManager()
        # Очередь врагов для последовательной обработки
        self._enemy_queue: deque = deque()
        self._current_enemy = None
        self.movement_input = MovementInputState(
            PLAYER_HORIZONTAL_KEYS,
            PLAYER_VERTICAL_KEYS,
            diagonal_window=PLAYER_INPUT_DIAGONAL_WINDOW,
        )

    def setup(self):
        self.ui.setup()
        self.start_new_game()

    def start_new_game(self) -> None:
        self.ui.clear_view_screen()
        self.ui.clear_overlay()
        self.ui.set_hud_visible(True)
        self.movement_input.clear()
        self._enemy_queue.clear()
        self._current_enemy = None

        # Генерируем уровень (BSP: 0=void, 1=floor, 2=wall, 3=stairs)
        gen = LevelGenerator(width=64, height=48)
        level, spawn_xy, stairs_xy = gen.generate()

        # Создаём сцену
        self.level = level
        world_width = len(level[0]) * TILE_SIZE
        world_height = len(level) * TILE_SIZE
        self.scene = arcade.Scene()
        self.scene.add_sprite_list("Ground")
        self.scene.add_sprite_list("Walls")
        self.scene.add_sprite_list("Player")
        self.scene.add_sprite_list("Skeleton")

        # Загрузка спрайтшита с тайлами
        tileset_image = ":assets:/sprites/tileset.png"

        # Загрузка тайлов из спрайтшита
        tiles = arcade.load_spritesheet(tileset_image)
        textures = tiles.get_texture_grid((TILE_SIZE, TILE_SIZE), columns=3, count=3)

        # Назначение текстур для пола и стен
        floor_texture = textures[0]
        wall_texture = textures[1]
        stairs_texture = textures[2]

        for y in range(len(level)):
            for x in range(len(level[0])):
                tile = level[y][x]
                world_x = x * TILE_SIZE
                world_y = y * TILE_SIZE

                if tile == 0:
                    # void — не рисуем
                    continue
                if tile == 1:
                    # floor
                    sprite = arcade.Sprite()
                    sprite.texture = floor_texture
                    sprite.center_x = world_x + TILE_SIZE / 2
                    sprite.center_y = world_y + TILE_SIZE / 2
                    self.scene["Ground"].append(sprite)
                elif tile == 3:
                    # stairs
                    sprite = arcade.Sprite()
                    sprite.texture = stairs_texture
                    sprite.center_x = world_x + TILE_SIZE / 2
                    sprite.center_y = world_y + TILE_SIZE / 2
                    self.scene["Ground"].append(sprite)
                elif tile == 2:
                    sprite = arcade.Sprite()
                    sprite.texture = wall_texture
                    sprite.center_x = world_x + TILE_SIZE / 2
                    sprite.center_y = world_y + TILE_SIZE / 2
                    self.scene["Walls"].append(sprite)

        # Создаём игрока в точке спавна с генератора
        self.player_sprite = Player(tile_x=spawn_xy[0], tile_y=spawn_xy[1])
        self.scene.add_sprite("Player", self.player_sprite)
        # Настраиваем камеру
        self.camera = arcade.camera.Camera2D(position=self.player_sprite.position, zoom=2.0)
        self.camera_controller = CameraController(
            self.camera,
            world_width=world_width,
            world_height=world_height,
            initial_zoom=2.0,
        )

        # Скелет на случайном полу, не на спавне и не на лестнице
        floor_tiles = [
            (x, y)
            for y in range(len(level))
            for x in range(len(level[0]))
            if level[y][x] in (1, 3)
            and (x, y) != spawn_xy
            and (x, y) != stairs_xy
        ]
        if floor_tiles:
            sx, sy = random.choice(floor_tiles)
            skeleton = Skeleton(tile_x=sx, tile_y=sy)
        else:
            skeleton = Skeleton(tile_x=spawn_xy[0] + 1, tile_y=spawn_xy[1])
        self.scene.add_sprite("Skeleton", skeleton)

        # Подключаем базовый световой слой через arcade.gl
        self.light_layer = LightLayer(self.settings.screen_width, self.settings.screen_height)
        self.light_layer.set_background_color((0, 0, 0, 255))
        self.player_light = Light(
            self.player_sprite.center_x,
            self.player_sprite.center_y,
            radius=180,
            color=(255, 244, 216),
            mode="soft",
        )
        self.light_layer.add(self.player_light)

        self.state.enter_game()

    def on_resize(self, width, height):
        super().on_resize(width, height)
        if self.camera_controller is not None:
            self.camera_controller.on_resize(width, height)
        elif self.camera is not None:
            self.camera.match_window()
        if self.light_layer is not None:
            self.light_layer.resize(width, height)

    def on_draw(self):
        self.clear()
        if self.state.is_in_game() and self.light_layer is not None and self.camera is not None and self.scene is not None:
            with self.light_layer:
                self.camera.use()
                self.scene.draw()
            self.light_layer.draw(ambient_color=(28, 24, 34, 255))
        self.ui.draw()

    def on_update(self, delta_time):
        if self.state.is_in_game() and self.player_sprite is not None:
            self.ui.update_hud(
                self.player_sprite.hp / self.player_sprite.max_hp,
                self._player_light_ratio(),
            )

        if not self.state.is_in_game() or self.state.is_paused():
            return

        # Обновляем сцену, чтобы вызвать Sprite.update на всех спрайтах (анимация движения)
        if self.scene:
            self.scene.update(delta_time)

        if self.camera_controller is not None and self.player_sprite is not None:
            self.camera_controller.update(self.player_sprite.position, delta_time)

        self._snap_moving_sprites()

        # После снапа спрайтов обновляем свет, чтобы он оставался привязанным к рендеру игрока.
        if self.player_light is not None and self.player_sprite is not None:
            self.player_light.position = self.player_sprite.position
            ratio = self._player_light_ratio()
            self.player_light.radius = 160 + 35 * ratio

        now = time.time()

        # Если игрок завершил свою анимацию — запускаем очередь врагов
        if self.state.is_player_anim():
            if not getattr(self.player_sprite, "moving", False):
                self.state.set_phase(GamePhase.ENEMY_TURN)
                self.process_enemy_turns()
                return

        self._process_player_movement(now)

    def _player_light_ratio(self) -> float:
        if not self.player_sprite:
            return 0.0
        try:
            return self.player_sprite.light_ratio()
        except Exception:
            return 0.0

    def _recover_player_light(self, amount: int) -> int:
        if not self.player_sprite:
            return 0
        try:
            return self.player_sprite.recover_light(amount)
        except Exception:
            return 0

    def _consume_player_light(self, amount: int = 1) -> int:
        if not self.player_sprite:
            return 0
        try:
            return self.player_sprite.spend_light(amount)
        except Exception:
            return 0

    def get_entity_at(self, tile_x: int, tile_y: int, list_name: str | None = None):
        """Возвращает сущность в списке по координатам тайла, либо None."""
        if self.scene is None:
            return None
        # Если указано имя списка - ищем только в нём
        if list_name:
            sprites = self.scene.get_sprite_list(list_name)
            if sprites:
                for s in sprites:
                    if getattr(s, "tile_x", None) == tile_x and getattr(s, "tile_y", None) == tile_y:
                        return s
            return None

        # Иначе проверяем по всем основным спискам сущностей (можно расширить)
        for name in ("Player", "Skeleton"):
            sprites = self.scene.get_sprite_list(name)
            if sprites:
                for s in sprites:
                    if getattr(s, "tile_x", None) == tile_x and getattr(s, "tile_y", None) == tile_y:
                        return s
        return None

    def on_key_press(self, symbol, modifiers):
        if self.ui.handle_key_press(symbol, modifiers):
            return

        if symbol == arcade.key.ESCAPE:
            self._pause_game()
            return

        if not self.state.is_in_game():
            return

        # Зум камеры, не должен зависеть от порядка ходов.
        if symbol in (arcade.key.PLUS, arcade.key.EQUAL):
            if self.camera_controller is not None:
                self.camera_controller.zoom_in()
            return
        if symbol in (arcade.key.MINUS, arcade.key.UNDERSCORE):
            if self.camera_controller is not None:
                self.camera_controller.zoom_out()
            return

        now = time.time()

        if symbol in PLAYER_DIRECTION_KEYS:
            self.movement_input.press(symbol, now)
            self._process_player_movement(now)
            return

        # Игрок может действовать только в свой ход
        if not self.state.is_player_turn():
            return

        # Пропуск хода по пробелу
        if symbol == arcade.key.SPACE:
            self._recover_player_light(2)
            self.state.set_phase(GamePhase.ENEMY_TURN)
            self.process_enemy_turns()
            return

    def _move_with_fallback(self, entity, dx, dy):
        """Попытка перемещения с fallback по осям при диагональном столкновении со стеной."""
        res, blocker = entity.attempt_move(dx, dy, self.level, self.scene)
        if res == MoveResult.MOVED:
            return res, blocker
        if dx != 0 and dy != 0 and res == MoveResult.BLOCKED_WALL:
            res2, blocker2 = entity.attempt_move(dx, 0, self.level, self.scene)
            if res2 == MoveResult.MOVED:
                return res2, blocker2
            res3, blocker3 = entity.attempt_move(0, dy, self.level, self.scene)
            return res3, blocker3
        return res, blocker

    def _try_player_move(self, dx, dy):
        """Попытка перемещения игрока с управлением сменой хода."""
        res, blocker = self._move_with_fallback(self.player_sprite, dx, dy)
        if res is None:
            return None, None
        if res == MoveResult.BLOCKED_WALL:
            return res, blocker
        if res == MoveResult.BLOCKED_ENTITY:
            if blocker is not None and hasattr(self.player_sprite, 'attack'):
                self.player_sprite.attack(blocker)
                self._consume_player_light(1)
            self.state.set_phase(GamePhase.ENEMY_TURN)
            self.process_enemy_turns()
            return res, blocker
        if res == MoveResult.MOVED:
            self._consume_player_light(1)
            self.state.set_phase(GamePhase.PLAYER_ANIM)
            return res, blocker
        return res, blocker

    def on_key_release(self, symbol, modifiers):
        if not self.state.is_in_game() or self.ui.has_active_overlay():
            return
        self.movement_input.release(symbol, time.time())

    def _process_player_movement(self, now: float):
        if not self.state.is_player_turn():
            return

        move = self.movement_input.resolve_move(now)
        if move is None:
            return

        dx, dy = move
        res, _ = self._try_player_move(dx, dy)
        if res == MoveResult.BLOCKED_WALL:
            self.movement_input.mark_blocked(dx, dy)

    def _snap_moving_sprites(self):
        if self.scene is None:
            return

        zoom = self.camera_controller.zoom if self.camera_controller is not None else self.camera.zoom
        sprite_lists = getattr(self.scene, "sprite_lists", {})
        for sprites in sprite_lists.values():
            for sprite in sprites:
                if not getattr(sprite, "moving", False):
                    continue
                snapped_x, snapped_y = snap_world_point(sprite.center_x, sprite.center_y, zoom)
                sprite.position = (snapped_x, snapped_y)

    def process_enemy_turns(self):
        """Запускает последовательную обработку ходов всех врагов с ожиданием их анимаций."""
        if self.state.is_paused() or self.scene is None:
            return
        # Сформируем очередь живых врагов
        enemies = list(self.scene.get_sprite_list("Skeleton") or [])
        self._enemy_queue = deque(e for e in enemies if not getattr(e, 'removed', False))
        self._current_enemy = None
        # Запускаем обработку
        self._process_next_enemy()

    def _process_next_enemy(self):
        """
        Обрабатывает следующий враг из очереди. Если враг начинает анимацию — ждём её завершения.
        Иначе продолжаем к следующему врагу. По окончании возвращаем ход игроку.
        """
        if self.state.is_paused():
            return

        while self._enemy_queue:
            enemy = self._enemy_queue.popleft()
            # Пропуск мёртвых/удалённых сущностей
            if getattr(enemy, "removed", False):
                continue
            action = decide_enemy_action(enemy, self.player_sprite, self.level, self.scene)

            if action.kind == "wait":
                continue

            if action.kind == "attack":
                if hasattr(enemy, "attack"):
                    enemy.attack(self.player_sprite)
                continue

            if action.kind != "move":
                continue

            res, blocker = self._move_with_fallback(enemy, action.dx, action.dy)
            if res == MoveResult.BLOCKED_WALL:
                continue
            if res == MoveResult.BLOCKED_ENTITY:
                if blocker is self.player_sprite:
                    enemy.attack(self.player_sprite)
                continue
            if res == MoveResult.MOVED:
                self._current_enemy = enemy

                def _make_callback(e):
                    def cb():
                        e.on_move_complete = None
                        self._current_enemy = None
                        self._process_next_enemy()
                    return cb

                enemy.on_move_complete = _make_callback(enemy)
                # ждем завершения анимации — выходим, дальнейшая обработка продолжится в callback
                return
            continue

        # Очередь пуста — возвращаем ход игроку
        self.state.set_phase(GamePhase.PLAYER_TURN)

    def _pause_game(self) -> None:
        if not self.state.pause():
            return
        self.movement_input.clear()
        self.ui.show_screen(OverlayScreenId.PAUSE)

    def _resume_game(self) -> None:
        if not self.state.resume():
            return
        self.movement_input.clear()
        self.ui.clear_overlay()

    def _return_to_main_menu(self) -> None:
        self.state.enter_main_menu()
        self.movement_input.clear()
        self.ui.clear_overlay()
        self.ui.set_hud_visible(False)
        self.ui.show_view_screen(ViewScreenId.MAIN_MENU)


def main():
    game = Game()
    game.setup()
    arcade.run()

if __name__ == "__main__":
    main()
