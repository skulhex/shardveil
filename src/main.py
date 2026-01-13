import sys
from pathlib import Path
import arcade
from arcade import gl
from sv.core import Settings, GameState
from sv.world import LevelGenerator
from sv.entities import Player, Skeleton

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
        # Перемещение теперь происходит через проверку уровня/сущностей
        dx = 0
        dy = 0
        if symbol in (arcade.key.W, arcade.key.UP):
            dy = 1
        elif symbol in (arcade.key.S, arcade.key.DOWN):
            dy = -1
        elif symbol in (arcade.key.A, arcade.key.LEFT):
            dx = -1
        elif symbol in (arcade.key.D, arcade.key.RIGHT):
            dx = 1
        # Зум камеры
        elif symbol in (arcade.key.PLUS, arcade.key.EQUAL):  # Приблизить
            self.target_zoom *= 1.5
        elif symbol in (arcade.key.MINUS, arcade.key.UNDERSCORE):  # Отдалить
            self.target_zoom /= 1.5

        # Ограничиваем диапазон зума (1x–4x)
        self.target_zoom = max(1.0, min(4.0, self.target_zoom))

        # Если была нажата клавиш направления — пробуем сделать ход
        if dx != 0 or dy != 0:
            cur_tx = self.player_sprite.tile_x
            cur_ty = self.player_sprite.tile_y
            target_tx = cur_tx + dx
            target_ty = cur_ty + dy

            # Проверяем границы уровня
            max_y = len(self.level)
            max_x = len(self.level[0]) if max_y > 0 else 0
            if not (0 <= target_tx < max_x and 0 <= target_ty < max_y):
                return

            # Проверяем тайл (0 = стена, 1 = пол)
            if self.level[target_ty][target_tx] == 0:
                # Стена — ход невозможен
                return

            # Проверяем наличие сущности в целевом тайле
            entity = self.get_entity_at(target_tx, target_ty)
            if entity and entity is not self.player_sprite:
                # Враг/сущность на пути — атакуем
                if hasattr(self.player_sprite, "attack"):
                    self.player_sprite.attack(entity)
                return

            # Пустой проходимый тайл — двигаем игрока
            self.player_sprite.tile_x = target_tx
            self.player_sprite.tile_y = target_ty
            self.player_sprite.center_x = target_tx * TILE_SIZE + TILE_SIZE // 2
            self.player_sprite.center_y = target_ty * TILE_SIZE + TILE_SIZE // 2

    def on_key_release(self, symbol, modifiers):
        pass


def main():
    game = Game()
    game.setup()
    arcade.run()

if __name__ == "__main__":
    main()
