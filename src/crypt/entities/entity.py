import arcade
from src.crypt.core import Settings

PLAYER_TEXTURE_PATH = "assets/player.png"   # путь к текстуре игрока
TILE_SIZE = Settings.TILE_SIZE

class Entity(arcade.Sprite):
    """Базовая сущность игрового мира"""
    def __init__(self, x: int, y: int, texture: str = None, scale: float = 1):
        super().__init__(texture=texture, scale=scale)
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
        super().__init__(pixel_x, pixel_y, PLAYER_TEXTURE_PATH)
        self.tile_x = tile_x
        self.tile_y = tile_y
        self.is_moving = False

    def _handle_collisions(self):
        # Заглушка для обработки коллизий
        pass

    def _update_animation(self):
        # Заглушка для смены кадров
        pass