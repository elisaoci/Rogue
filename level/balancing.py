import time
from typing import Dict, Any


class DynamicBalancingSystem:
    def __init__(self):
        self.health_lost_recent = 0
        self.level_start_time = time.time()
        self.difficulty = 5  # 1–10

    def record_damage(self, damage: int):
        self.health_lost_recent += damage

    def on_level_complete(self):
        level_time = time.time() - self.level_start_time

        if self.health_lost_recent > 55 or level_time > 320:
            self.difficulty = max(1, self.difficulty - 1)
        elif self.health_lost_recent < 18 and level_time < 90:
            self.difficulty = min(10, self.difficulty + 1)

        adjustments = self.get_adjustments()

        self.health_lost_recent = 0
        self.level_start_time = time.time()

        return adjustments

    def get_adjustments(self) -> Dict[str, float]:
        d = self.difficulty
        if d <= 3:
            return {"enemy": 0.6, "hp": 0.7, "dmg": 0.7, "items": 1.7}
        elif d <= 7:
            return {"enemy": 1.0, "hp": 1.0, "dmg": 1.0, "items": 1.0}
        else:
            return {"enemy": 1.5, "hp": 1.3, "dmg": 1.4, "items": 0.6}
