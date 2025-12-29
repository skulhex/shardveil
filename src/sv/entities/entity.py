import arcade
from pathlib import Path
from sv.core import Settings

ASSETS_PATH = Path(__file__).parent.parent.parent.parent / "assets"
PLAYER_TEXTURE = str(ASSETS_PATH / "sprites/player.png")
TILE_SIZE = Settings.TILE_SIZE

class Entity(arcade.Sprite):
    """Базовая сущность игрового мира"""
    def __init__(self, texture, tile_x: int, tile_y: int, hp: int = 1):
        super().__init__(str(texture))

        self.hp = hp
        self.tile_x = tile_x
        self.tile_y = tile_y

        self.center_x = tile_x * TILE_SIZE + TILE_SIZE // 2
        self.center_y = tile_y * TILE_SIZE + TILE_SIZE // 2

    def take_damage(self, amount: int):
        self.hp -= amount
        if self.hp <= 0:
            self.die()

    def die(self):
        self.remove_from_sprite_lists()

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
        texture = str(ASSETS_PATH / "sprites/player.png")
        super().__init__(texture, tile_x, tile_y, hp=10)

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
    def __init__(self, texture, tile_x: int, tile_y: int, hp: int = 3):
        super().__init__(texture, tile_x, tile_y, hp)

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

class Skeleton(Enemy):
    def __init__(self, tile_x: int, tile_y: int):
        texture = ASSETS_PATH / "sprites/skeleton.png"
        super().__init__(texture, tile_x, tile_y, hp=4)