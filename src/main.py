import random
import sys
import time
from collections import deque
from pathlib import Path
import arcade
from arcade import gl
from sv.core import Settings
from sv.world import LevelGenerator
from sv.entities import Player, Skeleton
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
        self.target_zoom = None
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
        self.camera = arcade.camera.Camera2D()
        self.camera.zoom = 2.0  # увеличение всех спрайтов в 2 раза
        self.target_zoom = 2.0  # начальный целевой зум
        self.camera.position = (self.player_sprite.center_x, self.player_sprite.center_y)

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
        self.hud_anchor.add(self.bars_layout, anchor_x="left", 
                            anchor_y="bottom", align_y=10, align_x=8)

        # Добавляем подложку в UI
        self.ui.add(self.hud_anchor)

    def on_draw(self):
        self.clear()
        self.camera.use()
        self.scene.draw()
        self.ui.draw()

    def on_update(self, delta_time):
        # Обновляем значение hp(хп * флоат_значение)
        self.pbar.value = self.player_sprite.hp / self.player_sprite.max_hp
        self.pbar.update_bar()
        
        # Плавная интерполяция зума камеры
        self.camera.zoom += (self.target_zoom - self.camera.zoom) * 0.1
        # Плавное следование камеры за игроком
        cam_x, cam_y = self.camera.position
        self.camera.position = (
            cam_x + (self.player_sprite.center_x - cam_x) * 0.1,
            cam_y + (self.player_sprite.center_y - cam_y) * 0.1,
        )

        # Обновляем сцену, чтобы вызвать Sprite.update на всех спрайтах (анимация движения)
        if self.scene:
            self.scene.update(delta_time)

        # Небольшая очистка старых меток нажатий, чтобы словарь не рос бесконечно
        now = time.time()
        to_del = [k for k, t in self._key_timestamps.items() if now - t > DIAGONAL_TOLERANCE * 3]
        for k in to_del:
            self._key_timestamps.pop(k, None)

        # Если есть отложенный ход и он просрочен — выполним его
        if self._pending_move is not None:
            if now - self._pending_move.get('time', 0.0) >= DIAGONAL_TOLERANCE:
                pdx = self._pending_move.get('dx', 0)
                pdy = self._pending_move.get('dy', 0)
                self._pending_move = None
                if self.turn == 'player':
                    self._try_player_move(pdx, pdy)

        # Если игрок завершил свою анимацию — запускаем очередь врагов
        if self.turn == "waiting_player_anim":
            if not getattr(self.player_sprite, "moving", False):
                # Переключаемся в обработку врагов
                self.turn = "enemy"
                self.process_enemy_turns()

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
            self.turn = "enemy"
            self.process_enemy_turns()
            return

        # Зум камеры
        if symbol in (arcade.key.PLUS, arcade.key.EQUAL):
            self.target_zoom = min(4.0, self.target_zoom * 1.5)
        elif symbol in (arcade.key.MINUS, arcade.key.UNDERSCORE):
            self.target_zoom = max(1.0, self.target_zoom / 1.5)

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
            # Завершаем ход игрока
            self.turn = "enemy"
            self.process_enemy_turns()
            return res, blocker
        if res == MoveResult.MOVED:
            self.turn = "waiting_player_anim"
            return res, blocker
        return res, blocker

    def on_key_release(self, symbol, modifiers):
        # Убираем клавишу из набора зажатых, но НЕ удаляем метку времени — она нужна для tolerance
        self._pressed_keys.discard(symbol)

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
            ex = enemy.tile_x
            ey = enemy.tile_y
            px = self.player_sprite.tile_x
            py = self.player_sprite.tile_y
            # Если рядом (включая диагональ) — атакуем (Chebyshev distance)
            if max(abs(ex - px), abs(ey - py)) == 1:
                if hasattr(enemy, "attack"):
                    enemy.attack(self.player_sprite)
                continue
            # Иначе пытаемся подойти на 1 тайл по оси с приоритетом X
            # Подходить можно по обеим осям одновременно — так враги смогут двигаться по диагонали
            dx = 0
            dy = 0
            if ex < px:
                dx = 1
            elif ex > px:
                dx = -1
            if ey < py:
                dy = 1
            elif ey > py:
                dy = -1

            res, blocker = self._move_with_fallback(enemy, dx, dy)
            # Если блокирует стена — пропускаем
            if res == MoveResult.BLOCKED_WALL:
                continue
            # Если блокирует сущность — если это игрок, атакуем
            if res == MoveResult.BLOCKED_ENTITY:
                if blocker is self.player_sprite:
                    enemy.attack(self.player_sprite)
                continue
            # Если MOVED — нужно дождаться завершения анимации этого врага
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
            # иначе — продолжаем к следующему врагу
            continue

        # Очередь пуста — возвращаем ход игроку
        self.turn = "player"


def main():
    game = Game()
    game.setup()
    arcade.run()

if __name__ == "__main__":
    main()
