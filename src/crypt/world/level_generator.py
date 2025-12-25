class LevelGenerator:
    def __init__(self, width=10, height=10):
        self.width = width
        self.height = height

    def generate(self):
        """
        Очень простой генератор уровня:
        0 = wall
        1 = floor
        """
        import random

        level = []
        for y in range(self.height):
            row = []
            for x in range(self.width):
                # border walls
                if x == 0 or y == 0 or x == self.width - 1 or y == self.height - 1:
                    row.append(0)
                # random floor/wall mix
                else:
                    row.append(1 if random.random() > 0.2 else 0)
            level.append(row)

        return level
