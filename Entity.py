import arcade
from typing import Optional, Tuple

# --- Константы игры ---
TILE_SIZE: int = 32                  # размер тайла пиксельной игры
PLAYER_SPEED: int = 2                # скорость (целые числа)
PLAYER_SIZE: int = TILE_SIZE         # размер игрока = 1 тайл

PLAYER_TEXTURE_PATH = "assets/player.png"   # путь к текстуре игрока


class Entity(arcade.Sprite):
    """
    Базовая сущность игрового мира.
    """

    def __init__(self, x: int, y: int, texture: Optional[str] = None):
        # Для пиксельной игры важна четкая сетка → scale=1
        super().__init__(texture=texture, scale=1)

        # позиция в сетке тайлов
        self.center_x = x
        self.center_y = y

        # Размеры пиксельного хитбокса
        self.width = PLAYER_SIZE
        self.height = PLAYER_SIZE

    def update(self):
        super().update()


class Player(Entity):
    """
    Класс игрока.
    """

    def __init__(self, x: int, y: int):
        # загружаем текстуру, можно заменить на анимации позже
        super().__init__(x, y, PLAYER_TEXTURE_PATH)

        # скорость в пикселях
        self.speed: int = PLAYER_SPEED

        # состояние под FSM (idle/move/jump)
        self.is_moving: bool = False

        # входной вектор движения (будет задаваться окном)
        self._input_vector: Tuple[int, int] = (0, 0)

    def setup(self):
        self.change_x = 0
        self.change_y = 0

    def update(self):
        self._apply_input()
        self._update_animation()
        super().update()
        self._handle_collisions()

    # --- ЛОГИКА ---

    def set_input(self, dx: int, dy: int):
        """
        Устанавливается из on_key_press / on_key_release в Window.
        """
        self._input_vector = (dx, dy)

    def _apply_input(self):
        dx, dy = self._input_vector
        self.change_x = dx * self.speed
        self.change_y = dy * self.speed

        self.is_moving = (dx != 0 or dy != 0)

    def _handle_collisions(self):
        """
        Заготовка под Arcade Physics Engine. пригодиться
        """
        pass

    def _update_animation(self):
        """
        На будущее: смена кадров. Ну вроде она есть она на всякий добавил заготовочку
        """
        pass
