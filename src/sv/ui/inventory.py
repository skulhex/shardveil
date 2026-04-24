from __future__ import annotations

from dataclasses import dataclass

import arcade
from arcade import gui
from arcade.gui import events
from arcade.gui.widgets import EVENT_HANDLED, EVENT_UNHANDLED

from sv.items import EQUIPMENT_SLOT_ORDER, EquipmentSlot, Inventory, ItemStack, STORAGE_COLUMNS, STORAGE_ROWS, load_item_textures


GRID_COLUMNS = 1 + STORAGE_COLUMNS
GRID_ROWS = STORAGE_ROWS
CELL_SIZE = 60
CELL_GAP = 8
PANEL_PADDING = 18
HEADER_HEIGHT = 36
FOOTER_HEIGHT = 20
EQUIPMENT_LABELS = {
    EquipmentSlot.WEAPON: "Оружие",
    EquipmentSlot.ARMOR: "Броня",
    EquipmentSlot.ACCESSORY: "Аксессуар",
    EquipmentSlot.EXTRA: "Слот",
}


def _grid_width() -> float:
    return GRID_COLUMNS * CELL_SIZE + (GRID_COLUMNS - 1) * CELL_GAP


def _grid_height() -> float:
    return GRID_ROWS * CELL_SIZE + (GRID_ROWS - 1) * CELL_GAP


def panel_size() -> tuple[float, float]:
    width = PANEL_PADDING * 2 + _grid_width()
    height = PANEL_PADDING * 2 + HEADER_HEIGHT + FOOTER_HEIGHT + _grid_height()
    return width, height


@dataclass(slots=True)
class InventorySelection:
    column: int = 0
    row: int = 0

    def clamp(self) -> None:
        self.column = max(0, min(GRID_COLUMNS - 1, self.column))
        self.row = max(0, min(GRID_ROWS - 1, self.row))


class InventoryPanel(gui.UIWidget):
    def __init__(self, inventory: Inventory):
        width, height = panel_size()
        super().__init__(width=width, height=height)
        self.inventory = inventory
        self.selection = InventorySelection()
        self._textures = load_item_textures()
        self.with_background(color=(18, 20, 28, 240))
        self.with_border(color=(94, 102, 118, 255), width=2)

    def handle_key_press(self, symbol: int) -> bool:
        if symbol == arcade.key.LEFT:
            self.selection.column = (self.selection.column - 1) % GRID_COLUMNS
            self.trigger_render()
            return True
        if symbol == arcade.key.RIGHT:
            self.selection.column = (self.selection.column + 1) % GRID_COLUMNS
            self.trigger_render()
            return True
        if symbol == arcade.key.UP:
            self.selection.row = (self.selection.row - 1) % GRID_ROWS
            self.trigger_render()
            return True
        if symbol == arcade.key.DOWN:
            self.selection.row = (self.selection.row + 1) % GRID_ROWS
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
        return False

    def on_event(self, event: events.UIEvent) -> bool | None:
        if isinstance(event, events.UIMousePressEvent):
            if event.button != arcade.MOUSE_BUTTON_LEFT:
                return EVENT_UNHANDLED
            cell = self._cell_at_point(event.x, event.y)
            if cell is None:
                return EVENT_UNHANDLED
            column, row = cell
            self.selection.column = column
            self.selection.row = row
            self.trigger_render()
            return EVENT_HANDLED
        return super().on_event(event)

    def do_render(self, surface: gui.Surface) -> None:
        self.prepare_render(surface)

        self._draw_text(
            "Инвентарь",
            PANEL_PADDING,
            self.height - PANEL_PADDING,
            color=(235, 238, 245, 255),
            font_size=16,
            bold=True,
            anchor_y="top",
        )
        self._draw_text(
            "I или Esc - закрыть",
            PANEL_PADDING,
            PANEL_PADDING // 2,
            color=(164, 170, 184, 255),
            font_size=11,
            anchor_y="bottom",
        )

        for row in range(GRID_ROWS):
            self._draw_equipment_cell(row)
            for column in range(1, GRID_COLUMNS):
                self._draw_storage_cell(column, row)

    def _draw_equipment_cell(self, row: int) -> None:
        slot = EQUIPMENT_SLOT_ORDER[row]
        rect = self._cell_rect(0, row)
        self._draw_cell_background(rect, selected=self.selection.column == 0 and self.selection.row == row, equipment=True)
        stack = self.inventory.get_equipment(slot)
        if stack is not None:
            self._draw_stack(stack, rect)
        else:
            label = EQUIPMENT_LABELS[slot]
            self._draw_slot_label(label, rect)

    def _draw_storage_cell(self, column: int, row: int) -> None:
        rect = self._cell_rect(column, row)
        self._draw_cell_background(rect, selected=self.selection.column == column and self.selection.row == row, equipment=False)
        stack = self.inventory.storage_cell(row, column - 1)
        if stack is not None:
            self._draw_stack(stack, rect)

    def _draw_cell_background(self, rect: arcade.types.Rect, *, selected: bool, equipment: bool) -> None:
        base_color = (37, 42, 55, 245) if equipment else (28, 31, 40, 245)
        border_color = (106, 115, 131, 255) if equipment else (74, 81, 95, 255)
        arcade.draw_rect_filled(rect, color=base_color)
        arcade.draw_rect_outline(rect, color=border_color, border_width=2)
        if selected:
            arcade.draw_rect_outline(rect, color=(219, 186, 78, 255), border_width=4)

    def _draw_stack(self, stack: ItemStack, rect: arcade.types.Rect) -> None:
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
        if symbol == arcade.key.I:
            self.on_close()
            return True
        if self.panel is None:
            return False
        return self.panel.handle_key_press(symbol)
