import math
from typing import List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from src.level import Level
    from src.entities.entity import Player


class RayCast3D:
    def __init__(self, level: "Level", player: "Player"):
        self.level = level
        self.player = player
        self.is_3d_mode = False

        self.player_x = float(player.x) + 0.5
        self.player_y = float(player.y) + 0.5
        self.player_angle = 0.0  
        self.fov = math.pi / 3  
        self.move_speed = 0.15
        self.rotation_speed = 0.15

        self.wall_textures = {
            '#': ['█', '▓', '▒', '░'], 
            '+': ['║', '│', '┃', '┆'], 
        }

    def sync_with_player(self):
        self.player_x = float(self.player.x) + 0.5
        self.player_y = float(self.player.y) + 0.5

    def toggle_3d_mode(self):
        self.is_3d_mode = not self.is_3d_mode
        if self.is_3d_mode:
            self.sync_with_player()
        else:
            self.player.set_position(int(self.player_x), int(self.player_y))
        return self.is_3d_mode

    def handle_3d_input(self, key: int) -> bool:
        if not self.is_3d_mode:
            return False

        old_x, old_y, old_angle = self.player_x, self.player_y, self.player_angle

        if key == ord('w'):
            self.player_x += math.cos(self.player_angle) * self.move_speed
            self.player_y += math.sin(self.player_angle) * self.move_speed
        elif key == ord('s'):
            self.player_x -= math.cos(self.player_angle) * self.move_speed
            self.player_y -= math.sin(self.player_angle) * self.move_speed
        elif key == ord('a'):
            self.player_angle -= self.rotation_speed
        elif key == ord('d'):
            self.player_angle += self.rotation_speed
        else:
            return False

        self.player_angle %= 2 * math.pi

        map_x, map_y = int(self.player_x), int(self.player_y)
        if not self._can_move_to(map_x, map_y):
            self.player_x, self.player_y, self.player_angle = old_x, old_y, old_angle
            return True

        self.player.set_position(map_x, map_y)
        return True

    def _can_move_to(self, map_x: int, map_y: int) -> bool:
        if not (0 <= map_x < self.level.W and 0 <= map_y < self.level.H):
            return False
        return self.level.is_passable(map_x, map_y, self.player)

    def cast_ray(self, angle: float) -> Tuple[float, str, float]:
        ray_dir_x = math.cos(angle)
        ray_dir_y = math.sin(angle)
        ray_x, ray_y = self.player_x, self.player_y

        step_x = 1 if ray_dir_x >= 0 else -1
        step_y = 1 if ray_dir_y >= 0 else -1

        delta_dist_x = abs(1 / ray_dir_x) if ray_dir_x != 0 else 1e30
        delta_dist_y = abs(1 / ray_dir_y) if ray_dir_y != 0 else 1e30

        side_dist_x = (ray_x - int(ray_x)) * delta_dist_x if ray_dir_x < 0 else (
            int(ray_x) + 1.0 - ray_x) * delta_dist_x
        side_dist_y = (ray_y - int(ray_y)) * delta_dist_y if ray_dir_y < 0 else (
            int(ray_y) + 1.0 - ray_y) * delta_dist_y

        map_x, map_y = int(ray_x), int(ray_y)
        hit, side = False, 0
        max_dist = 20

        for _ in range(max_dist):
            if side_dist_x < side_dist_y:
                side_dist_x += delta_dist_x
                map_x += step_x
                side = 0
            else:
                side_dist_y += delta_dist_y
                map_y += step_y
                side = 1

            if not (0 <= map_x < self.level.W and 0 <= map_y < self.level.H):
                break

            tile = self.level.tiles.get((map_x, map_y), '#')
            if tile in ('#', '+'):
                hit = True
                break

        if not hit:
            return 10.0, '#', 0.0

        if side == 0:
            dist = (map_x - ray_x + (1 - step_x) / 2) / ray_dir_x
        else:
            dist = (map_y - ray_y + (1 - step_y) / 2) / ray_dir_y

        if side == 0:
            wall_x = ray_y + dist * ray_dir_y
        else:
            wall_x = ray_x + dist * ray_dir_x
        wall_x -= math.floor(wall_x)

        tile = self.level.tiles.get((map_x, map_y), '#')

        return abs(dist), tile, wall_x

    def render_3d_view(self, screen_height: int, screen_width: int) -> List[List[str]]:
        screen = [[' ' for _ in range(screen_width)] for _ in range(screen_height)]

        for x in range(screen_width):
            camera_x = 2 * x / screen_width - 1
            ray_angle = self.player_angle + self.fov / 2 * camera_x

            dist, wall_type, tex_pos = self.cast_ray(ray_angle)

            line_height = int(screen_height / dist) if dist > 0 else screen_height
            line_height = min(screen_height, line_height)

            texture = self.wall_textures.get(wall_type, self.wall_textures['#'])
            tex_char = texture[min(3, int(tex_pos * 4))]
            brightness = max(0.2, 1.0 - dist / 8.0)
            if brightness < 0.4:
                tex_char = texture[3]
            elif brightness < 0.7:
                tex_char = texture[2]

            draw_start = max(0, (screen_height - line_height) // 2)
            draw_end = min(screen_height, (screen_height + line_height) // 2)

            for y in range(draw_start, draw_end):
                screen[y][x] = tex_char
        for y in range(screen_height):
            for x in range(screen_width):
                if screen[y][x] == ' ':
                    if y < screen_height // 2:
                        screen[y][x] = '·'
                    else:
                        screen[y][x] = '_' 

        return screen

    def render_minimap(self, width: int = 20, height: int = 10) -> List[List[str]]:
        minimap = [[' ' for _ in range(width)] for _ in range(height)]

        if self.level.W == 0 or self.level.H == 0:
            return minimap
        scale_x = self.level.W / width
        scale_y = self.level.H / height

        for y in range(height):
            for x in range(width):
                map_x = int(x * scale_x)
                map_y = int(y * scale_y)

                if (0 <= map_x < self.level.W and 0 <= map_y < self.level.H):
                    tile = self.level.tiles.get((map_x, map_y), ' ')
                    if (map_x, map_y) in self.level.explored:
                        if tile == '#':
                            minimap[y][x] = '#'
                        elif tile in ('.', '>', '+'):
                            minimap[y][x] = '.'
                    else:
                        minimap[y][x] = ' '

        player_map_x = int(self.player_x / scale_x)
        player_map_y = int(self.player_y / scale_y)

        if (0 <= player_map_x < width and 0 <= player_map_y < height):
            minimap[player_map_y][player_map_x] = '@'

            dir_x = int(math.cos(self.player_angle) * 2)
            dir_y = int(math.sin(self.player_angle) * 2)
            for i in range(1, 3):
                dir_xx = player_map_x + dir_x * i
                dir_yy = player_map_y + dir_y * i
                if (0 <= dir_xx < width and 0 <= dir_yy < height and
                        minimap[dir_yy][dir_xx] == ' '):
                    minimap[dir_yy][dir_xx] = '·'

        return minimap
