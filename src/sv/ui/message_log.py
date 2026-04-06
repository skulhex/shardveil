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

    def __init__(
        self,
        x=10,
        y=100,
        width=400,
        line_height=18,
        max_messages=8,
    ):
        self.x = x
        self.y = y
        self.width = width
        self.line_height = line_height
        self.max_messages = max_messages

        self.messages: deque[Message] = deque()

    # API
    def push(self, text: str, kind: str = "info"):
        self.messages.append(Message(text, kind))

        # ограничение размера
        while len(self.messages) > self.max_messages:
            self.messages.popleft()

    def clear(self):
        self.messages.clear()

    def draw(self):
        """Рисует лог поверх HUD"""
        y_offset = 0

        for msg in self.messages:
            color = self.COLORS.get(msg.kind, arcade.color.WHITE)

            arcade.draw_text(
                msg.text,
                self.x,
                self.y + y_offset,
                color,
                14,
                width=self.width,
            )

            y_offset += self.line_height