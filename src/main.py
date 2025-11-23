from crypt.core import Settings, GameState
from crypt.world import LevelGenerator

def main():
    settings = Settings()
    state = GameState(settings)
    print("Game initialized.")

if __name__ == "__main__":
    main()
