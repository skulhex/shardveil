import arcade
from arcade import gui


class ProgressBar(arcade.gui.UIAnchorLayout):
    value = arcade.gui.Property(0.0)

    def __init__(
        self,
        value: float = 1.0,
        width: int = 100,
        height: int = 20,
        color: arcade.types.Color = arcade.color.GREEN,
    ):
        super().__init__(width=width, height=height, size_hint=None)
        self.with_background(color=arcade.uicolor.GRAY_CONCRETE)
        self.with_border(color=arcade.uicolor.BLACK)

        self._bar = arcade.gui.UISpace(color=color, size_hint=(value, 1))
        self.add(self._bar, anchor_x="left", anchor_y="top")
        self.value = value
        arcade.gui.bind(self, "value", self.trigger_render)

    def update_bar(self):
        self._bar.size_hint = (self.value, 1)
        self._bar.visible = self.value > 0


