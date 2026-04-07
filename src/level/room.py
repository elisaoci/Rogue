import random
from typing import Any, Dict, List, Optional, Tuple

from src.entities import Enemy
from src.entities.entity import Item, item_from_dict

class Room:
    def __init__(self, x: int, y: int, width: int, height: int):
        self.x, self.y = x, y
        self.width, self.height = width, height
        self.doors: List[Tuple[int, int]] = []
        self.enemies: List[Enemy] = []
        self.items: Dict[Tuple[int, int], List[Item]] = {}
        self.stairs: Optional[Tuple[int, int]] = None
        self.is_start: bool = False

    def is_passable(self, x: int, y: int) -> bool:
        rx, ry = x - self.x, y - self.y
        return 0 < rx < self.width - 1 and 0 < ry < self.height - 1

    def get_items_at(self, x: int, y: int) -> List[Item]:
        return self.items.get((x, y), [])

    def remove_item(self, item: Item):
        for pos, items in list(self.items.items()):
            if item in items:
                items.remove(item)
                if not items:
                    del self.items[pos]
                break

    def add_enemy(self, enemy: Enemy):
        self.enemies.append(enemy)

    def get_enemy_at(self, x: int, y: int) -> Optional[Enemy]:
        for e in self.enemies:
            if e.x == x and e.y == y:
                return e
        return None

    def contains(self, x: int, y: int) -> bool:
        return (
            self.x <= x < self.x + self.width and
            self.y <= y < self.y + self.height
        )

    @property
    def center(self) -> Tuple[int, int]:
        return (
            self.x + self.width // 2,
            self.y + self.height // 2,
        )

    def random_interior_position(self) -> Tuple[int, int]:
        rx = random.randint(1, self.width - 2)
        ry = random.randint(1, self.height - 2)
        return self.x + rx, self.y + ry

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "doors": self.doors,
            "stairs": self.stairs,
            "is_start": self.is_start,
            "items": {
                f"{pos[0]}:{pos[1]}": [item.to_dict() for item in items]
                for pos, items in self.items.items()
            },
            "enemies": [enemy.to_dict() for enemy in self.enemies],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Room":
        room = cls(data["x"], data["y"], data["width"], data["height"])
        room.doors = [tuple(door) for door in data.get("doors", [])]
        room.stairs = tuple(data["stairs"]) if data.get("stairs") else None
        room.is_start = data.get("is_start", False)

        for pos_key, items in data.get("items", {}).items():
            x, y = map(int, pos_key.split(":"))
            room.items[(x, y)] = [item_from_dict(raw) for raw in items]

        for enemy_data in data.get("enemies", []):
            room.enemies.append(Enemy.from_dict(enemy_data))

        return room