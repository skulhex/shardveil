from __future__ import annotations
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Deque, Dict, List, Optional


class EventType(Enum):
    INFO = auto()
    COMBAT = auto()
    SYSTEM = auto()

    # задел под будущее (не обязательно использовать сразу)
    DAMAGE = auto()
    HEAL = auto()
    DEATH = auto()
    ITEM_PICKED = auto()
    FLOOR_CHANGED = auto()


@dataclass(slots=True)
class GameEvent:
    type: EventType
    text: str
    payload: Dict[str, Any] = field(default_factory=dict)
    # можно добавить timestamp при необходимости


class EventQueue:
    """Простая очередь событий (без подписчиков)."""

    def __init__(self, maxlen: Optional[int] = None):
        self._q: Deque[GameEvent] = deque(maxlen=maxlen)

    # ===== API из ТЗ =====
    def emit(self, event: GameEvent) -> None:
        self._q.append(event)

    def drain(self) -> List[GameEvent]:
        items = list(self._q)
        self._q.clear()
        return items

    def clear(self) -> None:
        self._q.clear()

    def has_events(self) -> bool:
        return len(self._q) > 0


class EventBus:
    """
    Обёртка над очередью + (опционально) подписчики.
    Можно использовать просто как очередь, а можно подписывать системы.
    """

    def __init__(self, maxlen: Optional[int] = None):
        self._queue = EventQueue(maxlen=maxlen)
        self._subs: Dict[EventType, List] = {}

    # ===== API из ТЗ =====
    def emit(self, event: GameEvent) -> None:
        # кладём в очередь
        self._queue.emit(event)
        # уведомляем подписчиков (если есть)
        for cb in self._subs.get(event.type, []):
            cb(event)

    def drain(self) -> List[GameEvent]:
        return self._queue.drain()

    def clear(self) -> None:
        self._queue.clear()

    def has_events(self) -> bool:
        return self._queue.has_events()

    # ===== Дополнительно (необязательно, но полезно) =====
    def subscribe(self, event_type: EventType, callback) -> None:
        self._subs.setdefault(event_type, []).append(callback)

    def unsubscribe(self, event_type: EventType, callback) -> None:
        if event_type in self._subs:
            self._subs[event_type] = [
                cb for cb in self._subs[event_type] if cb != callback
            ]
