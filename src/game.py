from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
from typing import Deque, Dict, Optional
import time

from src.ai import EnemyAI
from src.entities import Enemy, EnemyType
from src.entities.entity import Player, Weapon
from src.level.generator import LevelGenerator
from src.level import Level, Tile
from src.level import DynamicBalancingSystem


@dataclass
class GameStats:
    steps: int = 0
    enemies_defeated: int = 0
    treasure_collected: int = 0
    food_consumed: int = 0
    elixirs_used: int = 0
    scrolls_used: int = 0
    weapons_swapped: int = 0
    hits_dealt: int = 0
    hits_taken: int = 0
    damage_dealt: int = 0
    damage_taken: int = 0
    levels_completed: int = 0

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "GameStats":
        return cls(**data)


class GameSession:
    TOTAL_LEVELS = 21

    def __init__(self, state: Optional[Dict] = None):
        self.message_log: Deque[str] = deque(maxlen=6)
        self.total_levels = self.TOTAL_LEVELS

        # Система балансировки
        self.balancing = DynamicBalancingSystem() if not state else None

        if state:
            self._load_state(state)
        else:
            self.player = Player()
            self.stats = GameStats()
            self.level_index = 1
            self.level = LevelGenerator.generate(self.level_index)
            self._place_player_in_start_room()

    def _place_player_in_start_room(self):
        spawn_x, spawn_y = self.level.start_room.random_interior_position()
        self.player.set_position(spawn_x, spawn_y)
        self.player.current_level = self.level_index

    def log(self, message: str):
        self.message_log.append(message)

    def perform_turn(self, action: str) -> str:
        if action not in {"w", "a", "s", "d"}:
            return "continue"

        if self.player.asleep:
            self.player.asleep = False
            self.log("Вы приходите в себя.")
            return "continue"

        target_dirs = {"w": (0, -1), "s": (0, 1), "a": (-1, 0), "d": (1, 0)}
        dx, dy = target_dirs.get(action, (0, 0))
        nx, ny = self.player.x + dx, self.player.y + dy

        tile = self.level.tiles.get((nx, ny))

        if tile == Tile.DOOR:
            if not self.level.try_open_door(self.player, nx, ny):
                self.log("Дверь заперта. Нужен ключ.")
                return "blocked"
            self.player.set_position(nx, ny)

        elif not self.level.is_passable(nx, ny, self.player):
            self.log("Стена преграждает путь.")
            return "blocked"

        else:
            self.player.set_position(nx, ny)

        self.stats.steps += 1

        collected = self.level.collect_items_for_player(self.player)
        if collected:
            names = ", ".join(item.name for item in collected)
            self.log(f"Вы подобрали: {names}.")

        enemy = self.level.get_enemy_at(self.player.x, self.player.y)
        if enemy:
            outcome = self._resolve_combat(enemy)
            if outcome != "continue":
                return outcome

        tile = self.level.tiles.get((self.player.x, self.player.y))
        if tile == Tile.STAIRS:
            if self.level_index >= self.total_levels:
                return "victory"
            self.level_index += 1
            self.stats.levels_completed += 1
            self.log("Вы спускаетесь глубже...")

            if self.balancing:
                adjustments = self.balancing.on_level_complete()
                self.level = LevelGenerator.generate(self.level_index, adjustments=adjustments)
            else:
                self.level = LevelGenerator.generate(self.level_index)
            self._place_player_in_start_room()
            return "level_complete"

        enemy_outcome = self._advance_enemies()
        if enemy_outcome:
            return enemy_outcome
        self.player.update_effects()

        if not self.player.is_alive():
            return "game_over"
        return "continue"

    def _resolve_combat(self, enemy: Enemy) -> str:
        if enemy.type == EnemyType.MIMIC and not enemy.awake:
            enemy.awake = True
            enemy.visible = True
            self.log("Это был мимик!")
        
        enemy.awake = True
        enemy.visible = True
        
        while enemy.is_alive() and self.player.is_alive():
            dmg = self.player.attack(enemy)
            if dmg:
                self.stats.hits_dealt += 1
                self.stats.damage_dealt += dmg
                self.log(f"Вы наносите {dmg} урона {enemy.type.name.lower()}.")
            else:
                self.log("Вы промахиваетесь.")

            if not enemy.is_alive():
                gold = enemy.drop_treasures()
                self.player.treasure_value += gold
                self.stats.treasure_collected += gold
                self.stats.enemies_defeated += 1
                self.level.remove_enemy(enemy)
                self.log(f"Противник повержен. Сокровища +{gold}.")
                break

            dmg_taken = enemy.attack(self.player)
            if dmg_taken:
                self.stats.hits_taken += 1
                self.stats.damage_taken += dmg_taken
                self.log(f"{enemy.type.name.title()} атакует на {dmg_taken}.")

                if self.balancing:
                    self.balancing.record_damage(dmg_taken)

                if not self.player.is_alive():
                    return "game_over"
            else:
                self.log(f"{enemy.type.name.title()} промахивается.")

        return "continue"

    def _advance_enemies(self) -> Optional[str]:
        enemies = list(self.level.get_all_enemies())
        for enemy in enemies:
            if not enemy.is_alive():
                continue
            if enemy.resting:
                enemy.resting = False
                continue
            EnemyAI.move(enemy, self.level, self.player)
            if enemy.x == self.player.x and enemy.y == self.player.y:
                outcome = self._resolve_combat(enemy)
                if outcome != "continue":
                    return outcome
        return None

    def use_item(self, item_type: str, index: Optional[int]) -> bool:
        if item_type == "weapon" and index is None:
            if self.player.unequip_weapon(self.level):
                self.log("Вы убрали оружие.")
                return True
            return False

        if index is None:
            return False

        item = self.player.backpack.remove_item(item_type, index)
        if not item:
            return False

        self.player.use_item(item, self.level)

        if isinstance(item, Weapon):
            self.stats.weapons_swapped += 1
            self.log(f"Вы экипировались: {item.name}.")
        elif item.item_type == "food":
            self.stats.food_consumed += 1
            self.log(f"Вы съели {item.name}.")
        elif item.item_type == "elixir":
            self.stats.elixirs_used += 1
            self.log(f"Вы выпили {item.name}.")
        elif item.item_type == "scroll":
            self.stats.scrolls_used += 1
            self.log(f"Вы прочитали {item.name}.")
        return True

    def to_dict(self) -> Dict:
        result = {
            "player": self.player.to_dict(),
            "level": self.level.to_dict(),
            "stats": self.stats.to_dict(),
            "level_index": self.level_index,
            "total_levels": self.total_levels,
        }
        if self.balancing:
            result["balancing"] = {
                "difficulty": self.balancing.difficulty,
                "health_lost_recent": self.balancing.health_lost_recent,
            }
        return result

    def _load_state(self, state: Dict):
        self.player = Player.from_dict(state["player"])
        self.level = Level.from_dict(state["level"])
        self.stats = GameStats.from_dict(state["stats"])
        self.level_index = state["level_index"]
        self.total_levels = state.get("total_levels", self.TOTAL_LEVELS)

        saved = state.get("balancing", {})
        self.balancing = DynamicBalancingSystem()
        self.balancing.difficulty = saved.get("difficulty", 5)
        self.balancing.health_lost_recent = saved.get("health_lost_recent", 0)
        self.balancing.level_start_time = time.time()

    def leaderboard_entry(self, result: str) -> Dict:
        return {
            "treasure": self.player.treasure_value,
            "level_reached": self.level_index,
            "result": result,
            "steps": self.stats.steps,
            "enemies_defeated": self.stats.enemies_defeated,
            "food_consumed": self.stats.food_consumed,
            "elixirs_used": self.stats.elixirs_used,
            "scrolls_used": self.stats.scrolls_used,
            "hits_dealt": self.stats.hits_dealt,
            "hits_taken": self.stats.hits_taken,
            "damage_dealt": self.stats.damage_dealt,
            "damage_taken": self.stats.damage_taken,
        }
