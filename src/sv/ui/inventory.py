from __future__ import annotations

from dataclasses import dataclass

import arcade
from arcade import gui
from arcade.gui import events
from arcade.gui.widgets import EVENT_HANDLED, EVENT_UNHANDLED

from sv.items import EQUIPMENT_SLOT_ORDER, Inventory, STORAGE_COLUMNS, STORAGE_ROWS, load_item_textures


GRID_COLUMNS = 1 + STORAGE_COLUMNS
GRID_ROWS = STORAGE_ROWS
CELL_SIZE = 60
CELL_GAP = 8
PANEL_PADDING = 18
HEADER_HEIGHT = 36
FOOTER_HEIGHT = 20
DETAILS_PANEL_WIDTH = 250
DETAILS_GAP = 16
INFO_PANEL_PADDING = 0


def _grid_width() -> float:
    return GRID_COLUMNS * CELL_SIZE + (GRID_COLUMNS - 1) * CELL_GAP


def _grid_height() -> float:
    return GRID_ROWS * CELL_SIZE + (GRID_ROWS - 1) * CELL_GAP


def panel_size() -> tuple[float, float]:
    width = PANEL_PADDING * 2 + _grid_width() + DETAILS_GAP + DETAILS_PANEL_WIDTH
    height = PANEL_PADDING * 2 + HEADER_HEIGHT + FOOTER_HEIGHT + _grid_height()
    return width, height


@dataclass(slots=True)
class InventoryFocus:
    """Класс для отслеживания текущей сфокусированной ячейки в инвентаре."""
    column: int = 0
    row: int = 0

    def clamp(self) -> None:
        self.column = max(0, min(GRID_COLUMNS - 1, self.column))
        self.row = max(0, min(GRID_ROWS - 1, self.row))

    def as_tuple(self) -> tuple[int, int]:
        return self.column, self.row


class InventoryPanel(gui.UIWidget):
    """Панель инвентаря, отображающая экипировку и хранилище персонажа, а также детали выбранного предмета."""
    def __init__(self, inventory: Inventory):
        width, height = panel_size()
        super().__init__(width=width, height=height)
        self.inventory = inventory
        self.focus = InventoryFocus()
        self.hover_cell: tuple[int, int] | None = None
        self.selected_source: tuple[int, int] | None = None
        self._textures = load_item_textures()

    def handle_key_press(self, symbol: int) -> bool:
        if symbol == arcade.key.LEFT:
            self.focus.column = (self.focus.column - 1) % GRID_COLUMNS
            self.trigger_render()
            return True
        if symbol == arcade.key.RIGHT:
            self.focus.column = (self.focus.column + 1) % GRID_COLUMNS
            self.trigger_render()
            return True
        if symbol == arcade.key.UP:
            self.focus.row = (self.focus.row - 1) % GRID_ROWS
            self.trigger_render()
            return True
        if symbol == arcade.key.DOWN:
            self.focus.row = (self.focus.row + 1) % GRID_ROWS
            self.trigger_render()
            return True
        if symbol in (arcade.key.W, arcade.key.A, arcade.key.S, arcade.key.D):
            if symbol == arcade.key.W:
                return self.handle_key_press(arcade.key.UP)
            if symbol == arcade.key.S:
                return self.handle_key_press(arcade.key.DOWN)
            if symbol == arcade.key.A:
                return self.handle_key_press(arcade.key.LEFT)
            if symbol == arcade.key.D:
                return self.handle_key_press(arcade.key.RIGHT)
        if symbol in (arcade.key.SPACE, arcade.key.ENTER):
            self._activate_focused_cell()
            return True
        return False

    def on_event(self, event: events.UIEvent) -> bool | None:
        if isinstance(event, events.UIMouseMovementEvent):
            cell = self._cell_at_point(event.x, event.y)
            self.hover_cell = cell
            if cell is not None:
                self.focus.column, self.focus.row = cell
            self.trigger_render()
            return EVENT_HANDLED

        if isinstance(event, events.UIMousePressEvent):
            if event.button != arcade.MOUSE_BUTTON_LEFT:
                return EVENT_UNHANDLED
            cell = self._cell_at_point(event.x, event.y)
            if cell is None:
                return EVENT_UNHANDLED
            self.focus.column, self.focus.row = cell
            self.hover_cell = cell
            self._activate_focused_cell()
            return EVENT_HANDLED

        return super().on_event(event)

    def do_render(self, surface: gui.Surface) -> None:
        """Отрисовка панели инвентаря, включая сетку ячеек, экипировку, хранилище и панель деталей."""
        self.prepare_render(surface)

        menu_rect = arcade.LBWH(0, 0, self.width, self.height)
        grid_rect = self._grid_panel_rect()
        info_rect = self._info_panel_rect()

        arcade.draw_rect_filled(menu_rect, color=(18, 20, 28, 255))
        arcade.draw_rect_outline(menu_rect, color=(94, 102, 118, 255), border_width=2)
        title_y = menu_rect.top - PANEL_PADDING
        self._draw_panel_title("Инвентарь", grid_rect.left, title_y)
        self._draw_panel_title("Детали", info_rect.left, title_y)

        self._draw_text(
            "I или Esc - закрыть, Space или Enter - взять/положить",
            PANEL_PADDING,
            PANEL_PADDING // 2,
            color=(164, 170, 184, 255),
            font_size=11,
            anchor_y="bottom",
        )

        self._draw_grid()
        self._draw_info_panel(info_rect)

    def _activate_focused_cell(self) -> None:
        focus_cell = self.focus.as_tuple()

        if self.selected_source is None:
            stack = self.inventory.get_cell(*focus_cell)
            if stack is None:
                self.trigger_render()
                return
            self.selected_source = focus_cell
            self.trigger_render()
            return

        if self.selected_source == focus_cell:
            self.selected_source = None
            self.trigger_render()
            return

        source_column, source_row = self.selected_source
        result = self.inventory.transfer_between_cells(source_column, source_row, focus_cell[0], focus_cell[1])
        if result.moved:
            self.selected_source = None
        self.trigger_render()

    def _draw_grid(self) -> None:
        for row in range(GRID_ROWS):
            self._draw_equipment_cell(row)
            for column in range(1, GRID_COLUMNS):
                self._draw_storage_cell(column, row)

    def _draw_equipment_cell(self, row: int) -> None:
        slot = EQUIPMENT_SLOT_ORDER[row]
        rect = self._cell_rect(0, row)
        self._draw_cell_background(
            rect,
            selected=self.focus.as_tuple() == (0, row),
            equipment=True,
            source=self.selected_source == (0, row),
        )
        stack = self.inventory.get_equipment(slot)
        if stack is not None:
            self._draw_stack(stack, rect)
        else:
            self._draw_slot_label(slot.label, rect)

    def _draw_storage_cell(self, column: int, row: int) -> None:
        rect = self._cell_rect(column, row)
        self._draw_cell_background(
            rect,
            selected=self.focus.as_tuple() == (column, row),
            equipment=False,
            source=self.selected_source == (column, row),
        )
        stack = self.inventory.storage_cell(row, column - 1)
        if stack is not None:
            self._draw_stack(stack, rect)

    def _draw_info_panel(self, rect: arcade.types.Rect) -> None:
        info_cell = self.hover_cell or self.focus.as_tuple()
        selected_stack = self.inventory.get_cell(*info_cell)

        if selected_stack is None:
            selected_label = self.inventory.cell_label(*info_cell)
            self._draw_text(
                selected_label,
                rect.left + INFO_PANEL_PADDING,
                rect.top - HEADER_HEIGHT - 12,
                color=(235, 238, 245, 255),
                font_size=12,
                bold=True,
                anchor_y="top",
            )
            self._draw_text(
                "Пусто",
                rect.left + INFO_PANEL_PADDING,
                rect.top - HEADER_HEIGHT - 40,
                color=(142, 149, 163, 255),
                font_size=11,
                anchor_y="top",
            )
        else:
            content_top = rect.top - HEADER_HEIGHT - 8
            self._draw_item_preview(selected_stack, rect.left + INFO_PANEL_PADDING, content_top)
            text_left = rect.left + INFO_PANEL_PADDING + 52
            self._draw_text(
                selected_stack.definition.name,
                text_left,
                content_top,
                color=(235, 238, 245, 255),
                font_size=13,
                bold=True,
                anchor_y="top",
            )
            self._draw_text(
                selected_stack.definition.kind_label,
                text_left,
                content_top - 20,
                color=(164, 170, 184, 255),
                font_size=10,
                anchor_y="top",
            )
            self._draw_wrapped_text(
                selected_stack.definition.description,
                rect.left + INFO_PANEL_PADDING,
                content_top - 54,
                width=rect.width - INFO_PANEL_PADDING * 2,
                color=(211, 215, 223, 255),
                font_size=10,
            )

    def _draw_panel_title(self, title: str, x: float, y: float) -> None:
        self._draw_text(
            title,
            x,
            y,
            color=(235, 238, 245, 255),
            font_size=14,
            bold=True,
            anchor_y="top",
        )

    def _draw_cell_background(self, rect: arcade.types.Rect, *, selected: bool, equipment: bool, source: bool) -> None:
        base_color = (37, 42, 55, 245) if equipment else (28, 31, 40, 245)
        border_color = (106, 115, 131, 255) if equipment else (74, 81, 95, 255)
        arcade.draw_rect_filled(rect, color=base_color)
        arcade.draw_rect_outline(rect, color=border_color, border_width=2)
        if selected:
            arcade.draw_rect_outline(rect, color=(84, 188, 224, 255), border_width=3)
        if source:
            arcade.draw_rect_outline(rect, color=(219, 186, 78, 255), border_width=4)

    def _draw_item_preview(self, stack, left: float, top: float) -> None:
        texture = self._textures[stack.definition.icon_index]
        icon_rect = arcade.LBWH(left, top - 40, 40, 40)
        arcade.draw_texture_rect(texture, icon_rect, pixelated=True)
        if stack.quantity > 1:
            self._draw_text(
                str(stack.quantity),
                left + 38,
                top - 2,
                color=(255, 255, 255, 255),
                font_size=11,
                bold=True,
                anchor_x="right",
                anchor_y="top",
            )

    def _draw_stack(self, stack, rect: arcade.types.Rect) -> None:
        texture = self._textures[stack.definition.icon_index]
        icon_size = CELL_SIZE - 20
        icon_rect = arcade.LBWH(
            rect.left + (rect.width - icon_size) / 2,
            rect.bottom + (rect.height - icon_size) / 2,
            icon_size,
            icon_size,
        )
        arcade.draw_texture_rect(texture, icon_rect, pixelated=True)

        if stack.quantity > 1:
            self._draw_text(
                str(stack.quantity),
                rect.left + rect.width - 18,
                rect.bottom + 4,
                color=(255, 255, 255, 255),
                font_size=12,
                bold=True,
                anchor_x="right",
                anchor_y="bottom",
            )

    def _draw_slot_label(self, label: str, rect: arcade.types.Rect) -> None:
        self._draw_text(
            label,
            rect.left + rect.width / 2,
            rect.bottom + rect.height / 2,
            color=(142, 149, 163, 255),
            font_size=9,
            align="center",
            anchor_x="center",
            anchor_y="center",
            width=int(rect.width - 10),
            multiline=True,
        )

    def _draw_text(self, text: str, x: float, y: float, **kwargs) -> None:
        arcade.Text(text, x, y, **kwargs).draw()

    def _draw_wrapped_text(self, text: str, x: float, y: float, *, width: float, color: arcade.types.Color, font_size: int) -> None:
        arcade.Text(
            text,
            x,
            y,
            color=color,
            font_size=font_size,
            width=int(width),
            multiline=True,
            anchor_y="top",
        ).draw()

    def _grid_panel_rect(self) -> arcade.types.Rect:
        width = PANEL_PADDING * 2 + _grid_width()
        height = self.height - PANEL_PADDING * 2
        return arcade.LBWH(PANEL_PADDING, PANEL_PADDING, width, height)

    def _info_panel_rect(self) -> arcade.types.Rect:
        left = PANEL_PADDING + _grid_width() + DETAILS_GAP
        width = DETAILS_PANEL_WIDTH
        height = self.height - PANEL_PADDING * 2
        return arcade.LBWH(left, PANEL_PADDING, width, height)

    def _cell_rect(self, column: int, row: int) -> arcade.types.Rect:
        left = PANEL_PADDING + column * (CELL_SIZE + CELL_GAP)
        top = self.height - PANEL_PADDING - HEADER_HEIGHT
        bottom = top - (row + 1) * CELL_SIZE - row * CELL_GAP
        return arcade.LBWH(left, bottom, CELL_SIZE, CELL_SIZE)

    def _cell_at_point(self, x: float, y: float) -> tuple[int, int] | None:
        local_x = x - self.left
        local_y = y - self.bottom
        if not (PANEL_PADDING <= local_x <= self.width - PANEL_PADDING):
            return None
        grid_top = self.height - PANEL_PADDING - HEADER_HEIGHT
        grid_bottom = grid_top - _grid_height()
        if not (grid_bottom <= local_y <= grid_top):
            return None

        for row in range(GRID_ROWS):
            for column in range(GRID_COLUMNS):
                rect = self._cell_rect(column, row)
                if rect.left <= local_x <= rect.left + rect.width and rect.bottom <= local_y <= rect.bottom + rect.height:
                    return column, row
        return None


class InventoryScreen:
    """Экран инвентаря, отображающий панель инвентаря и обрабатывающий её события."""
    def __init__(self, inventory: Inventory, on_close):
        self.inventory = inventory
        self.on_close = on_close
        self.panel: InventoryPanel | None = None

    def build(self) -> tuple[gui.UIAnchorLayout, list[gui.UIFlatButton]]:
        root = gui.UIAnchorLayout()
        root.add(gui.UISpace(color=(4, 6, 10, 190), size_hint=(1, 1)))

        panel = InventoryPanel(self.inventory)
        self.panel = panel
        root.add(panel, anchor_x="center", anchor_y="center")
        return root, []

    def handle_key_press(self, symbol: int) -> bool:
        if symbol in (arcade.key.I, arcade.key.ESCAPE):
            self.on_close()
            return True
        if self.panel is None:
            return False
        return self.panel.handle_key_press(symbol)
