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


def create_default_inventory() -> Inventory:
    inventory = Inventory()
    inventory.set_equipment(EquipmentSlot.WEAPON, ItemStack(DEFAULT_ITEM_DEFINITIONS["sword"]))
    inventory.set_equipment(EquipmentSlot.ARMOR, ItemStack(DEFAULT_ITEM_DEFINITIONS["armor"]))
    inventory.set_equipment(EquipmentSlot.ACCESSORY, ItemStack(DEFAULT_ITEM_DEFINITIONS["ring"]))
    inventory.set_storage_cell(0, 0, ItemStack(DEFAULT_ITEM_DEFINITIONS["potion"]))
    return inventory
