from enum import Enum
import random
from typing import Any, Dict

from .entity import Entity

class EnemyType(Enum):
    ZOMBIE = "z"
    VAMPIRE = "v"
    GHOST = "g"
    OGRE = "O"
    SNAKE_MAGE = "s"
    MIMIC = "m"

class Enemy(Entity):
    BASE_STATS = {
        EnemyType.ZOMBIE:     {"hp": 25, "dex": 6,  "power": 10, "hostility": 4},
        EnemyType.VAMPIRE:    {"hp": 20, "dex": 12, "power": 6,  "hostility": 5},
        EnemyType.GHOST:      {"hp": 12, "dex": 16, "power": 4,  "hostility": 3},
        EnemyType.OGRE:       {"hp": 50, "dex": 4,  "power": 18, "hostility": 5},
        EnemyType.SNAKE_MAGE: {"hp": 18, "dex": 20, "power": 6,  "hostility": 7},
        EnemyType.MIMIC:      {"hp": 35, "dex": 18, "power": 3,  "hostility": 1},
    }

    @classmethod
    def create(cls, enemy_type: EnemyType, level_idx: int):
        base = cls.BASE_STATS[enemy_type]
        mult = 1 + (level_idx - 1) * 0.2
        return cls(
            health=int(base["hp"] * mult),
            max_health=int(base["hp"] * mult),
            dexterity=int(base["dex"] * mult),
            power=int(base["power"] * mult),
            type=enemy_type,
            hostility=max(1, int(base["hostility"] * mult)),
        )

    def __init__(
        self,
        health,
        max_health,
        dexterity,
        power,
        type,
        hostility,
        x=0,
        y=0,
        awake=False,
        resting=False,
    ):
        super().__init__(health, max_health, dexterity, power)
        self.type = type
        self.hostility = hostility
        self.x, self.y = x, y
        self.awake = awake
        self.resting = resting
        self.visible = type != EnemyType.GHOST
        self._first_strike_ignored = type == EnemyType.VAMPIRE
        self._last_direction: tuple = None

        if type == EnemyType.MIMIC:
            self.disguise_as = random.choice(["food", "weapon", "elixir", "scroll"])
            self.awake = False
            self.visible = False
        else:
            self.disguise_as = None

    def is_hit(self, attacker_dex: int) -> bool:
        chance = self.dexterity / (self.dexterity + attacker_dex)
        return random.random() < min(chance, 0.9)

    def damage_calculation(self) -> int:
        return max(1, int(self.power * random.uniform(0.8, 1.2)))

    def take_damage(self, damage: int):
        if self.type == EnemyType.VAMPIRE and self._first_strike_ignored:
            self._first_strike_ignored = False
            return 
        super().take_damage(damage)

    def attack(self, player) -> int:
        if not self.awake or self.resting:
            return 0

        if self.type == EnemyType.VAMPIRE and self.is_hit(player.dexterity):
            drain = random.randint(4, 8)
            player.take_damage(drain)
            self.health = min(self.max_health, self.health + drain // 2)

        if self.type == EnemyType.SNAKE_MAGE and random.random() < 0.35:
            player.asleep = True

        if not self.is_hit(player.dexterity):
            return 0

        dmg = self.damage_calculation()
        player.take_damage(dmg)
        if self.type == EnemyType.OGRE:
            self.resting = True
        return dmg

    def drop_treasures(self) -> int:
        total = self.hostility + self.power + self.dexterity + self.max_health // 10
        return random.randint(total // 2, total * 2 // 3)

    def distance_to(self, x, y):
        return ((self.x - x) ** 2 + (self.y - y) ** 2) ** 0.5

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "type": self.type.value,
            "health": self.health,
            "max_health": self.max_health,
            "dexterity": self.dexterity,
            "power": self.power,
            "hostility": self.hostility,
            "x": self.x,
            "y": self.y,
            "awake": self.awake,
            "resting": self.resting,
            "visible": self.visible,
            "first_strike_ignored": getattr(self, "_first_strike_ignored", False),
            "last_direction": getattr(self, "_last_direction", None),
        }
        if self.type == EnemyType.MIMIC:
            data["disguise_as"] = self.disguise_as
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Enemy":
        enemy = cls(
            health=data["health"],
            max_health=data["max_health"],
            dexterity=data["dexterity"],
            power=data["power"],
            type=EnemyType(data["type"]),
            hostility=data["hostility"],
            x=data["x"],
            y=data["y"],
            awake=data.get("awake", False),
            resting=data.get("resting", False),
        )
        enemy.visible = data.get("visible", True)
        enemy._first_strike_ignored = data.get("first_strike_ignored", False)
        enemy._last_direction = tuple(data.get("last_direction")) if data.get("last_direction") else None
        if enemy.type == EnemyType.MIMIC:
            enemy.disguise_as = data.get("disguise_as")
            if not enemy.awake:
                enemy.visible = False
        else:
            enemy.disguise_as = None
        return enemy
