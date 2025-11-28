import arcade
import math
from typing import Optional, List
from abc import ABC

COLOR_PLAYER = arcade.color.DODGER_BLUE
COLOR_ENEMY = arcade.color.ALIZARIN_CRIMSON
COLOR_NPC = arcade.color.AMBER

class Entity(arcade.Sprite):
    """
    Базовый класс для всех живых сущностей.
    """

    def __init__(self, x: float, y: float, max_hp: int, color: arcade.color):

        # 1. Вызываем конструктор родителя ТОЛЬКО с координатами.
        # Мы НЕ передаем texture здесь, чтобы избежать ошибки "multiple values".
        super().__init__(center_x=x, center_y=y)

        # 2. Создаем и присваиваем текстуру вручную после инициализации.
        # Это самый надежный способ в новых версиях Arcade.
        self.texture = arcade.make_soft_circle_texture(30, color)

        # 3. Инициализируем кастомные переменные
        self._max_hp: int = max_hp
        self._current_hp: int = max_hp
        self.color = color

    @property
    def is_alive(self) -> bool:
        return self._current_hp > 0

    @property
    def hp_percent(self) -> float:
        return max(0.0, self._current_hp / self._max_hp)

    def take_damage(self, amount: int) -> None:
        """Нанесение урона сущности."""
        self._current_hp -= amount
        if self._current_hp < 0:
            self._current_hp = 0

        # Визуальная отладка (принт в консоль)
        print(f"[{self.__class__.__name__}] получил {amount} урона. HP: {self._current_hp}/{self._max_hp}")

        if not self.is_alive:
            self.on_death()

    def on_death(self):
        """Переопределяемый метод смерти."""
        self.kill()  # Удаляет спрайт из всех списков Arcade


class NPC(Entity):
    """
    Класс для мирных NPC (Торговцы, Квестодатели).
    """

    def __init__(self, x: float, y: float, name: str, role: str):
        super().__init__(x, y, max_hp=100, color=COLOR_NPC)
        self.name = name
        self.role = role  # 'Trader', 'QuestGiver'

    def interact(self):
        """Метод взаимодействия с игроком."""
        print(f"{self.name} ({self.role}): 'Приветствую, путник!'")


class Enemy(Entity):
    """
    Класс врагов. Имеет базовый AI для атаки по таймеру.
    """

    def __init__(self, x: float, y: float):
        super().__init__(x, y, max_hp=100, color=COLOR_ENEMY)
        self.damage: int = 10
        self.attack_cooldown: float = 2.0
        self.time_since_last_attack: float = 0.0
        self.attack_range: float = 100.0  # Дистанция атаки

    def update_ai(self, delta_time: float, player: 'Player'):
        """
        Логика врага. Вызывается каждый кадр игровым циклом.
        """
        if not self.is_alive or not player.is_alive:
            return

        self.time_since_last_attack += delta_time

        # Проверка дистанции до игрока
        distance = arcade.get_distance_between_sprites(self, player)

        if distance <= self.attack_range:
            if self.time_since_last_attack >= self.attack_cooldown:
                self.attack(player)

    def attack(self, target: Entity):
        target.take_damage(self.damage)
        self.time_since_last_attack = 0.0
        print(f"Враг атаковал игрока на {self.damage} урона!")


class Player(Entity):
    """
    Главный герой. Управление скиллами.
    """

    def __init__(self, x: float, y: float):
        super().__init__(x, y, max_hp=100, color=COLOR_PLAYER)
        # Настройки скиллов
        self.aoe_damage: int = 25
        self.aoe_radius: float = 150.0

        self.single_damage: int = 40
        self.single_range: float = 200.0

    def skill_aoe_attack(self, enemies: List[Entity]):
        """
        Скилл 1: Взмах меча по области.
        """
        print(f"Игрок использует AoE атаку (Радиус: {self.aoe_radius})")
        hit_count = 0
        for enemy in enemies:
            dist = arcade.get_distance_between_sprites(self, enemy)
            if dist <= self.aoe_radius:
                enemy.take_damage(self.aoe_damage)
                hit_count += 1

        if hit_count == 0:
            print("Никого не задело.")

    def skill_single_target(self, enemies: List[Entity]):
        """
        Скилл 2: Направленный удар (бьет ближайшего в радиусе).
        """
        print("Игрок использует прицельный удар...")
        # Находим ближайшего врага
        closest_enemy = arcade.get_closest_sprite(self, list(enemies))

        if closest_enemy:
            enemy, dist = closest_enemy
            if dist <= self.single_range:
                enemy.take_damage(self.single_damage)
                print(f"Точечный удар попал!")
            else:
                print("Цель слишком далеко.")
        else:
            print("Нет целей.")
