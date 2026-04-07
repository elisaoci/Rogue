from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Type, Set

if TYPE_CHECKING:
    from src.level.level import Level


@dataclass
class Entity:
    health: int
    max_health: int
    dexterity: int
    power: int

    def is_alive(self) -> bool:
        return self.health > 0

    def take_damage(self, damage: int):
        self.health = max(0, self.health - damage)

    def heal(self, amount: int):
        self.health = min(self.max_health, self.health + amount)

    def to_dict(self) -> Dict[str, int]:
        return {
            "health": self.health,
            "max_health": self.max_health,
            "dexterity": self.dexterity,
            "power": self.power,
        }


class Backpack:
    CAPACITY_PER_TYPE = 9

    def __init__(self):
        self.items: Dict[str, List["Item"]] = {
            "food": [],
            "scroll": [],
            "elixir": [],
            "weapon": [],
        }
        self.treasure_value: int = 0
        self.keys: Set[str] = set()

    def add(self, item: "Item") -> bool:
        if item.item_type == "treasure":
            self.treasure_value += getattr(item, "value", 0)
            return True

        storage = self.items.setdefault(item.item_type, [])
        if len(storage) >= self.CAPACITY_PER_TYPE:
            return False

        storage.append(item)
        return True

    def remove_item(self, item_type: str, index: int) -> Optional["Item"]:
        storage = self.items.get(item_type, [])
        if 0 <= index < len(storage):
            return storage.pop(index)
        return None

    def list_items(self, item_type: str) -> List["Item"]:
        return list(self.items.get(item_type, []))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "treasure": self.treasure_value,
            "items": {
                key: [item.to_dict() for item in values]
                for key, values in self.items.items()
            },
            "keys": list(self.keys),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Backpack":
        pack = cls()
        pack.treasure_value = data.get("treasure", 0)
        for key, items in data.get("items", {}).items():
            pack.items[key] = [item_from_dict(raw) for raw in items]
        for k in data.get("keys", []):
            pack.keys.add(k)
        return pack


class Player(Entity):
    def __init__(
        self,
        health: int = 100,
        max_health: int = 100,
        dexterity: int = 10,
        power: int = 10,
    ):
        super().__init__(health, max_health, dexterity, power)
        self.current_weapon: Optional["Weapon"] = None
        self.backpack = Backpack()
        self.active_effects: List[Dict[str, int]] = []
        self.x: int = 0
        self.y: int = 0
        self.current_level: int = 1
        self.asleep: bool = False

    @property
    def treasure_value(self) -> int:
        return self.backpack.treasure_value

    @treasure_value.setter
    def treasure_value(self, value: int):
        self.backpack.treasure_value = value

    def set_position(self, x: int, y: int):
        self.x, self.y = x, y

    def move(self, action: str, level: "Level") -> bool:
        dirs = {"w": (0, -1), "s": (0, 1), "a": (-1, 0), "d": (1, 0)}
        dx, dy = dirs.get(action, (0, 0))
        nx, ny = self.x + dx, self.y + dy

        if not level.is_passable(nx, ny, self):
            return False

        self.x, self.y = nx, ny
        return True

    def is_hit(self, opponent_dex: int) -> bool:
        chance = self.dexterity / (self.dexterity + opponent_dex)
        return random.random() < min(chance, 0.9)

    def damage_calculation(self) -> int:
        base = self.power
        if self.current_weapon:
            base += self.current_weapon.power
        return max(1, int(base * random.uniform(0.8, 1.2)))

    def attack(self, opponent) -> int:
        if self.is_hit(opponent.dexterity):
            dmg = self.damage_calculation()
            opponent.take_damage(dmg)
            return dmg
        return 0

    def equip_weapon(self, weapon: "Weapon", level: Optional["Level"] = None):
        if self.current_weapon:
            if not self.backpack.add(self.current_weapon):
                if level:
                    level.drop_item_near((self.x, self.y), self.current_weapon)
        self.current_weapon = weapon

    def unequip_weapon(self, level: Optional["Level"] = None) -> bool:
        if not self.current_weapon:
            return False
        weapon = self.current_weapon
        if not self.backpack.add(weapon):
            if not level:
                return False
            level.drop_item_near((self.x, self.y), weapon)
        self.current_weapon = None
        return True

    def use_item(self, item: "Item", level: Optional["Level"] = None) -> bool:
        if isinstance(item, Weapon):
            self.equip_weapon(item, level)
            return True
        return item.apply_effect(self)

    def apply_temporary_effects(self, stat: str, boost: int, turns: int):
        self.active_effects.append({"stat": stat, "boost": boost, "turns": turns})
        if stat == "power":
            self.power += boost
        elif stat == "dexterity":
            self.dexterity += boost
        elif stat == "max_health":
            self.max_health += boost
            self.health += boost

    def update_effects(self):
        to_remove = []
        for effect in self.active_effects:
            effect["turns"] -= 1
            if effect["turns"] <= 0:
                to_remove.append(effect)

        for effect in to_remove:
            if effect["stat"] == "power":
                self.power -= effect["boost"]
            elif effect["stat"] == "dexterity":
                self.dexterity -= effect["boost"]
            elif effect["stat"] == "max_health":
                self.max_health -= effect["boost"]
                self.health = min(self.health, self.max_health)
            self.active_effects.remove(effect)

        self.health = min(self.health, self.max_health)
        if self.health <= 0:
            self.health = 1

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update(
            {
                "x": self.x,
                "y": self.y,
                "current_level": self.current_level,
                "asleep": self.asleep,
                "backpack": self.backpack.to_dict(),
                "active_effects": self.active_effects,
                "current_weapon": self.current_weapon.to_dict()
                if self.current_weapon
                else None,
            }
        )
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Player":
        player = cls(
            health=data["health"],
            max_health=data["max_health"],
            dexterity=data["dexterity"],
            power=data["power"],
        )
        player.x = data["x"]
        player.y = data["y"]
        player.current_level = data.get("current_level", 1)
        player.asleep = data.get("asleep", False)
        player.backpack = Backpack.from_dict(data.get("backpack", {}))
        weapon_data = data.get("current_weapon")
        if weapon_data:
            player.current_weapon = item_from_dict(weapon_data)
        player.active_effects = data.get("active_effects", [])
        return player


class Item:
    def __init__(self, item_type: str, name: str):
        self.item_type = item_type
        self.name = name

    def apply_effect(self, player: Player) -> bool:
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.item_type, "name": self.name}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Item":
        return cls(data.get("type", "item"), data.get("name", "Unknown"))


class Weapon(Item):
    def __init__(self, name: str, power: int):
        super().__init__("weapon", name)
        self.power = power

    def apply_effect(self, player: Player) -> bool:
        player.equip_weapon(self)
        return True

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["power"] = self.power
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Weapon":
        return cls(name=data["name"], power=data["power"])


class Food(Item):
    def __init__(self, name: str, health: int):
        super().__init__("food", name)
        self.health = health

    def apply_effect(self, player: Player) -> bool:
        player.heal(self.health)
        return True

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["health"] = self.health
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Food":
        return cls(name=data["name"], health=data["health"])


class Elixir(Item):
    def __init__(
        self,
        name: str,
        power: int = 0,
        dexterity: int = 0,
        max_health: int = 0,
        duration: int = 10,
    ):
        super().__init__("elixir", name)
        self.power = power
        self.dexterity = dexterity
        self.max_health = max_health
        self.duration = duration

    def apply_effect(self, player: Player) -> bool:
        if self.power:
            player.apply_temporary_effects("power", self.power, self.duration)
        if self.dexterity:
            player.apply_temporary_effects("dexterity", self.dexterity, self.duration)
        if self.max_health:
            player.apply_temporary_effects("max_health", self.max_health, self.duration)
        return True

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update(
            {
                "power": self.power,
                "dexterity": self.dexterity,
                "max_health": self.max_health,
                "duration": self.duration,
            }
        )
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Elixir":
        return cls(
            name=data["name"],
            power=data.get("power", 0),
            dexterity=data.get("dexterity", 0),
            max_health=data.get("max_health", 0),
            duration=data.get("duration", 10),
        )


class Scroll(Item):
    def __init__(self, name: str, power: int = 0, dexterity: int = 0, max_health: int = 0):
        super().__init__("scroll", name)
        self.power = power
        self.dexterity = dexterity
        self.max_health = max_health

    def apply_effect(self, player: Player) -> bool:
        if self.power:
            player.power += self.power
        if self.dexterity:
            player.dexterity += self.dexterity
        if self.max_health:
            player.max_health += self.max_health
            player.health += self.max_health
        return True

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update(
            {"power": self.power, "dexterity": self.dexterity, "max_health": self.max_health}
        )
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Scroll":
        return cls(
            name=data["name"],
            power=data.get("power", 0),
            dexterity=data.get("dexterity", 0),
            max_health=data.get("max_health", 0),
        )


class Treasure(Item):
    def __init__(self, name: str, value: int):
        super().__init__("treasure", name)
        self.value = value

    def apply_effect(self, player: Player) -> bool:
        player.treasure_value += self.value
        return True

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["value"] = self.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Treasure":
        return cls(name=data["name"], value=data["value"])


class Key(Item):
    def __init__(self, color: str):
        super().__init__("key", f"{color.capitalize()} key")
        self.color = color

    def apply_effect(self, player: Player) -> bool:
        player.backpack.keys.add(self.color)
        return True

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["color"] = self.color
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Key":
        return cls(color=data["color"])


ITEM_REGISTRY: Dict[str, Type[Item]] = {
    "weapon": Weapon,
    "food": Food,
    "elixir": Elixir,
    "scroll": Scroll,
    "treasure": Treasure,
    "key": Key,
}


def item_from_dict(data: Dict[str, Any]) -> Item:
    item_type = data["type"]
    cls: Type[Item] = ITEM_REGISTRY[item_type]
    return cls.from_dict(data)
