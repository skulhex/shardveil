from __future__ import annotations

import arcade
from arcade import gui


class ProgressBar(gui.UIAnchorLayout):
    value = gui.Property(0.0)

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

        self._bar = gui.UISpace(color=color, size_hint=(value, 1))
        self.add(self._bar, anchor_x="left", anchor_y="top")
        self.value = value
        gui.bind(self, "value", self.trigger_render)

    def update_bar(self) -> None:
        self._bar.size_hint = (self.value, 1)
        self._bar.visible = self.value > 0


class HUDLayer:
    def __init__(self) -> None:
        self.root = gui.UIAnchorLayout()
        bars_layout = gui.UIBoxLayout(vertical=False, space_between=20, align="center")

        self.health_bar = ProgressBar(
            color=arcade.color.RED,
            value=1.0,
            width=200,
            height=15,
        )
        bars_layout.add(self.health_bar)

        self.light_bar = ProgressBar(
            color=arcade.color.GOLD,
            value=1.0,
            width=200,
            height=15,
        )
        bars_layout.add(self.light_bar)

        self.root.add(
            bars_layout,
            anchor_x="left",
            anchor_y="bottom",
            align_x=8,
            align_y=10,
        )

    def update(self, health_ratio: float, light_ratio: float) -> None:
        self.health_bar.value = max(0.0, min(1.0, health_ratio))
        self.health_bar.update_bar()

        self.light_bar.value = max(0.0, min(1.0, light_ratio))
        self.light_bar.update_bar()
