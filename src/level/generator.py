import random
from typing import List, Tuple, Dict, Optional, Set
from collections import deque

from src.entities import Enemy, EnemyType
from src.entities.entity import Key, Elixir, Food, Scroll, Weapon
from .level import Level
from .room import Room


class Door:
    def __init__(self, color: str, positions: List[Tuple[int, int]]):
        self.color = color
        self.positions = positions


class LevelGenerator:
    W, H = 80, 24
    GRID = 3
    COLORS = ["red", "blue", "yellow"]

    @staticmethod
    def generate(level_idx: int, adjustments: Optional[Dict[str, float]] = None) -> Level:
        if adjustments is None:
            adjustments = {"enemy": 1.0, "hp": 1.0, "dmg": 1.0, "items": 1.0}

        rooms = LevelGenerator._make_rooms()
        corridors = LevelGenerator._connect_rooms(rooms)
        corridor_tiles = {tile for path in corridors for tile in path}
        start_room, exit_room = LevelGenerator._set_start_exit(rooms)
        LevelGenerator._place_stairs(exit_room)
        LevelGenerator._populate(rooms, level_idx, start_room, adjustments)

        if level_idx < 1:
            return Level(rooms, corridor_tiles, level_idx, doors=[], keys={})

        doors, keys = LevelGenerator._create_door_key_pairs(rooms, corridors, start_room, level_idx)
        return Level(rooms, corridor_tiles, level_idx, doors=doors, keys=keys)

    @staticmethod
    def _cell_bounds(index: int, total: int, segments: int) -> Tuple[int, int]:
        base = total // segments
        remainder = total % segments
        start = index * base + min(index, remainder)
        end = start + base + (1 if index < remainder else 0)
        return start, end

    @staticmethod
    def _make_rooms() -> List[Room]:
        rooms: List[Room] = []
        for gy in range(LevelGenerator.GRID):
            for gx in range(LevelGenerator.GRID):
                x0, x1 = LevelGenerator._cell_bounds(gx, LevelGenerator.W, LevelGenerator.GRID)
                y0, y1 = LevelGenerator._cell_bounds(gy, LevelGenerator.H, LevelGenerator.GRID)
                width = random.randint(6, max(7, x1 - x0 - 1))
                height = random.randint(5, max(6, y1 - y0 - 1))
                min_x = max(1, x0 + 1)
                max_x = max(min_x, x1 - width - 1)
                min_y = max(1, y0 + 1)
                max_y = max(min_y, y1 - height - 1)
                x = random.randint(min_x, max_x)
                y = random.randint(min_y, max_y)
                rooms.append(Room(x, y, width, height))
        return rooms

    @staticmethod
    def _connect_rooms(rooms: List[Room]) -> List[List[Tuple[int, int]]]:
        corridors: List[List[Tuple[int, int]]] = []
        grid = [rooms[i * LevelGenerator.GRID:(i + 1) * LevelGenerator.GRID] for i in range(LevelGenerator.GRID)]

        for gy in range(LevelGenerator.GRID):
            for gx in range(LevelGenerator.GRID):
                room = grid[gy][gx]
                if gx < LevelGenerator.GRID - 1:
                    corridors.append(LevelGenerator._make_corridor(room, grid[gy][gx + 1]))
                if gy < LevelGenerator.GRID - 1:
                    corridors.append(LevelGenerator._make_corridor(room, grid[gy + 1][gx]))

        extra_pairs = random.sample(range(len(rooms)), k=LevelGenerator.GRID)
        for idx in extra_pairs:
            target = random.randrange(len(rooms))
            if idx == target:
                continue
            corridors.append(LevelGenerator._make_corridor(rooms[idx], rooms[target]))
        return corridors

    @staticmethod
    def _make_corridor(r1: Room, r2: Room) -> List[Tuple[int, int]]:
        cx1, cy1 = r1.center
        cx2, cy2 = r2.center
        path = []
        x, y = cx1, cy1
        while x != cx2:
            x += 1 if cx2 > x else -1
            path.append((x, y))
        while y != cy2:
            y += 1 if cy2 > y else -1
            path.append((x, y))
        return path

    @staticmethod
    def _set_start_exit(rooms: List[Room]):
        start = random.choice(rooms)
        start.is_start = True
        exit_room = random.choice([room for room in rooms if room != start])
        return start, exit_room

    @staticmethod
    def _place_stairs(room: Room):
        for _ in range(50):
            sx = random.randint(1, room.width - 2)
            sy = random.randint(1, room.height - 2)
            pos = (room.x + sx, room.y + sy)
            if pos not in room.items:
                room.stairs = pos
                return
        room.stairs = (room.x + room.width // 2, room.y + room.height // 2)

    @staticmethod
    def _create_door_key_pairs(rooms: List[Room], corridors: List[List[Tuple[int, int]]],
                               start_room: Room, level_idx: int):
        all_entrances = LevelGenerator._find_all_entrances(rooms, corridors)

        lockable_rooms = [r for r in rooms if r != start_room and all_entrances.get(r)]

        if not lockable_rooms:
            return [], {}

        if level_idx <= 6:
            max_pairs = random.randint(1, 2)
        elif level_idx <= 15:
            max_pairs = random.randint(2, 3)
        else:
            max_pairs = random.randint(3, 4)
        max_pairs = min(max_pairs, len(lockable_rooms))

        room_graph = LevelGenerator._build_complete_room_graph(rooms, corridors)

        final_keys = {}
        final_doors = []
        colors_used = []
        successful_pairs = 0

        random.shuffle(lockable_rooms)

        for locked_room in lockable_rooms:
            if successful_pairs >= max_pairs:
                break

            available_colors = [c for c in LevelGenerator.COLORS if c not in colors_used]
            if not available_colors:
                break
            color = random.choice(available_colors)

            accessible_before_lock = LevelGenerator._get_accessible_rooms_without_room(
                room_graph, start_room, locked_room
            )

            key_room_candidates = [r for r in accessible_before_lock if r != locked_room]

            if not key_room_candidates:
                continue

            key_room = random.choice(key_room_candidates)

            key_placed = False
            for attempt in range(50):
                kx, ky = key_room.random_interior_position()
                if (key_room.x + 1 <= kx <= key_room.x + key_room.width - 2 and
                        key_room.y + 1 <= ky <= key_room.y + key_room.height - 2 and
                        (kx, ky) not in final_keys):
                    final_keys[(kx, ky)] = Key(color)
                    key_placed = True
                    break

            if not key_placed:
                continue

            room_entrances = all_entrances.get(locked_room, [])
            if not room_entrances:
                keys_to_remove = [pos for pos, key in final_keys.items() if key.color == color]
                for pos in keys_to_remove:
                    del final_keys[pos]
                continue

            door_positions = []
            for entrance in room_entrances:
                door_positions.append(entrance)

            final_doors.append(Door(color, door_positions))

            colors_used.append(color)
            successful_pairs += 1

        return final_doors, final_keys

    @staticmethod
    def _build_complete_room_graph(rooms: List[Room], corridors: List[List[Tuple[int, int]]]) -> Dict[Room, Set[Room]]:
        graph = {room: set() for room in rooms}

        for path in corridors:
            path_rooms = []
            for x, y in path:
                for room in rooms:
                    if room.contains(x, y) and room not in path_rooms:
                        path_rooms.append(room)

            for i in range(len(path_rooms)):
                for j in range(i + 1, len(path_rooms)):
                    graph[path_rooms[i]].add(path_rooms[j])
                    graph[path_rooms[j]].add(path_rooms[i])

        return graph

    @staticmethod
    def _find_all_entrances(rooms: List[Room], corridors: List[List[Tuple[int, int]]]) -> Dict[
        Room, List[Tuple[int, int]]]:
        entrances = {room: [] for room in rooms}

        corridor_cells = set()
        for path in corridors:
            for pos in path:
                corridor_cells.add(pos)

        for room in rooms:
            for x in range(room.x, room.x + room.width):
                y = room.y - 1
                if (x, y) in corridor_cells and 0 <= x < LevelGenerator.W and 0 <= y < LevelGenerator.H:
                    if not room.contains(x, y) and room.contains(x, room.y):
                        entrances[room].append((x, room.y))

            for x in range(room.x, room.x + room.width):
                y = room.y + room.height
                if (x, y) in corridor_cells and 0 <= x < LevelGenerator.W and 0 <= y < LevelGenerator.H:
                    if not room.contains(x, y) and room.contains(x, room.y + room.height - 1):
                        entrances[room].append((x, room.y + room.height - 1))

            for y in range(room.y, room.y + room.height):
                x = room.x - 1
                if (x, y) in corridor_cells and 0 <= x < LevelGenerator.W and 0 <= y < LevelGenerator.H:
                    if not room.contains(x, y) and room.contains(room.x, y):
                        entrances[room].append((room.x, y))

            for y in range(room.y, room.y + room.height):
                x = room.x + room.width
                if (x, y) in corridor_cells and 0 <= x < LevelGenerator.W and 0 <= y < LevelGenerator.H:
                    if not room.contains(x, y) and room.contains(room.x + room.width - 1, y):
                        entrances[room].append((room.x + room.width - 1, y))

        return entrances

    @staticmethod
    def _get_accessible_rooms_without_room(graph: Dict[Room, Set[Room]], start: Room, excluded: Room) -> Set[Room]:
        visited = set()
        queue = deque([start])

        while queue:
            current = queue.popleft()
            if current in visited:
                continue

            visited.add(current)

            for neighbor in graph.get(current, set()):
                if neighbor != excluded and neighbor not in visited:
                    queue.append(neighbor)

        return visited

    @staticmethod
    def _populate(rooms: List[Room], level_idx: int, start: Room, adjustments: Dict[str, float]):
        enemy_mult = adjustments["enemy"]
        hp_mult = adjustments["hp"]
        dmg_mult = adjustments["dmg"]
        item_mult = adjustments["items"]

        item_pool = [
            lambda: Food("Еда", random.randint(20, 35)),
            lambda: Elixir("Эликсир силы", power=2, duration=8),
            lambda: Elixir("Эликсир ловкости", dexterity=2, duration=8),
            lambda: Elixir("Эликсир жизненной силы", max_health=2, duration=8),
            lambda: Scroll("Свиток силы", power=5),
            lambda: Scroll("Свиток ловкости", dexterity=5),
            lambda: Scroll("Свиток жизненной силы", max_health=5),
            lambda: Weapon("Лезвие", random.randint(2, 6)),
            lambda: Weapon("Меч", random.randint(4, 8)),
            lambda: Weapon("Кинжал", random.randint(3, 7)),
        ]

        for room in rooms:
            if room is start:
                continue

            base_enemies = random.randint(1, min(1 + level_idx // 3, 5))
            enemies_count = max(1, int(base_enemies * enemy_mult))

            mimic_placed = False
            for _ in range(enemies_count):
                if not mimic_placed and random.random() < 0.15 + level_idx * 0.01:
                    enemy_type = EnemyType.MIMIC
                    mimic_placed = True
                else:
                    enemy_type = random.choice([et for et in EnemyType if et != EnemyType.MIMIC])
                
                enemy = Enemy.create(enemy_type, level_idx)

                enemy.health = max(1, int(enemy.health * hp_mult))
                enemy.max_health = max(1, int(enemy.max_health * hp_mult))
                enemy.power = max(1, int(enemy.power * dmg_mult))
                enemy.dexterity = max(1, int(enemy.dexterity * (0.9 + 0.2 * dmg_mult)))

                for _ in range(100):
                    ex = random.randint(1, room.width - 2)
                    ey = random.randint(1, room.height - 2)
                    pos = (room.x + ex, room.y + ey)
                    if (not room.get_enemy_at(pos[0], pos[1]) and
                            (room.stairs is None or pos != room.stairs)):
                        enemy.x, enemy.y = pos
                        room.add_enemy(enemy)
                        break

            items_to_place = int(random.randint(0, 3) * item_mult)
            for _ in range(items_to_place):
                item_factory = random.choice(item_pool)
                item = item_factory()
                ix = random.randint(1, room.width - 2)
                iy = random.randint(1, room.height - 2)
                pos = (room.x + ix, room.y + iy)
                if pos not in room.items and room.get_enemy_at(pos[0], pos[1]) is None:
                    room.items.setdefault(pos, []).append(item)
