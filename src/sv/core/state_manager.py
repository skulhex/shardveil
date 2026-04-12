from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class AppView(Enum):
    MAIN_MENU = auto()
    IN_GAME = auto()


class GamePhase(Enum):
    PLAYER_TURN = auto()
    PLAYER_ANIM = auto()
    ENEMY_TURN = auto()
    PAUSED = auto()


@dataclass
class StateManager:
    view: AppView = AppView.MAIN_MENU
    phase: GamePhase | None = None
    _phase_before_pause: GamePhase | None = None

    def is_in_game(self) -> bool:
        return self.view is AppView.IN_GAME

    def is_main_menu(self) -> bool:
        return self.view is AppView.MAIN_MENU

    def is_player_turn(self) -> bool:
        return self.phase is GamePhase.PLAYER_TURN

    def is_player_anim(self) -> bool:
        return self.phase is GamePhase.PLAYER_ANIM

    def is_enemy_turn(self) -> bool:
        return self.phase is GamePhase.ENEMY_TURN

    def is_paused(self) -> bool:
        return self.phase is GamePhase.PAUSED

    def enter_main_menu(self) -> None:
        self.view = AppView.MAIN_MENU
        self.phase = None
        self._phase_before_pause = None

    def enter_game(self, initial_phase: GamePhase = GamePhase.PLAYER_TURN) -> None:
        self.view = AppView.IN_GAME
        self.phase = initial_phase
        self._phase_before_pause = None

    def set_phase(self, phase: GamePhase) -> None:
        if not self.is_in_game():
            return
        if phase is GamePhase.PAUSED:
            self._phase_before_pause = self.phase
        elif phase is not self.phase:
            self._phase_before_pause = None
        self.phase = phase

    def toggle_pause(self) -> bool:
        if not self.is_in_game():
            return False
        if self.is_paused():
            return self.resume()
        return self.pause()

    def pause(self) -> bool:
        if not self.is_in_game() or self.phase is None or self.is_paused():
            return False
        self._phase_before_pause = self.phase
        self.phase = GamePhase.PAUSED
        return True

    def resume(self) -> bool:
        if not self.is_paused() or self._phase_before_pause is None:
            return False
        self.phase = self._phase_before_pause
        self._phase_before_pause = None
        return True
