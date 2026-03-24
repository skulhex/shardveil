import random
import sys
import time
from collections import deque
from pathlib import Path
import arcade
from arcade import gl
from arcade.future.light import Light, LightLayer
from sv.core import CameraController, Settings, snap_world_point
from sv.world import LevelGenerator
from sv.entities import Player, Skeleton
from sv.ai import decide_enemy_action
from sv.core.collision import MoveResult
from sv.ui import ProgressBar

TILE_SIZE = Settings.TILE_SIZE
# Время в секундах для учета двойных нажатий клавиш направления (для диагоналей)
DIAGONAL_TOLERANCE = 0.01

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

        # HUD, etc
        self.ui = arcade.gui.UIManager()
        self.ui.enable()
        
        self.level = None
        self.scene = None
        self.player_sprite = None
        self.camera = None
        self.camera_controller = None
        self.light_layer = None
        self.player_light = None
        self.light_pbar = None
        # Состояние хода: "player" или другие состояния
        self.turn = "player"
        # Очередь врагов для последовательной обработки
        self._enemy_queue: deque = deque()
        self._current_enemy = None
        # Набор текущих зажатых клавиш (для поддержки диагоналей)
        # Будем в этот set класть только ключи-направления
        self._pressed_keys: set[int] = set()
        # Временные метки последних нажатий клавиш (symbol -> timestamp)
        # Не удаляем метки при отпускании, чтобы учесть недавние нажатия в окне tolerance
        self._key_timestamps: dict[int, float] = {}

        # Буфер ожидаемого хода: {'time': float, 'dx': int, 'dy': int}
        self._pending_move: dict | None = None

    def setup(self):
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
        
        # Создаем hud bar

        # Инициализируем подложку
        self.hud_anchor = arcade.gui.UIAnchorLayout()
        self.bars_layout = arcade.gui.UIBoxLayout(vertical=False, 
                                                  space_between=20, align="center")
        # Инициализируем бар и добавляем в подложку
        self.pbar = ProgressBar(color=arcade.color.RED, 
                                value=1.0, width=200, height=15)
        self.bars_layout.add(self.pbar)
        self.light_pbar = ProgressBar(color=arcade.color.GOLD, 
                                       value=1.0, width=200, height=15)
        self.bars_layout.add(self.light_pbar)
        self.hud_anchor.add(self.bars_layout, anchor_x="left", 
                            anchor_y="bottom", align_y=10, align_x=8)

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

        # Добавляем подложку в UI
        self.ui.add(self.hud_anchor)

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
        with self.light_layer:
            self.camera.use()
            self.scene.draw()
        self.light_layer.draw(ambient_color=(28, 24, 34, 255))
        self.ui.draw()

    def on_update(self, delta_time):
        # Обновляем значение hp(хп * флоат_значение)
        self.pbar.value = self.player_sprite.hp / self.player_sprite.max_hp
        self.pbar.update_bar()
        self.light_pbar.value = self._player_light_ratio()
        self.light_pbar.update_bar()

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

        # Небольшая очистка старых меток нажатий, чтобы словарь не рос бесконечно
        now = time.time()
        to_del = [k for k, t in self._key_timestamps.items() if now - t > DIAGONAL_TOLERANCE * 3]
        for k in to_del:
            self._key_timestamps.pop(k, None)

        # Если ход уже не наш — сбрасываем отложенное движение
        if self.turn != "player" and self._pending_move is not None:
            self._pending_move = None

        # Если есть отложенный ход и он просрочен — выполним его
        if self._pending_move is not None:
            if now - self._pending_move.get('time', 0.0) >= DIAGONAL_TOLERANCE:
                pdx = self._pending_move.get('dx', 0)
                pdy = self._pending_move.get('dy', 0)
                self._pending_move = None
                if self.turn == 'player' and (pdx != 0 or pdy != 0):
                    self._try_player_move(pdx, pdy)

        # Если игрок завершил свою анимацию — запускаем очередь врагов
        if self.turn == "waiting_player_anim":
            if not getattr(self.player_sprite, "moving", False):
                # Переключаемся в обработку врагов
                self.turn = "enemy"
                self.process_enemy_turns()

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
        # Зум камеры, не должен зависеть от порядка ходов.
        if symbol in (arcade.key.PLUS, arcade.key.EQUAL):
            if self.camera_controller is not None:
                self.camera_controller.zoom_in()
            return
        if symbol in (arcade.key.MINUS, arcade.key.UNDERSCORE):
            if self.camera_controller is not None:
                self.camera_controller.zoom_out()
            return

        # Игрок может действовать только в свой ход
        if self.turn != "player":
            return

        # Перечень клавиш направления
        dir_keys = (
            arcade.key.W, arcade.key.S, arcade.key.A, arcade.key.D,
            arcade.key.UP, arcade.key.DOWN, arcade.key.LEFT, arcade.key.RIGHT,
        )

        now = time.time()
        # Если это клавиша направления — пометим её как зажатую и запомним метку времени
        if symbol in dir_keys:
            # Запомним нажатие
            self._pressed_keys.add(symbol)
            self._key_timestamps[symbol] = now

            # Определим, какие горизонтальные и вертикальные клавиши активны прямо сейчас
            horiz_keys = {arcade.key.A: -1, arcade.key.LEFT: -1, arcade.key.D: 1, arcade.key.RIGHT: 1}
            vert_keys = {arcade.key.W: 1, arcade.key.UP: 1, arcade.key.S: -1, arcade.key.DOWN: -1}

            # Найдём наиболее свежие активные клавиши по оси
            best_h_t = -1.0
            best_v_t = -1.0
            chosen_h = 0
            chosen_v = 0
            for k, s in horiz_keys.items():
                if k in self._pressed_keys:
                    chosen_h = s
                    best_h_t = now
                    break
                t = self._key_timestamps.get(k)
                if t is not None and now - t <= DIAGONAL_TOLERANCE and t > best_h_t:
                    chosen_h = s
                    best_h_t = t
            for k, s in vert_keys.items():
                if k in self._pressed_keys:
                    chosen_v = s
                    best_v_t = now
                    break
                t = self._key_timestamps.get(k)
                if t is not None and now - t <= DIAGONAL_TOLERANCE and t > best_v_t:
                    chosen_v = s
                    best_v_t = t

            # Если есть и горизонтальная, и вертикальная активность — сразу делаем диагональ
            if chosen_h != 0 and chosen_v != 0:
                self._try_player_move(chosen_h, chosen_v)
                # очистим pending, если был
                self._pending_move = None
                return

            # Иначе — поставим в pending для возможного объединения
            if chosen_h != 0:
                self._pending_move = {'time': now, 'dx': chosen_h, 'dy': 0}
            elif chosen_v != 0:
                self._pending_move = {'time': now, 'dx': 0, 'dy': chosen_v}
            else:
                # просто отложим текущее одиночное нажатие
                self._pending_move = {'time': now, 'dx': 0, 'dy': 0}
            return

        # Пропуск хода по пробелу
        if symbol == arcade.key.SPACE:
            self._pending_move = None
            self._recover_player_light(2)
            self.turn = "enemy"
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
            # Завершаем ход игрока
            self.turn = "enemy"
            self.process_enemy_turns()
            return res, blocker
        if res == MoveResult.MOVED:
            self._consume_player_light(1)
            self.turn = "waiting_player_anim"
            return res, blocker
        return res, blocker

    def on_key_release(self, symbol, modifiers):
        # Убираем клавишу из набора зажатых, но НЕ удаляем метку времени — она нужна для tolerance
        self._pressed_keys.discard(symbol)

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
        self.turn = "player"


def main():
    game = Game()
    game.setup()
    arcade.run()

if __name__ == "__main__":
    main()
