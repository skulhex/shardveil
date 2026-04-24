from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from functools import lru_cache
from pathlib import Path

import arcade


class ItemKind(Enum):
    WEAPON = auto()
    ARMOR = auto()
    ACCESSORY = auto()
    CONSUMABLE = auto()
    MISC = auto()


class EquipmentSlot(Enum):
    WEAPON = auto()
    ARMOR = auto()
    ACCESSORY = auto()
    EXTRA = auto()


@dataclass(frozen=True, slots=True)
class ItemDefinition:
    item_id: str
    name: str
    kind: ItemKind
    icon_index: int
    max_stack: int = 1
    equip_slot: EquipmentSlot | None = None

    @property
    def stackable(self) -> bool:
        return self.max_stack > 1

    @property
    def equippable(self) -> bool:
        return self.equip_slot is not None


@dataclass(slots=True)
class ItemStack:
    definition: ItemDefinition
    quantity: int = 1

    def __post_init__(self) -> None:
        self.quantity = max(1, int(self.quantity))
        self.quantity = min(self.quantity, self.definition.max_stack)

    @property
    def name(self) -> str:
        return self.definition.name


_ITEM_TEXTURE_SIZE = 16
_ITEM_SPRITESHEET_PATH = ":assets:/sprites/items.png"


@lru_cache(maxsize=1)
def load_item_textures() -> tuple[arcade.Texture, ...]:
    try:
        sheet = arcade.load_spritesheet(_ITEM_SPRITESHEET_PATH)
    except FileNotFoundError:
        fallback_path = Path(__file__).resolve().parents[3] / "assets" / "sprites" / "items.png"
        sheet = arcade.load_spritesheet(fallback_path)
    textures = sheet.get_texture_grid((_ITEM_TEXTURE_SIZE, _ITEM_TEXTURE_SIZE), columns=4, count=4)
    return tuple(textures)


DEFAULT_ITEM_DEFINITIONS: dict[str, ItemDefinition] = {
    "sword": ItemDefinition(
        item_id="sword",
        name="Меч",
        kind=ItemKind.WEAPON,
        icon_index=0,
        equip_slot=EquipmentSlot.WEAPON,
    ),
    "armor": ItemDefinition(
        item_id="armor",
        name="Кольчуга",
        kind=ItemKind.ARMOR,
        icon_index=1,
        equip_slot=EquipmentSlot.ARMOR,
    ),
    "ring": ItemDefinition(
        item_id="ring",
        name="Кольцо",
        kind=ItemKind.ACCESSORY,
        icon_index=2,
        equip_slot=EquipmentSlot.ACCESSORY,
    ),
    "potion": ItemDefinition(
        item_id="potion",
        name="Зелье",
        kind=ItemKind.CONSUMABLE,
        icon_index=3,
        max_stack=5,
    ),
}
