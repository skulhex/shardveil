from __future__ import annotations

from dataclasses import dataclass, field

from .item import DEFAULT_ITEM_DEFINITIONS, EquipmentSlot, ItemStack


EQUIPMENT_SLOT_ORDER: tuple[EquipmentSlot, ...] = (
    EquipmentSlot.WEAPON,
    EquipmentSlot.ARMOR,
    EquipmentSlot.ACCESSORY,
    EquipmentSlot.EXTRA,
)

STORAGE_COLUMNS = 4
STORAGE_ROWS = 4
STORAGE_SIZE = STORAGE_COLUMNS * STORAGE_ROWS
INVENTORY_COLUMNS = 1 + STORAGE_COLUMNS
INVENTORY_ROWS = STORAGE_ROWS


@dataclass(frozen=True, slots=True)
class InventoryMoveResult:
    moved: bool
    reason: str | None = None


def _empty_storage() -> list[ItemStack | None]:
    return [None for _ in range(STORAGE_SIZE)]


def _empty_equipment() -> dict[EquipmentSlot, ItemStack | None]:
    return {slot: None for slot in EQUIPMENT_SLOT_ORDER}


@dataclass(slots=True)
class Inventory:
    equipment: dict[EquipmentSlot, ItemStack | None] = field(default_factory=_empty_equipment)
    storage: list[ItemStack | None] = field(default_factory=_empty_storage)

    def equipment_index(self, slot: EquipmentSlot) -> int:
        return EQUIPMENT_SLOT_ORDER.index(slot)

    def storage_index(self, row: int, column: int) -> int:
        return row * STORAGE_COLUMNS + column

    def storage_cell(self, row: int, column: int) -> ItemStack | None:
        return self.storage[self.storage_index(row, column)]

    def set_storage_cell(self, row: int, column: int, stack: ItemStack | None) -> None:
        self.storage[self.storage_index(row, column)] = stack

    def set_equipment(self, slot: EquipmentSlot, stack: ItemStack | None) -> None:
        self.equipment[slot] = stack

    def get_equipment(self, slot: EquipmentSlot) -> ItemStack | None:
        return self.equipment.get(slot)

    def get_cell(self, column: int, row: int) -> ItemStack | None:
        if column == 0:
            return self.get_equipment(EQUIPMENT_SLOT_ORDER[row])
        return self.storage_cell(row, column - 1)

    def set_cell(self, column: int, row: int, stack: ItemStack | None) -> None:
        if column == 0:
            self.set_equipment(EQUIPMENT_SLOT_ORDER[row], stack)
        else:
            self.set_storage_cell(row, column - 1, stack)

    def cell_label(self, column: int, row: int) -> str:
        if column == 0:
            return EQUIPMENT_SLOT_ORDER[row].label
        return f"Хранилище {row + 1}:{column}"

    def can_place(self, column: int, row: int, stack: ItemStack | None) -> tuple[bool, str | None]:
        if stack is None:
            return False, "Нечего перемещать."

        if column == 0:
            slot = EQUIPMENT_SLOT_ORDER[row]
            if stack.definition.equip_slot != slot:
                return False, f"{stack.name} нельзя надеть в слот {slot.label.lower()}."
        return True, None

    def transfer_between_cells(
        self,
        source_column: int,
        source_row: int,
        target_column: int,
        target_row: int,
    ) -> InventoryMoveResult:
        if source_column == target_column and source_row == target_row:
            return InventoryMoveResult(False, "Выберите другую ячейку.")

        source_stack = self.get_cell(source_column, source_row)
        if source_stack is None:
            return InventoryMoveResult(False, "В выбранной ячейке нет предмета.")

        target_stack = self.get_cell(target_column, target_row)

        can_place_target, reason_target = self.can_place(target_column, target_row, source_stack)
        if not can_place_target:
            return InventoryMoveResult(False, reason_target)

        if target_stack is None:
            self.set_cell(target_column, target_row, source_stack)
            self.set_cell(source_column, source_row, None)
            return InventoryMoveResult(True)

        can_place_source, reason_source = self.can_place(source_column, source_row, target_stack)
        if not can_place_source:
            return InventoryMoveResult(False, reason_source)

        self.set_cell(source_column, source_row, target_stack)
        self.set_cell(target_column, target_row, source_stack)
        return InventoryMoveResult(True)


def create_default_inventory() -> Inventory:
    inventory = Inventory()
    inventory.set_equipment(EquipmentSlot.WEAPON, ItemStack(DEFAULT_ITEM_DEFINITIONS["sword"]))
    inventory.set_equipment(EquipmentSlot.ARMOR, ItemStack(DEFAULT_ITEM_DEFINITIONS["armor"]))
    inventory.set_equipment(EquipmentSlot.ACCESSORY, ItemStack(DEFAULT_ITEM_DEFINITIONS["ring"]))
    inventory.set_storage_cell(0, 0, ItemStack(DEFAULT_ITEM_DEFINITIONS["potion"]))
    return inventory
