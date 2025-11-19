from crypt.core.config import Settings
from crypt.core.game_state import GameState

def main():
    settings = Settings()
    state = GameState(settings)
    print("Game initialized.")

if __name__ == "__main__":
    main()
