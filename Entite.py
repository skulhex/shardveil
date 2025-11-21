import arcade
import random
import math
import os

# --- КОНФИГУРАЦИЯ ---
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
SCREEN_TITLE = "RPG: Меню, Физика и Регенерация"

# Текстуры
KNIGHT_IMG = None  # "hero.png"
CULTIST_IMG = None  # "enemy.png"
LORD_IMG = None  # "boss.png"

# Параметры баланса
PLAYER_SPEED = 5.0
ENEMY_SPEED = 3.5
XP_TO_LEVEL_UP_BASE = 100

# Состояния игры
STATE_PLAYING = 0
STATE_MENU = 1


class GameEntity(arcade.Sprite):
    """ Базовый класс """

    def __init__(self, image_path, scale, hp, mana, color):
        if image_path and os.path.exists(image_path):
            super().__init__(image_path, scale)
        else:
            super().__init__()
            self.texture = arcade.make_soft_square_texture(50, color, outer_alpha=255)
            self.scale = scale
            self.width = 50 * scale
            self.height = 50 * scale

        self.hp = hp
        self.max_hp = hp
        self.attack_cooldown_timer = 0

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp < 0: self.hp = 0
        if self.hp == 0:
            self.kill()
            return True  # Умер
        return False


class AshenKnight(GameEntity):
    def __init__(self, x, y):
        super().__init__(KNIGHT_IMG, 1.0, hp=150, mana=50, color=arcade.color.ASH_GREY)
        self.center_x = x
        self.center_y = y
        self.speed = PLAYER_SPEED

        # RPG Статы
        self.level = 1
        self.current_xp = 0
        self.xp_to_next_level = XP_TO_LEVEL_UP_BASE

        # Регенерация
        self.base_regen = 1.0  # 1 хп в секунду
        self.regen_per_level = 0.2

        # Способности
        self.stats = {
            "swing_dmg": 25,
            "swing_cd_max": 0.9,
            "overhead_dmg_crit": 50,
            "overhead_dmg_fail": 30,
            "overhead_cd_max": 8.0
        }
        self.cd_swing_current = 0
        self.cd_overhead_current = 0

    def regen_update(self, delta_time):
        """ Восстановление здоровья со временем """
        if self.hp < self.max_hp:
            # Формула: База (1) + (Уровень * 0.2)
            current_regen_rate = self.base_regen + (self.level * self.regen_per_level)
            self.hp += current_regen_rate * delta_time

            # Не превышаем максимум
            if self.hp > self.max_hp:
                self.hp = self.max_hp

    def on_kill_enemy(self, enemy_xp):
        """ Вызывается при убийстве врага """
        # 1. Повышаем макс ХП на 6
        self.max_hp += 6
        self.hp += 6  # Лечим на ту же сумму, чтобы полоска визуально не падала
        print(f"Враг убит! Макс. HP увеличено до {self.max_hp}")

        # 2. Опыт
        self.gain_xp(enemy_xp)

    def gain_xp(self, amount):
        self.current_xp += amount
        # Возвращаем True, если нужно открыть меню уровня
        if self.current_xp >= self.xp_to_next_level:
            return True
        return False

    def level_up_apply(self):
        """ Применяется ПОСЛЕ выбора в меню """
        self.level += 1
        self.current_xp -= self.xp_to_next_level
        self.xp_to_next_level = int(self.xp_to_next_level * 1.5)
        # Полное лечение при уровне
        self.hp = self.max_hp
        print(f"Уровень {self.level}! Регенерация теперь: {self.base_regen + self.level * 0.2:.1f}/сек")

    def update_timers(self, delta_time):
        if self.cd_swing_current > 0: self.cd_swing_current -= delta_time
        if self.cd_overhead_current > 0: self.cd_overhead_current -= delta_time

        # Запускаем регенерацию
        self.regen_update(delta_time)

    def attack_swing(self, enemy_list):
        if self.cd_swing_current > 0: return False  # Атака не прошла

        hit_someone = False
        for enemy in enemy_list:
            if arcade.get_distance_between_sprites(self, enemy) <= 100:
                is_dead = enemy.take_damage(self.stats["swing_dmg"])
                hit_someone = True
                if is_dead:
                    return "KILL", enemy.xp_reward  # Сообщаем игре, что убили

        self.cd_swing_current = self.stats["swing_cd_max"]
        return hit_someone, 0

    def attack_overhead(self, enemy_list):
        if self.cd_overhead_current > 0: return False

        closest = arcade.get_closest_sprite(self, enemy_list)
        if closest:
            enemy, dist = closest
            if dist <= 120:
                dmg = self.stats["overhead_dmg_crit"] if random.choice([True, False]) else self.stats[
                    "overhead_dmg_fail"]
                is_dead = enemy.take_damage(dmg)
                self.cd_overhead_current = self.stats["overhead_cd_max"]

                if is_dead:
                    return "KILL", enemy.xp_reward
                return True, 0
        return False


class Enemy(GameEntity):
    def __init__(self, img, scale, hp, mana, color, damage, xp_reward):
        super().__init__(img, scale, hp, mana, color)
        self.base_damage = damage
        self.xp_reward = xp_reward
        self.attack_range = 50
        self.attack_speed_cd = 2.0
        self.speed = ENEMY_SPEED

    def update_ai(self, delta_time, player, all_enemies):
        if not player or player.hp <= 0: return

        # 1. Вектор к игроку
        dx = player.center_x - self.center_x
        dy = player.center_y - self.center_y
        dist = math.sqrt(dx * dx + dy * dy)

        if dist > 0:
            # Движение к игроку
            move_x = (dx / dist) * self.speed
            move_y = (dy / dist) * self.speed

            # --- КОЛЛИЗИЯ (ОТТАЛКИВАНИЕ) ВРАГОВ ---
            # Проверяем, не слишком ли мы близко к другим врагам
            separation_force = 1.5  # Сила отталкивания
            for other in all_enemies:
                if other != self:
                    # Если дистанция до друга меньше 40 пикселей
                    d_friend = arcade.get_distance_between_sprites(self, other)
                    if d_friend < 40 and d_friend > 0:
                        # Вектор ОТ друга
                        push_x = (self.center_x - other.center_x) / d_friend
                        push_y = (self.center_y - other.center_y) / d_friend

                        # Добавляем к движению (отталкиваемся)
                        move_x += push_x * separation_force
                        move_y += push_y * separation_force

            # Применяем итоговое движение
            self.center_x += move_x
            self.center_y += move_y

        # Атака
        if self.attack_cooldown_timer > 0:
            self.attack_cooldown_timer -= delta_time

        if dist < self.attack_range and self.attack_cooldown_timer <= 0:
            player.take_damage(self.base_damage)
            self.attack_cooldown_timer = self.attack_speed_cd


class EternalCultist(Enemy):
    def __init__(self, x, y):
        super().__init__(CULTIST_IMG, 0.8, hp=80, mana=100, color=arcade.color.PURPLE_HEART, damage=10, xp_reward=35)
        self.center_x = x;
        self.center_y = y


class BuriedLord(Enemy):
    def __init__(self, x, y):
        super().__init__(LORD_IMG, 1.2, hp=300, mana=0, color=arcade.color.DARK_GREEN, damage=25, xp_reward=150)
        self.center_x = x;
        self.center_y = y


class MyGame(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        self.background_color = arcade.color.SMOKY_BLACK
        self.all_sprites = arcade.SpriteList()
        self.enemies = arcade.SpriteList()
        self.player = None

        # Текущее состояние игры
        self.game_state = STATE_PLAYING

    def setup(self):
        self.all_sprites = arcade.SpriteList()
        self.enemies = arcade.SpriteList()
        self.player = AshenKnight(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        self.all_sprites.append(self.player)
        self.spawn_wave()

    def spawn_wave(self):
        # Спавним врагов
        coords = [(100, 100), (900, 100), (100, 600), (900, 600)]
        for x, y in coords:
            mob = EternalCultist(x, y)
            self.enemies.append(mob)
            self.all_sprites.append(mob)
        boss = BuriedLord(500, 650)
        self.enemies.append(boss)
        self.all_sprites.append(boss)

    def on_draw(self):
        self.clear()

        # Рисуем игру всегда (даже если пауза, она будет на фоне)
        self.all_sprites.draw()

        # HUD Игры
        if self.player.hp > 0:
            regen_txt = f"{self.player.base_regen + self.player.level * 0.2:.1f}/s"
            arcade.draw_text(f"HP: {int(self.player.hp)}/{self.player.max_hp} (+{regen_txt})", 10, 20, arcade.color.RED,
                             14, bold=True)
            arcade.draw_text(f"LVL: {self.player.level} | EXP: {self.player.current_xp}/{self.player.xp_to_next_level}",
                             10, 40, arcade.color.GOLD, 14, bold=True)

            c1 = "READY" if self.player.cd_swing_current <= 0 else f"{self.player.cd_swing_current:.1f}"
            c2 = "READY" if self.player.cd_overhead_current <= 0 else f"{self.player.cd_overhead_current:.1f}"
            arcade.draw_text(f"[Z] Взмах: {c1}", 10, SCREEN_HEIGHT - 30, arcade.color.CYAN, 12)
            arcade.draw_text(f"[X] Удар сверху: {c2}", 10, SCREEN_HEIGHT - 50, arcade.color.ORANGE, 12)
        else:
            arcade.draw_text("GAME OVER", SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2, arcade.color.RED, 30)

        # --- ОТРИСОВКА МЕНЮ ПОВЫШЕНИЯ УРОВНЯ ---
        if self.game_state == STATE_MENU:
            # Затемнение фона
            arcade.draw_lrtb_rectangle_filled(0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, (0, 0, 0, 150))

            # Заголовок
            arcade.draw_text("НОВЫЙ УРОВЕНЬ! ВЫБЕРИТЕ УЛУЧШЕНИЕ", SCREEN_WIDTH / 2, SCREEN_HEIGHT - 150,
                             arcade.color.WHITE, 24, anchor_x="center")

            # СИНЯЯ КНОПКА (Слева)
            arcade.draw_rectangle_filled(SCREEN_WIDTH / 2 - 150, SCREEN_HEIGHT / 2, 200, 300, arcade.color.DARK_BLUE)
            arcade.draw_rectangle_outline(SCREEN_WIDTH / 2 - 150, SCREEN_HEIGHT / 2, 200, 300, arcade.color.CYAN, 3)
            arcade.draw_text("УЛУЧШИТЬ\nВЗМАХ (Z)", SCREEN_WIDTH / 2 - 150, SCREEN_HEIGHT / 2 + 50,
                             arcade.color.WHITE, 16, anchor_x="center", align="center")
            arcade.draw_text("+ Урон\n+ Скорость", SCREEN_WIDTH / 2 - 150, SCREEN_HEIGHT / 2 - 20,
                             arcade.color.LIGHT_BLUE, 12, anchor_x="center", align="center")

            # КРАСНАЯ КНОПКА (Справа)
            arcade.draw_rectangle_filled(SCREEN_WIDTH / 2 + 150, SCREEN_HEIGHT / 2, 200, 300, arcade.color.DARK_RED)
            arcade.draw_rectangle_outline(SCREEN_WIDTH / 2 + 150, SCREEN_HEIGHT / 2, 200, 300, arcade.color.RED, 3)
            arcade.draw_text("УЛУЧШИТЬ\nУДАР СВЕРХУ (X)", SCREEN_WIDTH / 2 + 150, SCREEN_HEIGHT / 2 + 50,
                             arcade.color.WHITE, 16, anchor_x="center", align="center")
            arcade.draw_text("+ Крит. урон\n+ Шанс крита", SCREEN_WIDTH / 2 + 150, SCREEN_HEIGHT / 2 - 20,
                             arcade.color.PINK, 12, anchor_x="center", align="center")

            arcade.draw_text("Нажми левой кнопкой мыши по карточке", SCREEN_WIDTH / 2, 100, arcade.color.GRAY, 14,
                             anchor_x="center")

    def on_update(self, delta_time):
        # Если меню открыто - ставим игру на паузу (не обновляем логику)
        if self.game_state == STATE_MENU:
            return

        if not self.player or self.player.hp <= 0: return

        # Логика игрока
        self.player.update_timers(delta_time)
        self.player.center_x += self.player.change_x
        self.player.center_y += self.player.change_y

        # Логика врагов (теперь передаем список всех врагов для коллизии)
        for enemy in self.enemies:
            enemy.update_ai(delta_time, self.player, self.enemies)

    def handle_attack_result(self, result):
        """ Обработка результата атаки (убийство и опыт) """
        if result and isinstance(result, tuple) and result[0] == "KILL":
            xp_gain = result[1]
            # Вызываем метод игрока (там добавляется +6 макс хп)
            need_menu = self.player.on_kill_enemy(xp_gain)

            # Удаляем мертвых
            for e in self.enemies:
                if e.hp <= 0: e.kill()

            # Если набрался опыт на уровень - ПАУЗА И МЕНЮ
            if need_menu:
                self.game_state = STATE_MENU

    def on_key_press(self, key, modifiers):
        if self.game_state == STATE_MENU:
            return  # Клавиатура отключена в меню

        if self.player.hp <= 0: return

        # Управление
        if key == arcade.key.W:
            self.player.change_y = self.player.speed
        elif key == arcade.key.S:
            self.player.change_y = -self.player.speed
        elif key == arcade.key.A:
            self.player.change_x = -self.player.speed
        elif key == arcade.key.D:
            self.player.change_x = self.player.speed

        # Атаки с проверкой на убийство
        elif key == arcade.key.Z:
            res = self.player.attack_swing(self.enemies)
            self.handle_attack_result(res)
        elif key == arcade.key.X:
            res = self.player.attack_overhead(self.enemies)
            self.handle_attack_result(res)

    def on_key_release(self, key, modifiers):
        if key in [arcade.key.W, arcade.key.S]:
            self.player.change_y = 0
        elif key in [arcade.key.A, arcade.key.D]:
            self.player.change_x = 0

    def on_mouse_press(self, x, y, button, modifiers):
        """ Обработка кликов (для меню) """
        if self.game_state == STATE_MENU:
            # Координаты кнопок
            blue_x = SCREEN_WIDTH / 2 - 150
            red_x = SCREEN_WIDTH / 2 + 150
            btn_width = 100  # половина ширины (200/2)
            btn_height = 150  # половина высоты (300/2)

            # Проверка нажатия на СИНЮЮ (Взмах)
            if (blue_x - btn_width < x < blue_x + btn_width) and \
                    (SCREEN_HEIGHT / 2 - btn_height < y < SCREEN_HEIGHT / 2 + btn_height):

                self.player.stats["swing_dmg"] += 10
                self.player.level_up_apply()
                self.game_state = STATE_PLAYING  # Снимаем с паузы

            # Проверка нажатия на КРАСНУЮ (Удар сверху)
            elif (red_x - btn_width < x < red_x + btn_width) and \
                    (SCREEN_HEIGHT / 2 - btn_height < y < SCREEN_HEIGHT / 2 + btn_height):

                self.player.stats["overhead_dmg_crit"] += 20
                self.player.level_up_apply()
                self.game_state = STATE_PLAYING  # Снимаем с паузы


if __name__ == "__main__":
    game = MyGame()
    game.setup()
    arcade.run()