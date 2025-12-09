import arcade
from pathlib import Path
from src.crypt.core import Settings

ASSETS_PATH = Path(__file__).parent.parent.parent.parent / "assets"
PLAYER_TEXTURE = str(ASSETS_PATH / "sprites/player.png")
TILE_SIZE = Settings.TILE_SIZE

class Entity(arcade.Sprite):
    """Базовая сущность игрового мира"""
    def __init__(self, x: int, y: int, texture: str = None):
        super().__init__(str(texture))
        self.center_x = x
        self.center_y = y

    def update(self):
        # Заглушка для будущей логики обновления сущности
        super().update()

    def _handle_collisions(self):
        # Заглушка для обработки коллизий
        pass

    def _update_animation(self):
        # Заглушка для смены кадров
        pass


class Player(Entity):
    """Класс игрока"""
    def __init__(self, tile_x: int, tile_y: int):
        # позиция в пикселях на основе тайлов, центр тайла
        pixel_x = tile_x * TILE_SIZE + TILE_SIZE // 2
        pixel_y = tile_y * TILE_SIZE + TILE_SIZE // 2
        super().__init__(pixel_x, pixel_y, PLAYER_TEXTURE)
        self.tile_x = tile_x
        self.tile_y = tile_y
        self.is_moving = False

    def _handle_collisions(self):
        # Заглушка для обработки коллизий
        pass

    def _update_animation(self):
        # Заглушка для смены кадров
        pass