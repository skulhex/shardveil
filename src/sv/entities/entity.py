import arcade
from sv.core import Settings

TILE_SIZE = Settings.TILE_SIZE

class Entity(arcade.Sprite):
    """Базовая сущность игрового мира"""
    def __init__(self, texture, tile_x: int, tile_y: int, hp: int = 1, blocking: bool = True):
        super().__init__(str(texture))

        self.hp = hp
        self.tile_x = int(tile_x)
        self.tile_y = int(tile_y)

        # Устанавливаем мировые координаты
        self.center_x = self.tile_x * TILE_SIZE + TILE_SIZE // 2
        self.center_y = self.tile_y * TILE_SIZE + TILE_SIZE // 2

        # По умолчанию сущность блокирует движение (предметы могут быть non-blocking)
        self.blocking = bool(blocking)

    def move_to(self, tile_x: int, tile_y: int):
        """Прямое перемещение сущности в тайловых координатах (без проверок)."""
        self.tile_x = int(tile_x)
        self.tile_y = int(tile_y)
        self.center_x = self.tile_x * TILE_SIZE + TILE_SIZE // 2
        self.center_y = self.tile_y * TILE_SIZE + TILE_SIZE // 2

    def attempt_move(self, dx: int, dy: int, level, scene):
        """Попытка перемещения: wrapper над sv.core.collision.attempt_move.

        Возвращает (MoveResult, blocker)
        """
        try:
            from sv.core.collision import attempt_move as _attempt_move
        except Exception:
            return None, None
        return _attempt_move(self, dx, dy, level, scene)

    def take_damage(self, amount: int):
        self.hp -= amount
        if self.hp <= 0:
            self.die()

    def die(self):
        self.remove_from_sprite_lists()

    def update(self, *args, **kwargs):
        # Совместимая сигнатура с arcade.Sprite.update
        super().update(*args, **kwargs)

    def take_turn(self):
        """Метод, вызываемый, когда наступает ход сущности. Основная игровая логика."""
        pass # Реализация в дочерних классах

    def _handle_collisions(self):
        # Заглушка для обработки коллизий
        pass

    def _update_animation(self):
        # Заглушка для смены кадров
        pass

    def attack(self, target: "Entity", damage: int = 1):
        """Наносит урон другому объекту-существу.

        По умолчанию наносит 1 урона. Проверяет, что цель не None и не сам субъект.
        """
        if target is None:
            return
        if target is self:
            return
        if not isinstance(target, Entity):
            return
        target.take_damage(damage)


class Player(Entity):
    """Класс игрока"""
    def __init__(self, tile_x: int, tile_y: int):
        texture = ":assets:/sprites/player.png"
        super().__init__(texture, tile_x, tile_y, hp=10, blocking=True)

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
        texture = ":assets:/sprites/skeleton.png"
        super().__init__(texture, tile_x, tile_y, hp=4)