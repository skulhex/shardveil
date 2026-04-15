import time
from collections import deque
import arcade


class Message:
    def __init__(self, text: str, kind: str):
        self.text = text
        self.kind = kind
        self.time = time.time()


class MessageLog:
    COLORS = {
        "info": arcade.color.LIGHT_GRAY,
        "combat": arcade.color.ORANGE_RED,
        "system": arcade.color.GOLD,
    }

    def __init__(self, x=10, y=70, width=350, line_height=18, max_messages=6):
        self.x = x
        self.y = y
        self.width = width
        self.line_height = line_height
        self.max_messages = max_messages

        self.messages: deque[Message] = deque()
        self._text_objects: list[arcade.Text] = []
        self._dirty = True

        # API

    def push(self, text: str, kind: str = "info"):
        self.messages.append(Message(text, kind))

        while len(self.messages) > self.max_messages:
            self.messages.popleft()

        self._dirty = True

    def clear(self):
        self.messages.clear()
        self._dirty = True

    # INTERNAL

    def _rebuild(self):
        self._text_objects.clear()

        y_offset = 0

        for msg in reversed(self.messages):
            color = self.COLORS.get(msg.kind, arcade.color.WHITE)

            text = arcade.Text(
                msg.text,
                self.x,
                self.y + y_offset,
                color,
                14,
                width=self.width,
                multiline=True,
            )

            self._text_objects.append(text)
            y_offset += self.line_height

        self._dirty = False

    #  DRAW

    def draw(self):
        # фон
        arcade.draw_lrbt_rectangle_filled(
            self.x - 5,
            self.x + self.width,
            self.y - 5,
            self.y + self.line_height * self.max_messages + 5,
            (0, 0, 0, 120),
        )

        if self._dirty:
            self._rebuild()

        for text in self._text_objects:
            text.draw()