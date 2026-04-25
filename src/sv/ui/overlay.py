from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum

import arcade
from arcade import gui


class ViewScreenId(str, Enum):
    MAIN_MENU = "main_menu"
    SETTINGS = "settings"


class OverlayScreenId(str, Enum):
    PAUSE = "pause"
    SETTINGS = "settings"
    INVENTORY = "inventory"


@dataclass(frozen=True)
class MenuAction:
    label: str
    callback: Callable[[], None]


@dataclass
class ScreenStack:
    _items: list[Enum] = field(default_factory=list)

    def push(self, screen_id: Enum) -> None:
        self._items.append(screen_id)

    def pop(self) -> Enum | None:
        if not self._items:
            return None
        return self._items.pop()

    def clear(self) -> None:
        self._items.clear()

    def current(self) -> Enum | None:
        if not self._items:
            return None
        return self._items[-1]

    def depth(self) -> int:
        return len(self._items)

    def is_empty(self) -> bool:
        return not self._items


@dataclass(frozen=True)
class MenuVisualSpec:
    button_width: int
    button_height: int
    panel_width: int
    panel_height: int
    title_font_size: int
    overlay_color: arcade.types.Color


OVERLAY_VISUAL_SPEC = MenuVisualSpec(
    button_width=240,
    button_height=44,
    panel_width=360,
    panel_height=280,
    title_font_size=24,
    overlay_color=(4, 6, 10, 190),
)

VIEW_VISUAL_SPEC = MenuVisualSpec(
    button_width=280,
    button_height=48,
    panel_width=420,
    panel_height=340,
    title_font_size=40,
    overlay_color=(8, 10, 16, 255),
)


class MenuScreen:
    def __init__(self, screen_id: Enum, title: str, actions: list[MenuAction], visual: MenuVisualSpec):
        self.screen_id = screen_id
        self.title = title
        self.actions = actions
        self.visual = visual

    def build(self) -> tuple[gui.UIAnchorLayout, list[gui.UIFlatButton]]:
        root = gui.UIAnchorLayout()
        root.add(gui.UISpace(color=self.visual.overlay_color, size_hint=(1, 1)))

        panel = gui.UIAnchorLayout(
            width=self.visual.panel_width,
            height=self.visual.panel_height,
            size_hint=None,
        )
        panel.with_background(color=(20, 22, 28, 235))
        panel.with_border(color=arcade.color.DAVY_GREY, width=2)

        content = gui.UIBoxLayout(vertical=True, space_between=18, align="center")
        content.add(
            gui.UILabel(
                text=self.title,
                width=self.visual.button_width,
                align="center",
                font_size=self.visual.title_font_size,
                bold=True,
            )
        )

        buttons: list[gui.UIFlatButton] = []
        for action in self.actions:
            button = gui.UIFlatButton(
                text=action.label,
                width=self.visual.button_width,
                height=self.visual.button_height,
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

    def handle_key_press(self, symbol: int) -> bool:
        return False


class MainMenuScreen(MenuScreen):
    def __init__(
        self,
        on_new_game: Callable[[], None],
        on_open_settings: Callable[[], None],
        on_exit_game: Callable[[], None],
    ):
        super().__init__(
            ViewScreenId.MAIN_MENU,
            "Shardveil",
            [
                MenuAction("Новая игра", on_new_game),
                MenuAction("Настройки", on_open_settings),
                MenuAction("Выйти из игры", on_exit_game),
            ],
            VIEW_VISUAL_SPEC,
        )


class PauseMenuScreen(MenuScreen):
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
            OVERLAY_VISUAL_SPEC,
        )


class SettingsScreen(MenuScreen):
    def __init__(self, on_back: Callable[[], None], *, visual: MenuVisualSpec):
        super().__init__(
            ViewScreenId.SETTINGS if visual is VIEW_VISUAL_SPEC else OverlayScreenId.SETTINGS,
            "Настройки",
            [MenuAction("Назад", on_back)],
            visual,
        )


class GameUI:
    def __init__(
        self,
        manager: gui.UIManager,
        hud_layer,
        *,
        on_resume: Callable[[], None],
        on_main_menu: Callable[[], None],
        on_new_game: Callable[[], None],
        on_exit_game: Callable[[], None],
    ) -> None:
        self.manager = manager
        self.hud_layer = hud_layer
        self.on_resume = on_resume
        self.on_main_menu = on_main_menu
        self.on_new_game = on_new_game
        self.on_exit_game = on_exit_game
        self.overlay_stack: ScreenStack = ScreenStack()
        self.view_stack: ScreenStack = ScreenStack()
        self._active_overlay: gui.UIWidget | None = None
        self._active_view: gui.UIWidget | None = None
        self._current_overlay_screen: MenuScreen | None = None
        self._current_view_screen: MenuScreen | None = None
        self._inventory_source = None
        self._overlay_buttons: list[gui.UIFlatButton] = []
        self._view_buttons: list[gui.UIFlatButton] = []
        self._overlay_selected_index = 0
        self._view_selected_index = 0
        self._overlay_factories = {
            OverlayScreenId.PAUSE: self._build_pause_screen,
            OverlayScreenId.SETTINGS: self._build_overlay_settings_screen,
            OverlayScreenId.INVENTORY: self._build_inventory_screen,
        }
        self._view_factories = {
            ViewScreenId.MAIN_MENU: self._build_main_menu_screen,
            ViewScreenId.SETTINGS: self._build_view_settings_screen,
        }

    def setup(self) -> None:
        self.manager.enable()
        self.manager.add(self.hud_layer.root)

    def draw(self) -> None:
        self.manager.draw()

    def set_hud_visible(self, visible: bool) -> None:
        self.hud_layer.root.visible = visible

    def update_hud(self, health_ratio: float, light_ratio: float) -> None:
        self.hud_layer.update(health_ratio, light_ratio)

    def show_view_screen(self, screen_id: ViewScreenId) -> None:
        self.clear_overlay()
        self.view_stack.clear()
        self.view_stack.push(screen_id)
        self._render_view_screen()

    def push_view_screen(self, screen_id: ViewScreenId) -> None:
        self.view_stack.push(screen_id)
        self._render_view_screen()

    def pop_view_screen(self) -> ViewScreenId | None:
        popped = self.view_stack.pop()
        self._render_view_screen()
        return popped

    def clear_view_screen(self) -> None:
        self.view_stack.clear()
        self._remove_active_view()
        self._current_view_screen = None
        self._view_buttons = []
        self._view_selected_index = 0

    def has_active_view(self) -> bool:
        return not self.view_stack.is_empty()

    def has_active_overlay(self) -> bool:
        return not self.overlay_stack.is_empty()

    def show_screen(self, screen_id: OverlayScreenId) -> None:
        self.clear_overlay()
        self.push_screen(screen_id)

    def show_inventory(self, inventory) -> None:
        self.clear_overlay()
        self._inventory_source = inventory
        self.push_screen(OverlayScreenId.INVENTORY)

    def push_screen(self, screen_id: OverlayScreenId) -> None:
        self.overlay_stack.push(screen_id)
        self._render_overlay_screen()

    def pop_screen(self) -> OverlayScreenId | None:
        popped = self.overlay_stack.pop()
        self._render_overlay_screen()
        return popped

    def clear_overlay(self) -> None:
        self.overlay_stack.clear()
        self._remove_active_overlay()
        self._current_overlay_screen = None
        self._overlay_buttons = []
        self._overlay_selected_index = 0
        self._inventory_source = None

    def handle_key_press(self, symbol: int, modifiers: int) -> bool:
        if self.has_active_overlay():
            return self._handle_overlay_key_press(symbol)
        if self.has_active_view():
            return self._handle_view_key_press(symbol)
        return False

    def _handle_overlay_key_press(self, symbol: int) -> bool:
        if symbol == arcade.key.ESCAPE:
            if self.overlay_stack.depth() > 1:
                self.pop_screen()
            else:
                self.on_resume()
            return True
        screen = self._current_overlay_screen
        if screen is None:
            return False
        if getattr(screen, "panel", None) is not None:
            handle_key_press = getattr(screen, "handle_key_press", None)
            if callable(handle_key_press):
                return bool(handle_key_press(symbol))
        return self._handle_menu_navigation(symbol, overlay=True)

    def _handle_view_key_press(self, symbol: int) -> bool:
        return self._handle_menu_navigation(symbol, overlay=False)

    def _handle_menu_navigation(self, symbol: int, *, overlay: bool) -> bool:
        if symbol in (arcade.key.UP, arcade.key.W):
            self._move_selection(-1, overlay=overlay)
            return True
        if symbol in (arcade.key.DOWN, arcade.key.S):
            self._move_selection(1, overlay=overlay)
            return True
        if symbol in (arcade.key.ENTER, arcade.key.SPACE):
            self._activate_selected(overlay=overlay)
            return True
        return False

    def _move_selection(self, step: int, *, overlay: bool) -> None:
        buttons = self._overlay_buttons if overlay else self._view_buttons
        if not buttons:
            return
        if overlay:
            self._overlay_selected_index = (self._overlay_selected_index + step) % len(buttons)
            self._refresh_button_labels(overlay=True)
        else:
            self._view_selected_index = (self._view_selected_index + step) % len(buttons)
            self._refresh_button_labels(overlay=False)

    def _activate_selected(self, *, overlay: bool) -> None:
        screen = self._current_overlay_screen if overlay else self._current_view_screen
        index = self._overlay_selected_index if overlay else self._view_selected_index
        if screen is None or not screen.actions:
            return
        screen.actions[index].callback()

    def _render_overlay_screen(self) -> None:
        self._remove_active_overlay()

        current_id = self.overlay_stack.current()
        if current_id is None:
            self._current_overlay_screen = None
            self._overlay_buttons = []
            self._overlay_selected_index = 0
            return

        screen = self._overlay_factories[current_id]()
        root, buttons = screen.build()
        self.manager.add(root)
        self._active_overlay = root
        self._current_overlay_screen = screen
        self._overlay_buttons = buttons
        self._overlay_selected_index = 0
        if buttons:
            self._refresh_button_labels(overlay=True)

    def _render_view_screen(self) -> None:
        self._remove_active_view()

        current_id = self.view_stack.current()
        if current_id is None:
            self._current_view_screen = None
            self._view_buttons = []
            self._view_selected_index = 0
            return

        screen = self._view_factories[current_id]()
        root, buttons = screen.build()
        self.manager.add(root)
        self._active_view = root
        self._current_view_screen = screen
        self._view_buttons = buttons
        self._view_selected_index = 0
        self._refresh_button_labels(overlay=False)

    def _remove_active_overlay(self) -> None:
        if self._active_overlay is None:
            return
        self.manager.remove(self._active_overlay)
        self._active_overlay = None

    def _remove_active_view(self) -> None:
        if self._active_view is None:
            return
        self.manager.remove(self._active_view)
        self._active_view = None

    def _refresh_button_labels(self, *, overlay: bool) -> None:
        if overlay:
            screen = self._current_overlay_screen
            buttons = self._overlay_buttons
            selected_index = self._overlay_selected_index
        else:
            screen = self._current_view_screen
            buttons = self._view_buttons
            selected_index = self._view_selected_index

        if screen is None or not hasattr(screen, "actions"):
            return
        for index, button in enumerate(buttons):
            label = screen.actions[index].label
            button.text = f"> {label} <" if index == selected_index else label
            button.trigger_full_render()

    def _build_main_menu_screen(self) -> MainMenuScreen:
        return MainMenuScreen(
            on_new_game=self.on_new_game,
            on_open_settings=lambda: self.push_view_screen(ViewScreenId.SETTINGS),
            on_exit_game=self.on_exit_game,
        )

    def _build_pause_screen(self) -> PauseMenuScreen:
        return PauseMenuScreen(
            on_resume=self.on_resume,
            on_open_settings=lambda: self.push_screen(OverlayScreenId.SETTINGS),
            on_main_menu=self.on_main_menu,
        )

    def _build_overlay_settings_screen(self) -> SettingsScreen:
        return SettingsScreen(on_back=self.pop_screen, visual=OVERLAY_VISUAL_SPEC)

    def _build_view_settings_screen(self) -> SettingsScreen:
        return SettingsScreen(on_back=self.pop_view_screen, visual=VIEW_VISUAL_SPEC)

    def _build_inventory_screen(self):
        from .inventory import InventoryScreen

        if self._inventory_source is None:
            raise RuntimeError("Inventory screen requested without inventory data")
        return InventoryScreen(inventory=self._inventory_source, on_close=self.on_resume)


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
