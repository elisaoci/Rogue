from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Set, Tuple, TYPE_CHECKING

from src.entities import Enemy
from src.entities.entity import Item, Key, item_from_dict
from .room import Room

if TYPE_CHECKING:
    from src.entities.entity import Player


class Tile:
    WALL = '#'
    FLOOR = '.'
    STAIRS = '>'
    DOOR = '+'


class Level:
    W, H = 80, 24

    def __init__(self, rooms, corridors, level_idx, doors=None, keys=None):
        self.rooms = rooms
        if isinstance(corridors, set):
            self.corridors = corridors
        else:
            self.corridors = set()
            for path in corridors:
                if isinstance(path, (list, tuple)):
                    for pos in path:
                        if isinstance(pos, (list, tuple)) and len(pos) == 2:
                            self.corridors.add(tuple(pos))
                        else:
                            self.corridors.add(pos if isinstance(pos, tuple) else tuple(pos))
                else:
                    self.corridors.add(path if isinstance(path, tuple) else tuple(path))
        self.level_idx = level_idx
        self.doors = doors or []
        self.keys = keys or {}
        self.index = level_idx
        self.start_room = next(r for r in rooms if r.is_start)

        self.tiles: Dict[Tuple[int, int], str] = {}
        self.room_lookup: Dict[Tuple[int, int], Room] = {}
        self.dropped_items: Dict[Tuple[int, int], List[Item]] = defaultdict(list)
        self.explored: Set[Tuple[int, int]] = set()
        self.visible_tiles: Set[Tuple[int, int]] = set()

        self._build_map()
        if self.doors:
            self._place_colored_doors_only()

    def _build_map(self):
        for y in range(self.H):
            for x in range(self.W):
                self.tiles[(x, y)] = Tile.WALL

        for room in self.rooms:
            for x in range(room.x + 1, room.x + room.width - 1):
                for y in range(room.y + 1, room.y + room.height - 1):
                    self.tiles[(x, y)] = Tile.FLOOR
                    self.room_lookup[(x, y)] = room
            for x in range(room.x, room.x + room.width):
                self.tiles[(x, room.y)] = Tile.WALL
                self.tiles[(x, room.y + room.height - 1)] = Tile.WALL
            for y in range(room.y, room.y + room.height):
                self.tiles[(room.x, y)] = Tile.WALL
                self.tiles[(room.x + room.width - 1, y)] = Tile.WALL

        for pos in self.corridors:
            self.tiles[pos] = Tile.FLOOR

        for room in self.rooms:
            if room.stairs:
                self.tiles[room.stairs] = Tile.STAIRS

    def _place_colored_doors_only(self):
        intended_door_positions = set()
        for door in self.doors:
            for pos in door.positions:
                if 0 <= pos[0] < self.W and 0 <= pos[1] < self.H:
                    intended_door_positions.add(pos)

        for y in range(self.H):
            for x in range(self.W):
                current_tile = self.tiles.get((x, y))

                if current_tile == Tile.DOOR:
                    if (x, y) in intended_door_positions:
                        continue
                    else:
                        self.tiles[(x, y)] = Tile.WALL
                elif (x, y) in intended_door_positions:
                    self.tiles[(x, y)] = Tile.DOOR

    def get_door_at(self, x: int, y: int):
        for door in self.doors:
            if (x, y) in door.positions:
                return door
        return None

    def is_passable(self, x: int, y: int, player=None) -> bool:
        if not (0 <= x < self.W and 0 <= y < self.H):
            return False
        tile = self.tiles.get((x, y))
        if tile == Tile.WALL:
            return False
        if tile == Tile.DOOR:
            door = self.get_door_at(x, y)
            if door:
                if player and door.color in player.backpack.keys:
                    return True
                return False
            return True
        return tile in (Tile.FLOOR, Tile.STAIRS)

    def try_open_door(self, player: "Player", x: int, y: int) -> bool:
        door = self.get_door_at(x, y)
        if not door:
            return True

        if door.color not in player.backpack.keys:
            return False

        doors_to_remove = []
        for d in self.doors:
            if d.color == door.color:
                for pos in d.positions:
                    self.tiles[pos] = Tile.FLOOR
                doors_to_remove.append(d)

        for d in doors_to_remove:
            if d in self.doors:
                self.doors.remove(d)

        return True

    def get_enemy_at(self, x: int, y: int) -> Optional[Enemy]:
        for enemy in self.get_all_enemies():
            if enemy.x == x and enemy.y == y and enemy.is_alive():
                return enemy
        return None

    def remove_enemy(self, enemy: Enemy):
        for room in self.rooms:
            if enemy in room.enemies:
                room.enemies.remove(enemy)
                return

    def get_all_enemies(self):
        return [e for room in self.rooms for e in room.enemies]

    def get_items_at(self, x: int, y: int) -> List[Item]:
        room = self.room_lookup.get((x, y))
        if room:
            return room.get_items_at(x, y)
        return self.dropped_items.get((x, y), [])

    def remove_item(self, x: int, y: int, item: Item):
        room = self.room_lookup.get((x, y))
        if room:
            room.remove_item(item)
        else:
            storage = self.dropped_items.get((x, y))
            if storage and item in storage:
                storage.remove(item)
                if not storage:
                    del self.dropped_items[(x, y)]

    def collect_items_for_player(self, player: "Player") -> List[Item]:
        collected = []
        pos = (player.x, player.y)
        room = self.room_lookup.get(pos)

        if room:
            items_here = room.get_items_at(player.x, player.y)
            for item in list(items_here):
                if player.backpack.add(item):
                    collected.append(item)
                    room.remove_item(item)

        for item in list(self.dropped_items.get(pos, [])):
            if player.backpack.add(item):
                collected.append(item)
                self.dropped_items[pos].remove(item)
                if not self.dropped_items[pos]:
                    del self.dropped_items[pos]

        if pos in self.keys:
            key = self.keys[pos]
            player.backpack.keys.add(key.color)
            del self.keys[pos]
            collected.append(key)

        return collected

    def drop_item(self, pos: Tuple[int, int], item: Item):
        x, y = pos
        room = self.room_lookup.get((x, y))
        if room:
            room.items.setdefault((x, y), []).append(item)
        else:
            self.dropped_items[(x, y)].append(item)

    def drop_item_near(self, position: Tuple[int, int], item: Item) -> bool:
        x, y = position
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if self.is_passable(nx, ny) and not self.has_item_at(nx, ny):
                self.drop_item((nx, ny), item)
                return True
        
        return False

    def has_item_at(self, x: int, y: int) -> bool:
        room = self.room_lookup.get((x, y))
        if room and room.get_items_at(x, y):
            return True
        
        if (x, y) in self.dropped_items and self.dropped_items[(x, y)]:
            return True
        
        return False

    def _line_of_sight(self, start: Tuple[int, int], end: Tuple[int, int]) -> bool:
        x0, y0 = start
        x1, y1 = end
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            if (x0, y0) == (x1, y1):
                return True
            if self.tiles.get((x0, y0)) == Tile.WALL and (x0, y0) != start:
                return False
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def visible_from(self, player: "Player", radius: int = 8) -> Set[Tuple[int, int]]:
        visible = set()
        start = (player.x, player.y)
        room = self.room_lookup.get(start)
        if room:
            for x in range(room.x, room.x + room.width):
                for y in range(room.y, room.y + room.height):
                    visible.add((x, y))

        queue = deque([start])
        visited = {start}
        while queue:
            x, y = queue.popleft()
            visible.add((x, y))
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
                nx, ny = x + dx, y + dy
                if (nx, ny) in visited:
                    continue
                if not self._line_of_sight(start, (nx, ny)):
                    continue
                visited.add((nx, ny))
                if self.tiles.get((nx, ny)) != Tile.WALL:
                    queue.append((nx, ny))

        self.visible_tiles = visible
        self.explored |= visible
        return visible

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "rooms": [r.to_dict() for r in self.rooms],
            "corridors": [list(p) for p in self.corridors],
            "doors": [{"color": d.color, "positions": [list(p) for p in d.positions]} for d in self.doors] if self.doors else [],
            "keys": {f"{x}:{y}": {"type": "key", "color": v.color} for (x, y), v in self.keys.items()},
            "dropped_items": [{"pos": [x, y], "items": [i.to_dict() for i in items]} for (x, y), items in self.dropped_items.items()],
            "explored": [list(p) for p in self.explored],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Level":
        from .generator import Door
        rooms = [Room.from_dict(r) for r in data["rooms"]]
        corridors = data.get("corridors", [])
        if corridors and isinstance(corridors[0], list):
            corridors = [tuple(p) for path in corridors for p in path]
        else:
            corridors = [tuple(p) if isinstance(p, list) else p for p in corridors]
        
        doors = [Door(d["color"], [tuple(p) for p in d["positions"]]) for d in data.get("doors", [])]
        keys = {tuple(map(int, k.split(":"))): Key(v["color"]) for k, v in data.get("keys", {}).items()}
        level = cls(rooms, corridors, data["index"], doors=doors, keys=keys)
        for e in data.get("dropped_items", []):
            pos = tuple(e["pos"])
            level.dropped_items[pos] = [item_from_dict(i) for i in e["items"]]
        level.explored = {tuple(p) for p in data.get("explored", [])}
        return level
