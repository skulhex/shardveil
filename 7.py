import arcade

# Настройки игрового окна
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN_TITLE = "My Platformer"

# Настройки персонажа
MOVEMENT_SPEED = 5
JUMP_SPEED = 12
GRAVITY = 0.5


class MyGame(arcade.Window):
    def __init__(self, width, height, title):
        super().__init__(width, height, title)

        # Цвет фона
        arcade.set_background_color(arcade.color.SKY_BLUE)

        # --- Создаём списки спрайтов ---
        self.scene = arcade.Scene()

        # Добавляем землю
        ground = arcade.Sprite("assets/Снимок экрана 2025-07-09 182924.png")
        ground.center_x = 400
        ground.center_y = 32
        self.scene.add_sprite("ground", ground)

        # Добавляем игрока
        player = arcade.Sprite("assets/говяшки.png", 0.5)
        player.center_x = 50
        player.center_y = 100
        self.scene.add_sprite("player", player)

        # Сохраняем ссылки
        self.player_sprite = player
        self.ground_sprite = ground

        # Для движения
        self.direction = 1
        self.current_keys = set()

    def on_draw(self):
        self.clear()
        self.scene.draw()  # ✅ Отрисовка всех спрайтов

    def on_update(self, delta_time):
        # Гравитация
        self.player_sprite.change_y -= GRAVITY
        self.player_sprite.center_x += self.player_sprite.change_x
        self.player_sprite.center_y += self.player_sprite.change_y

        # Столкновение с землёй
        if self.player_sprite.center_y < self.ground_sprite.center_y + 32:
            self.player_sprite.center_y = self.ground_sprite.center_y + 32
            self.player_sprite.change_y = 0

        # Автоматическое движение
        self.player_sprite.center_x += self.direction * MOVEMENT_SPEED
        if self.player_sprite.right >= SCREEN_WIDTH:
            self.direction = -1
        elif self.player_sprite.left <= 0:
            self.direction = 1

        # Прыжок
        if arcade.key.SPACE in self.current_keys:
            if abs(self.player_sprite.center_y - (self.ground_sprite.center_y + 32)) < 1:
                self.player_sprite.change_y = JUMP_SPEED

        # Проверки
        if self.player_sprite.bottom <= 0:
            print("Game over")
        if self.player_sprite.center_x >= SCREEN_WIDTH - 50:
            print("You win")

    def on_key_press(self, key, modifiers):
        self.current_keys.add(key)
        if key == arcade.key.A:
            self.player_sprite.change_x = -MOVEMENT_SPEED
        elif key == arcade.key.D:
            self.player_sprite.change_x = MOVEMENT_SPEED

    def on_key_release(self, key, modifiers):
        self.current_keys.discard(key)
        if key in (arcade.key.A, arcade.key.D):
            self.player_sprite.change_x = 0


# Запуск игры
window = MyGame(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
arcade.run()





            # import arcade
# from arcade import draw_text
# def zapusk():
#
#     # Задать константы для размеров экрана
#     SCREEN_WIDTH = 1920
#     SCREEN_HEIGHT = 1240
#     # Настройки персонажа
#     MOVEMENT_SPEED = 5
#     JUMP_SPEED = 12
#     GRAVITY = 0.5
#
#     # Открыть окно. Задать заголовок и размеры окна (ширина и высота)
#     arcade.open_window(SCREEN_WIDTH, SCREEN_HEIGHT, "Drawing Example")
#     # Определяем размеры текста
#     # Задать белый цвет фона.
#     # Для просмотра списка названий цветов прочитайте:
#     # http://arcade.academy/arcade.color.html
#     # Цвета также можно задавать в (красный, зеленый, синий) и
#     # (красный, зеленый, синий, альфа) формате.
#     arcade.set_background_color(arcade.color.BLACK)
#             # И так далее для остальных направлений
#     # Начать процесс рендера. Это нужно сделать до команд рисования
#     arcade.start_render()
#     arcade.draw_text("𝕬𝖘𝖍𝖊𝖘 𝖔𝖋 𝖙𝖍𝖊 𝖀𝖓𝖉𝖊𝖗𝖜𝖔𝖗𝖑𝖉", 700, 700, arcade.color.WHITE, 48)
#     arcade.finish_render()
#
#     arcade.run()
# zapusk()

