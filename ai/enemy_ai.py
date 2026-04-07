import random
from heapq import heappop, heappush
from typing import List, Tuple

from entities.enemy import Enemy, EnemyType
from level.level import Level


class EnemyAI:
    @staticmethod
    def move(enemy: Enemy, level: Level, player):
        if not enemy.is_alive():
            return

        if enemy.type == EnemyType.MIMIC and not enemy.awake:
            if (enemy.x, enemy.y) == (player.x, player.y):
                enemy.awake = True
                enemy.visible = True
            return

        dist = enemy.distance_to(player.x, player.y)
        path: List[Tuple[int, int]] = []
        
        if not enemy.awake and dist <= enemy.hostility:
            enemy.awake = True
            enemy.visible = True
            if enemy.type == EnemyType.MIMIC:
                enemy.disguise_as = None
        
        if dist <= enemy.hostility:
            path = EnemyAI._astar(level, (enemy.x, enemy.y), (player.x, player.y))
            if path:
                enemy.awake = True
                enemy.visible = True

        if enemy.awake and path and len(path) > 1 and not enemy.resting:
            nx, ny = path[1]
            if (nx, ny) == (player.x, player.y):
                return
            if level.is_passable(nx, ny, player) and level.get_enemy_at(nx, ny) is None:
                enemy.x, enemy.y = nx, ny
                return

        EnemyAI._idle_behavior(enemy, level)

    @staticmethod
    def _idle_behavior(enemy: Enemy, level: Level):
        if enemy.type == EnemyType.GHOST:
            room = level.room_lookup.get((enemy.x, enemy.y))
            if room:
                enemy.x, enemy.y = room.random_interior_position()
            enemy.visible = random.random() > 0.4
            return

        if enemy.type == EnemyType.OGRE:
            dirs = [(-2, 0), (2, 0), (0, -2), (0, 2)]
            random.shuffle(dirs)
            for dx, dy in dirs:
                mid_x, mid_y = enemy.x + dx // 2, enemy.y + dy // 2
                nx, ny = enemy.x + dx, enemy.y + dy
                if level.is_passable(mid_x, mid_y) and level.is_passable(nx, ny):
                    enemy.x, enemy.y = nx, ny
                    return
        elif enemy.type == EnemyType.SNAKE_MAGE:
            dirs = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
            if enemy._last_direction and enemy._last_direction in dirs:
                dirs = [d for d in dirs if d != enemy._last_direction]
            if not dirs:
                dirs = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
            random.shuffle(dirs)
            for dx, dy in dirs:
                nx, ny = enemy.x + dx, enemy.y + dy
                if level.is_passable(nx, ny):
                    enemy.x, enemy.y = nx, ny
                    enemy._last_direction = (dx, dy)
                    return
        else:
            dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
            random.shuffle(dirs)
            for dx, dy in dirs:
                nx, ny = enemy.x + dx, enemy.y + dy
                if level.is_passable(nx, ny):
                    enemy.x, enemy.y = nx, ny
                    return

    @staticmethod
    def _astar(level: Level, start: Tuple[int, int], goal: Tuple[int, int]) -> List[Tuple[int, int]]:
        if start == goal:
            return [start]

        open_set = []
        heappush(open_set, (0, start))
        came_from = {}
        cost = {start: 0}

        while open_set:
            _, current = heappop(open_set)
            if current == goal:
                path = [current]
                while current in came_from:
                    current = came_from[current]
                    path.append(current)
                return path[::-1]

            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                neighbor = (current[0] + dx, current[1] + dy)
                if not level.is_passable(*neighbor):
                    continue
                if neighbor in cost:
                    continue
                new_cost = cost[current] + 1
                cost[neighbor] = new_cost
                priority = new_cost + abs(neighbor[0] - goal[0]) + abs(neighbor[1] - goal[1])
                came_from[neighbor] = current
                heappush(open_set, (priority, neighbor))

        return []
