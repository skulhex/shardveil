import sys
from pathlib import Path
import arcade
from arcade import gl
from sv.core import Settings, GameState
from sv.world import LevelGenerator
from sv.entities import Player, Skeleton
from sv.core.collision import MoveResult

TILE_SIZE = Settings.TILE_SIZE

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
        self.level = None
        self.scene = None
        self.player_sprite = None
        self.camera = None
        self.target_zoom = None
        # Состояние хода: "player" или другие состояния
        self.turn = "player"
        # Очередь врагов для последовательной обработки
        self._enemy_queue: list = []
        self._current_enemy = None
        # Набор текущих зажатых клавиш (для поддержки диагоналей)
        self._pressed_keys: set[int] = set()

    def setup(self):
        # Генерируем уровень
        gen = LevelGenerator(width=16, height=16)
        level = gen.generate()

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
        textures = tiles.get_texture_grid((TILE_SIZE, TILE_SIZE), columns=2, count=2)

        # Назначение текстур для пола и стен
        floor_texture = textures[0]
        wall_texture = textures[1]

        for y in range(len(level)):
            for x in range(len(level[0])):
                tile = level[y][x]
                world_x = x * TILE_SIZE
                world_y = y * TILE_SIZE

                if tile == 1:
                    sprite = arcade.Sprite()
                    sprite.texture = floor_texture
                    sprite.center_x = world_x + TILE_SIZE / 2
                    sprite.center_y = world_y + TILE_SIZE / 2
                    self.scene["Ground"].append(sprite)
                else:
                    sprite = arcade.Sprite()
                    sprite.texture = wall_texture
                    sprite.center_x = world_x + TILE_SIZE / 2
                    sprite.center_y = world_y + TILE_SIZE / 2
                    self.scene["Walls"].append(sprite)

        # Создаём игрока
        self.player_sprite = Player(tile_x=8, tile_y=5)
        self.scene.add_sprite("Player", self.player_sprite)
        # Настраиваем камеру
        self.camera = arcade.camera.Camera2D()
        self.camera.zoom = 2.0  # увеличение всех спрайтов в 2 раза
        self.target_zoom = 2.0  # начальный целевой зум
        self.camera.position = (# начальная позиция камеры
            self.player_sprite.center_x,
            self.player_sprite.center_y)

        # Создаём врага
        skeleton = Skeleton(tile_x=10, tile_y=5)
        self.scene.add_sprite("Skeleton", skeleton)

    def on_draw(self):
        self.clear()
        self.camera.use()
        self.scene.draw()

    def on_update(self, delta_time):
        # Плавная интерполяция зума камеры
        self.camera.zoom += (self.target_zoom - self.camera.zoom) * 0.1
        # Плавное следование камеры за игроком
        cam_x, cam_y = self.camera.position
        self.camera.position = (
            cam_x + (self.player_sprite.center_x - cam_x) * 0.1,
            cam_y + (self.player_sprite.center_y - cam_y) * 0.1
        )

        # Обновляем сцену, чтобы вызвать Sprite.update на всех спрайтах (анимация движения)
        try:
            if self.scene:
                # arcade.Scene.update принимает delta_time в новых версиях
                self.scene.update(delta_time)
        except Exception:
            # for compatibility, call without args
            try:
                self.scene.update()
            except Exception:
                pass

        # Если игрок завершил свою анимацию — запускаем очередь врагов
        if self.turn == "waiting_player_anim":
            if not getattr(self.player_sprite, 'moving', False):
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

        # Добавляем клавишу в набор зажатых
        self._pressed_keys.add(symbol)

        # Вычисляем направление по текущим нажатым клавишам (поддержка диагоналей)
        dx = 0
        dy = 0
        if any(k in self._pressed_keys for k in (arcade.key.W, arcade.key.UP)):
            dy = 1
        if any(k in self._pressed_keys for k in (arcade.key.S, arcade.key.DOWN)):
            dy = -1
        if any(k in self._pressed_keys for k in (arcade.key.A, arcade.key.LEFT)):
            dx = -1
        if any(k in self._pressed_keys for k in (arcade.key.D, arcade.key.RIGHT)):
            dx = 1
        # Пропуск хода по пробелу
        elif symbol == arcade.key.SPACE:
            # Завершаем ход без действий — запускаем очередь врагов
            self.turn = "enemy"
            self.process_enemy_turns()
            return
        # Зум камеры
        elif symbol in (arcade.key.PLUS, arcade.key.EQUAL):  # Приблизить
            self.target_zoom *= 1.5
        elif symbol in (arcade.key.MINUS, arcade.key.UNDERSCORE):  # Отдалить
            self.target_zoom /= 1.5

        # Ограничиваем диапазон зума (1x–4x)
        self.target_zoom = max(1.0, min(4.0, self.target_zoom))

        if dx == 0 and dy == 0:
            return

        # Попробуем перемещение с fallback-логикой при диагоналях: сначала (dx,dy), затем (dx,0), затем (0,dy)
        def try_move_with_fallback(entity, dx, dy):
            # Используем метод сущности, чтобы запустить анимацию (entity.attempt_move)
            res, blocker = entity.attempt_move(dx, dy, self.level, self.scene)
            if res == MoveResult.MOVED:
                return res, blocker
            # Если диагональ была заблокирована стеной — попробуем по осям
            if dx != 0 and dy != 0 and res == MoveResult.BLOCKED_WALL:
                res2, blocker2 = entity.attempt_move(dx, 0, self.level, self.scene)
                if res2 == MoveResult.MOVED:
                    return res2, blocker2
                res3, blocker3 = entity.attempt_move(0, dy, self.level, self.scene)
                return res3, blocker3
            return res, blocker

        res, blocker = try_move_with_fallback(self.player_sprite, dx, dy)
        if res is None:
            return

        if res == MoveResult.BLOCKED_WALL:
            return
        if res == MoveResult.BLOCKED_ENTITY:
            if blocker is not None and hasattr(self.player_sprite, 'attack'):
                self.player_sprite.attack(blocker)
            # Завершаем ход игрока
            self.turn = "enemy"
            self.process_enemy_turns()
            return

        # Если удалось переместиться — запускаем очередь врагов после завершения анимации игрока
        if res == MoveResult.MOVED:
            # Ожидаем завершения анимации игрока перед действиями врагов
            self.turn = "waiting_player_anim"
            return

    def on_key_release(self, symbol, modifiers):
        # Убираем клавишу из набора зажатых
        if symbol in self._pressed_keys:
            self._pressed_keys.remove(symbol)
        return

    def process_enemy_turns(self):
        """Запускает последовательную обработку ходов всех врагов с ожиданием их анимаций."""
        # Сформируем очередь живых врагов
        enemies = list(self.scene.get_sprite_list("Skeleton") or [])
        self._enemy_queue = [e for e in enemies if not getattr(e, 'removed', False)]
        self._current_enemy = None
        # Запускаем обработку
        self._process_next_enemy()

    def _process_next_enemy(self):
        """
        Обрабатывает следующий враг из очереди. Если враг начинает анимацию — ждём её завершения.
        Иначе продолжаем к следующему врагу. По окончании возвращаем ход игроку.
        """
        while self._enemy_queue:
            enemy = self._enemy_queue.pop(0)
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

            # Используем безопасную попытку перемещения через метод сущности (анимация)
            def try_move_with_fallback_enemy(entity, dx, dy):
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

            res, blocker = try_move_with_fallback_enemy(enemy, dx, dy)
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
                # Пометим текущего врага и установим hook на окончание анимации
                self._current_enemy = enemy
                # устанавливаем callback, который вызовет продолжение очереди
                def _make_callback(e):
                    def cb():
                        # убираем callback и продолжим обработку
                        try:
                            e.on_move_complete = None
                        except Exception:
                            pass
                        # после завершения анимации — продолжим со следующего врага
                        self._current_enemy = None
                        self._process_next_enemy()
                    return cb
                try:
                    enemy.on_move_complete = _make_callback(enemy)
                except Exception:
                    # если не получилось установить callback — просто продолжим
                    self._current_enemy = None
                    continue
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
