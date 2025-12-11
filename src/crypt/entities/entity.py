import arcade
from pathlib import Path
from src.crypt.core import Settings

ASSETS_PATH = Path(__file__).parent.parent.parent.parent / "-"
PLAYER_TEXTURE = str(ASSETS_PATH / "-")
ENEMY_TEXTURE = str(ASSETS_PATH / "-") 
TILE_SIZE = Settings.TILE_SIZE

class Entity(arcade.Sprite):
    """Базовая сущность игрового мира"""
    def __init__(self, x: int, y: int, texture: str = None):
        super().__init__(str(texture))
        self.center_x = x
        self.center_y = y

    def update(self):
        super().update()

    def take_turn(self):
        """Метод, вызываемый, когда наступает ход сущности. Основная игровая логика."""
        pass # Реализация в дочерних классах

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
        self.health = 100 # ХП

    def take_turn(self):
        """Ход игрока: ждет ввода от пользователя."""
        pass
        
    def _handle_collisions(self):
        # Заглушка для обработки коллизий
        pass

    def _update_animation(self):
        # Заглушка для смены кадров
        pass


class Enemy(Entity):
    """Класс противника, наследуется от Entity. Логика ИИ активируется только в его ход."""
    def __init__(self, tile_x: int, tile_y: int):
        # Инициализация позиции по тайлам
        pixel_x = tile_x * TILE_SIZE + TILE_SIZE // 2
        pixel_y = tile_y * TILE_SIZE + TILE_SIZE // 2
        super().__init__(pixel_x, pixel_y, ENEMY_TEXTURE)
        self.tile_x = tile_x
        self.tile_y = tile_y
        self.health = 100 
        self.target = None

    def take_turn(self):
        """Ход врага: немедленно выполняет логику ИИ."""
        self._ai_logic() 
        
    def _ai_logic(self):
        """Реализация искусственного интеллекта (поиск пути, атака)."""
        print(f"Enemy at ({self.tile_x}, {self.tile_y}) takes a turn.")

    def _handle_collisions(self):
        # Переопределение заглушки для обработки коллизий
        pass

    def _update_animation(self):
        # Переопределение заглушки для анимации
        pass
