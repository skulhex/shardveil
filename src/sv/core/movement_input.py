from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field


Direction = tuple[int, int]


@dataclass
class MovementInputState:
    horizontal_bindings: Mapping[int, int]
    vertical_bindings: Mapping[int, int]
    diagonal_window: float = 0.12
    _pressed_keys: set[int] = field(default_factory=set, init=False)
    _press_times: dict[int, float] = field(default_factory=dict, init=False)
    _press_order: dict[int, int] = field(default_factory=dict, init=False)
    _order_counter: int = field(default=0, init=False)
    _initial_move: Direction | None = field(default=None, init=False)
    _held_move: Direction | None = field(default=None, init=False)
    _ready_at: float = field(default=0.0, init=False)
    _initial_move_consumed: bool = field(default=True, init=False)
    _blocked_move: Direction | None = field(default=None, init=False)
    _directional_keys: set[int] = field(default_factory=set, init=False)

    def __post_init__(self) -> None:
        self._directional_keys = set(self.horizontal_bindings) | set(self.vertical_bindings)

    def press(self, symbol: int, now: float) -> None:
        if symbol not in self._directional_keys:
            return
        if symbol in self._pressed_keys:
            return
        previous_move = self._held_move if self._held_move is not None else self._initial_move
        self._pressed_keys.add(symbol)
        self._press_times[symbol] = now
        self._order_counter += 1
        self._press_order[symbol] = self._order_counter
        self.clear_blocked_on_input_change()
        self._refresh_resolution(now, event_kind="press", previous_move=previous_move)

    def release(self, symbol: int, now: float) -> None:
        if symbol not in self._directional_keys:
            return
        if symbol not in self._pressed_keys:
            return
        self._pressed_keys.remove(symbol)
        self.clear_blocked_on_input_change()
        self._refresh_resolution(now, event_kind="release", previous_move=None)

    def resolve_move(self, now: float) -> Direction | None:
        move = self._held_move if self._initial_move_consumed else self._initial_move
        if move is None:
            return None
        if self._blocked_move == move:
            return None
        if not self._initial_move_consumed and now < self._ready_at:
            return None
        if not self._initial_move_consumed:
            self._initial_move_consumed = True
        return move

    def mark_blocked(self, dx: int, dy: int) -> None:
        self._blocked_move = (int(dx), int(dy))

    def clear_blocked_on_input_change(self) -> None:
        self._blocked_move = None

    def clear(self) -> None:
        self._pressed_keys.clear()
        self._press_times.clear()
        self._press_order.clear()
        self._order_counter = 0
        self._initial_move = None
        self._held_move = None
        self._ready_at = 0.0
        self._initial_move_consumed = True
        self._blocked_move = None

    def _refresh_resolution(
        self,
        now: float,
        event_kind: str,
        previous_move: Direction | None,
    ) -> None:
        dx, h_time = self._resolve_axis(self.horizontal_bindings)
        dy, v_time = self._resolve_axis(self.vertical_bindings)

        if dx == 0 and dy == 0:
            self._initial_move = None
            self._held_move = None
            self._ready_at = now
            self._initial_move_consumed = True
            return

        if dx != 0 and dy != 0:
            diagonal = (dx, dy)
            if event_kind == "press" and self._is_cardinal_component(previous_move, diagonal):
                self._set_resolution(diagonal, diagonal, now)
                return
            if abs(h_time - v_time) <= self.diagonal_window:
                self._set_resolution(diagonal, diagonal, now)
                return
            if h_time > v_time:
                self._set_resolution((dx, 0), diagonal, now)
                return
            self._set_resolution((0, dy), diagonal, now)
            return

        single_axis_move = (dx, dy)
        ready_at = now + self.diagonal_window if event_kind == "press" else now
        self._set_resolution(single_axis_move, single_axis_move, ready_at)

    def _set_resolution(
        self,
        initial_move: Direction | None,
        held_move: Direction | None,
        ready_at: float,
    ) -> None:
        self._initial_move = initial_move
        self._held_move = held_move
        self._ready_at = ready_at
        self._initial_move_consumed = initial_move is None

    def _resolve_axis(self, bindings: Mapping[int, int]) -> tuple[int, float]:
        selected_key = None
        selected_order = -1
        for key in bindings:
            if key not in self._pressed_keys:
                continue
            order = self._press_order.get(key, -1)
            if order > selected_order:
                selected_key = key
                selected_order = order

        if selected_key is None:
            return 0, 0.0
        return bindings[selected_key], self._press_times.get(selected_key, 0.0)

    @staticmethod
    def _is_cardinal_component(
        previous_move: Direction | None,
        diagonal: Direction,
    ) -> bool:
        if previous_move is None:
            return False
        pdx, pdy = previous_move
        dx, dy = diagonal
        return (pdx == dx and pdy == 0) or (pdx == 0 and pdy == dy)
