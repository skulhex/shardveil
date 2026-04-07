from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum

import arcade
from arcade import gui


class OverlayScreenId(str, Enum):
    PAUSE = "pause"
    SETTINGS = "settings"


@dataclass(frozen=True)
class MenuAction:
    label: str
    callback: Callable[[], None]


@dataclass
class OverlayStack:
    _items: list[OverlayScreenId] = field(default_factory=list)

    def push(self, screen_id: OverlayScreenId) -> None:
        self._items.append(screen_id)

    def pop(self) -> OverlayScreenId | None:
        if not self._items:
            return None
        return self._items.pop()

    def clear(self) -> None:
        self._items.clear()

    def current(self) -> OverlayScreenId | None:
        if not self._items:
            return None
        return self._items[-1]

    def depth(self) -> int:
        return len(self._items)

    def is_empty(self) -> bool:
        return not self._items


class OverlayScreen:
    BUTTON_WIDTH = 240
    BUTTON_HEIGHT = 44
    PANEL_WIDTH = 360
    PANEL_HEIGHT = 280

    def __init__(self, screen_id: OverlayScreenId, title: str, actions: list[MenuAction]):
        self.screen_id = screen_id
        self.title = title
        self.actions = actions

    def build(self) -> tuple[gui.UIAnchorLayout, list[gui.UIFlatButton]]:
        root = gui.UIAnchorLayout()
        root.add(gui.UISpace(color=(4, 6, 10, 190), size_hint=(1, 1)))

        panel = gui.UIAnchorLayout(
            width=self.PANEL_WIDTH,
            height=self.PANEL_HEIGHT,
            size_hint=None,
        )
        panel.with_background(color=(20, 22, 28, 235))
        panel.with_border(color=arcade.color.DAVY_GREY, width=2)

        content = gui.UIBoxLayout(vertical=True, space_between=18, align="center")
        content.add(
            gui.UILabel(
                text=self.title,
                width=self.BUTTON_WIDTH,
                align="center",
                font_size=24,
                bold=True,
            )
        )

        buttons: list[gui.UIFlatButton] = []
        for action in self.actions:
            button = gui.UIFlatButton(
                text=action.label,
                width=self.BUTTON_WIDTH,
                height=self.BUTTON_HEIGHT,
                style=_menu_button_style(),
            )

            def _on_click(_event, callback: Callable[[], None] = action.callback) -> None:
                callback()

            button.on_click = _on_click
            content.add(button)
            buttons.append(button)

        panel.add(content, anchor_x="center", anchor_y="center")
        root.add(panel, anchor_x="center", anchor_y="center")
        return root, buttons


class PauseMenuScreen(OverlayScreen):
    def __init__(
        self,
        on_resume: Callable[[], None],
        on_open_settings: Callable[[], None],
        on_main_menu: Callable[[], None],
    ):
        super().__init__(
            OverlayScreenId.PAUSE,
            "Пауза",
            [
                MenuAction("Продолжить", on_resume),
                MenuAction("Настройки", on_open_settings),
                MenuAction("Главное меню", on_main_menu),
            ],
        )


class SettingsScreen(OverlayScreen):
    def __init__(self, on_back: Callable[[], None]):
        super().__init__(
            OverlayScreenId.SETTINGS,
            "Настройки",
            [MenuAction("Назад", on_back)],
        )


class GameUI:
    def __init__(
        self,
        manager: gui.UIManager,
        hud_layer,
        *,
        on_resume: Callable[[], None],
        on_main_menu: Callable[[], None],
    ) -> None:
        self.manager = manager
        self.hud_layer = hud_layer
        self.on_resume = on_resume
        self.on_main_menu = on_main_menu
        self.overlay_stack = OverlayStack()
        self._active_overlay: gui.UIWidget | None = None
        self._current_screen: OverlayScreen | None = None
        self._buttons: list[gui.UIFlatButton] = []
        self._selected_index = 0
        self._screen_factories = {
            OverlayScreenId.PAUSE: self._build_pause_screen,
            OverlayScreenId.SETTINGS: self._build_settings_screen,
        }

    def setup(self) -> None:
        self.manager.enable()
        self.manager.add(self.hud_layer.root)

    def draw(self) -> None:
        self.manager.draw()

    def update_hud(self, health_ratio: float, light_ratio: float) -> None:
        self.hud_layer.update(health_ratio, light_ratio)

    def has_active_overlay(self) -> bool:
        return not self.overlay_stack.is_empty()

    def show_screen(self, screen_id: OverlayScreenId) -> None:
        self.clear_overlay()
        self.push_screen(screen_id)

    def push_screen(self, screen_id: OverlayScreenId) -> None:
        self.overlay_stack.push(screen_id)
        self._render_current_screen()

    def pop_screen(self) -> OverlayScreenId | None:
        popped = self.overlay_stack.pop()
        self._render_current_screen()
        return popped

    def clear_overlay(self) -> None:
        self.overlay_stack.clear()
        self._remove_active_overlay()
        self._current_screen = None
        self._buttons = []
        self._selected_index = 0

    def handle_key_press(self, symbol: int, modifiers: int) -> bool:
        if not self.has_active_overlay():
            return False

        if symbol == arcade.key.ESCAPE:
            if self.overlay_stack.depth() > 1:
                self.pop_screen()
            else:
                self.on_resume()
            return True

        if symbol in (arcade.key.UP, arcade.key.W):
            self._move_selection(-1)
            return True

        if symbol in (arcade.key.DOWN, arcade.key.S):
            self._move_selection(1)
            return True

        if symbol in (arcade.key.ENTER, arcade.key.SPACE):
            self._activate_selected()
            return True

        return False

    def _move_selection(self, step: int) -> None:
        if not self._buttons:
            return
        self._selected_index = (self._selected_index + step) % len(self._buttons)
        self._refresh_button_labels()

    def _activate_selected(self) -> None:
        if self._current_screen is None or not self._current_screen.actions:
            return
        self._current_screen.actions[self._selected_index].callback()

    def _render_current_screen(self) -> None:
        self._remove_active_overlay()

        current_id = self.overlay_stack.current()
        if current_id is None:
            self._current_screen = None
            self._buttons = []
            self._selected_index = 0
            return

        screen = self._screen_factories[current_id]()
        root, buttons = screen.build()
        self.manager.add(root)

        self._active_overlay = root
        self._current_screen = screen
        self._buttons = buttons
        self._selected_index = 0
        self._refresh_button_labels()

    def _remove_active_overlay(self) -> None:
        if self._active_overlay is None:
            return
        self.manager.remove(self._active_overlay)
        self._active_overlay = None

    def _refresh_button_labels(self) -> None:
        if self._current_screen is None:
            return
        for index, button in enumerate(self._buttons):
            label = self._current_screen.actions[index].label
            button.text = f"> {label} <" if index == self._selected_index else label
            button.trigger_full_render()

    def _build_pause_screen(self) -> PauseMenuScreen:
        return PauseMenuScreen(
            on_resume=self.on_resume,
            on_open_settings=lambda: self.push_screen(OverlayScreenId.SETTINGS),
            on_main_menu=self.on_main_menu,
        )

    def _build_settings_screen(self) -> SettingsScreen:
        return SettingsScreen(on_back=self.pop_screen)


def _menu_button_style() -> dict[str, dict[str, object]]:
    style = deepcopy(gui.UIFlatButton.DEFAULT_STYLE)
    style["normal"].font_size = 14
    style["normal"].font_color = arcade.color.WHITE
    style["normal"].border = arcade.color.DAVY_GREY
    style["normal"].bg = arcade.color.BLACK
    style["hover"].font_size = 14
    style["hover"].border = arcade.color.DAVY_GREY
    style["hover"].bg = arcade.color.DARK_MIDNIGHT_BLUE
    style["press"].font_size = 14
    style["press"].border = arcade.color.DAVY_GREY
    style["press"].bg = arcade.color.DARK_SLATE_BLUE
    style["disabled"].font_size = 14
    style["disabled"].font_color = arcade.color.GRAY
    return style
