import arcade
from pathlib import Path
from PIL import Image
from crypt.core import Settings, GameState
from crypt.world import LevelGenerator

ASSETS_PATH = Path(__file__).parent.parent / "assets"
TILE_SIZE = Settings.TILE_SIZE

class Game(arcade.Window):
    def __init__(self):
        self.settings = Settings()
        super().__init__(
            width=self.settings.screen_width,
            height=self.settings.screen_height,
            title=self.settings.title
        )
        self.scene = None
        self.player_sprite = None
        self.camera = None
        self.target_zoom = None

    def setup(self):
        # Генерируем уровень
        gen = LevelGenerator(width=16, height=16)
        level = gen.generate()

        # Создаём сцену
        self.scene = arcade.Scene()
        self.scene.add_sprite_list("Ground")
        self.scene.add_sprite_list("Walls")

        # Загружаем PNG tileset целиком
        tileset_image = Image.open(ASSETS_PATH / "sprites/tileset.png")

        # Основные тайлы
        floor_texture = self.get_tile(tileset_image, 0, 0)  # пол
        wall_texture = self.get_tile(tileset_image, 1, 0)   # стена

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
        self.player_sprite = arcade.Sprite(str(ASSETS_PATH / "sprites/player.png"), scale=1)
        self.player_sprite.center_x = TILE_SIZE * 2 + TILE_SIZE / 2
        self.player_sprite.center_y = TILE_SIZE * 2 + TILE_SIZE / 2

        self.scene.add_sprite("Player", self.player_sprite)
        self.camera = arcade.camera.Camera2D()
        self.camera.zoom = 2.0  # увеличение всех спрайтов в 2 раза
        self.target_zoom = 2.0  # чтобы зум при нажатиях корректно работал

    def on_draw(self):
        self.clear()
        self.camera.use()
        self.scene.draw()

    def on_update(self, delta_time):
        # Плавная интерполяция зума камеры
        self.camera.zoom += (self.target_zoom - self.camera.zoom) * 0.1
        # Центр экрана на игроке
        self.camera.position = (
            self.player_sprite.center_x,
            self.player_sprite.center_y)

    def on_key_press(self, symbol, modifiers):
        tile = TILE_SIZE
        # Передвижение по тайлам
        if symbol in (arcade.key.W, arcade.key.UP):
            self.player_sprite.center_y += tile
        elif symbol in (arcade.key.S, arcade.key.DOWN):
            self.player_sprite.center_y -= tile
        elif symbol in (arcade.key.A, arcade.key.LEFT):
            self.player_sprite.center_x -= tile
        elif symbol in (arcade.key.D, arcade.key.RIGHT):
            self.player_sprite.center_x += tile
        # Зум камеры
        elif symbol in (arcade.key.PLUS, arcade.key.EQUAL):  # Приблизить
            self.target_zoom *= 1.5
        elif symbol in (arcade.key.MINUS, arcade.key.UNDERSCORE):  # Отдалить
            self.target_zoom /= 1.5
        # Ограничиваем диапазон зума (1x–4x)
        self.target_zoom = max(1.0, min(4.0, self.target_zoom))

    def on_key_release(self, symbol, modifiers):
        pass

    def get_tile(self, tileset_image, col, row):
        x = col * TILE_SIZE
        y = row * TILE_SIZE
        tile = tileset_image.crop((x, y, x + TILE_SIZE, y + TILE_SIZE))
        return arcade.Texture(tile)


def main():
    game = Game()
    game.setup()
    arcade.run()

if __name__ == "__main__":
    main()
