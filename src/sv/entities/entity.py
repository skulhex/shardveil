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

        # --- Новые атрибуты для анимированного перемещения ---
        self.moving = False
        self._move_from = (self.center_x, self.center_y)
        self._move_to = (self.center_x, self.center_y)
        self._move_elapsed = 0.0
        self._move_duration = 0.18  # секунда по умолчанию
        # hook, вызывается когда анимация перемещения завершена
        self.on_move_complete = None

    def move_to(self, tile_x: int, tile_y: int):
        """Прямое перемещение сущности в тайловых координатах (без проверок)."""
        self.tile_x = int(tile_x)
        self.tile_y = int(tile_y)
        self.center_x = self.tile_x * TILE_SIZE + TILE_SIZE // 2
        self.center_y = self.tile_y * TILE_SIZE + TILE_SIZE // 2

    def start_move(self, target_tile_x: int, target_tile_y: int, duration: float | None = None):
        """
        Запускает анимированное перемещение к указанному тайлу.
        Резервирует/предполагает, что tile_x/tile_y уже установлены (commit_tile).
        Интерполирует center_x/center_y от текущих мировых координат до целевых за время duration.
        """
        if duration is not None:
            self._move_duration = float(duration)
        self.moving = True
        self._move_elapsed = 0.0
        self._move_from = (self.center_x, self.center_y)
        self._move_to = (target_tile_x * TILE_SIZE + TILE_SIZE // 2,
                         target_tile_y * TILE_SIZE + TILE_SIZE // 2)

    def attempt_move(self, dx: int, dy: int, level, scene):
        """Попытка перемещения: использует разделённый can_move/commit_tile чтобы запустить анимацию вместо мгновенного перемещения."""
        try:
            from sv.core.collision import can_move, commit_tile, MoveResult
        except Exception:
            return None, None

        res, blocker, target_tx, target_ty = can_move(self, dx, dy, level, scene)
        # Если не можем двинуться - вернуть причину
        if res != MoveResult.MOVED:
            return res, blocker

        # Резервируем тайл
        committed = commit_tile(self, target_tx, target_ty)
        if not committed:
            return MoveResult.BLOCKED_WALL, None

        # Запускаем анимацию перемещения
        self.start_move(target_tx, target_ty)
        return MoveResult.MOVED, None

    def take_damage(self, amount: int):
        self.hp -= amount
        if self.hp <= 0:
            self.die()

    def die(self):
        self.remove_from_sprite_lists()

    def update(self, *args, **kwargs):
        # Совместимая сигнатура с arcade.Sprite.update
        # Обновляем анимацию позиционирования, если мы в движении
        if self.moving:
            # delta_time may be passed as first positional arg in some arcade versions
            delta_time = 1/60
            if len(args) > 0 and isinstance(args[0], (int, float)):
                delta_time = float(args[0])

            self._move_elapsed += delta_time
            t = min(1.0, self._move_elapsed / max(1e-6, self._move_duration))
            # ease-out квадратическая: t' = 1 - (1-t)^2
            tt = 1 - (1 - t) * (1 - t)
            sx, sy = self._move_from
            ex, ey = self._move_to
            self.center_x = sx + (ex - sx) * tt
            self.center_y = sy + (ey - sy) * tt

            if t >= 1.0:
                # Завершили перемещение: гарантированно ставим в целевые мировые координаты
                self.center_x = ex
                self.center_y = ey
                self.moving = False
                # Вызов хуков
                try:
                    if callable(self.on_move_complete):
                        self.on_move_complete()
                except Exception:
                    pass
        # вызов базового обновления
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