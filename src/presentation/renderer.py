import curses
from typing import List, Optional, Sequence, Tuple, TYPE_CHECKING

from src.entities.entity import Item, Key
from src.entities import EnemyType, Enemy
from src.level import Tile
from .raycast_3d import RayCast3D

if TYPE_CHECKING:
    from src.game import GameSession, GameStats

ITEM_SYMBOLS = {
    "food": "f",
    "weapon": "/",
    "elixir": "!",
    "scroll": "?",
    "treasure": "$",
}

COLOR_PAIR_ZOMBIE = 1
COLOR_PAIR_VAMPIRE = 2
COLOR_PAIR_GHOST = 3
COLOR_PAIR_OGRE = 4
COLOR_PAIR_SNAKE_MAGE = 5
COLOR_PAIR_KEY_RED = 6
COLOR_PAIR_KEY_YELLOW = 7
COLOR_PAIR_KEY_BLUE = 8
COLOR_PAIR_DOOR_RED = 9
COLOR_PAIR_DOOR_YELLOW = 10
COLOR_PAIR_DOOR_BLUE = 11
COLOR_PAIR_DOOR_OPEN = 12


class Renderer:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        curses.curs_set(0)
        self.stdscr.keypad(True)
        self.stdscr.timeout(100)
        self.height, self.width = self.stdscr.getmaxyx()
        self.raycaster: Optional[RayCast3D] = None
        self._init_colors()

    def _init_colors(self):
        if not curses.has_colors():
            return
        curses.start_color()
        try:
            curses.use_default_colors()
        except:
            pass

        curses.init_pair(COLOR_PAIR_ZOMBIE, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(COLOR_PAIR_VAMPIRE, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(COLOR_PAIR_GHOST, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(COLOR_PAIR_OGRE, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(COLOR_PAIR_SNAKE_MAGE, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(COLOR_PAIR_KEY_RED, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(COLOR_PAIR_KEY_YELLOW, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(COLOR_PAIR_KEY_BLUE, curses.COLOR_BLUE, curses.COLOR_BLACK)
        curses.init_pair(COLOR_PAIR_DOOR_RED, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(COLOR_PAIR_DOOR_YELLOW, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(COLOR_PAIR_DOOR_BLUE, curses.COLOR_BLUE, curses.COLOR_BLACK)
        curses.init_pair(COLOR_PAIR_DOOR_OPEN, curses.COLOR_GREEN, curses.COLOR_BLACK)

    def draw(self, session: "GameSession"):
        self.height, self.width = self.stdscr.getmaxyx()
        self.stdscr.erase()

        if self.raycaster is None:
            self.raycaster = RayCast3D(session.level, session.player)

        self.raycaster.level = session.level
        self.raycaster.player = session.player
        
        if not self.raycaster.is_3d_mode:
            self.raycaster.sync_with_player()

        if self.raycaster.is_3d_mode:
            self._draw_3d_view(session)
        else:
            visible = session.level.visible_from(session.player)
            self._draw_map(session, visible)
            self._draw_actors(session, visible)
            self._draw_hud(session)

        self.stdscr.refresh()

    def _draw_map(self, session: "GameSession", visible: Sequence[Tuple[int, int]]):
        level = session.level
        visible_set = set(visible)
        explored = level.explored
        max_map_y = min(24, self.height - 6)

        for (x, y), tile in level.tiles.items():
            if y >= max_map_y or x >= self.width:
                continue
            if (x, y) not in visible_set and (x, y) not in explored:
                continue

            char = tile
            attr = 0

            if tile == Tile.DOOR:
                door_color = None
                door_found = False

                for door in level.doors:
                    if hasattr(door, 'positions') and (x, y) in door.positions:
                        door_color = door.color
                        door_found = True
                        break

                if door_found and door_color:
                    has_key = door_color in session.player.backpack.keys
                    if has_key:
                        attr = curses.color_pair(COLOR_PAIR_DOOR_OPEN) | curses.A_BOLD
                        char = "+"
                    else:
                        color_map = {
                            "red": COLOR_PAIR_DOOR_RED,
                            "yellow": COLOR_PAIR_DOOR_YELLOW,
                            "blue": COLOR_PAIR_DOOR_BLUE
                        }
                        attr = curses.color_pair(color_map.get(door_color, 0)) | curses.A_BOLD
                        char = "+"
                else:
                    char = Tile.WALL
                    attr = 0

            if (x, y) in level.keys and (x, y) in visible_set:
                key = level.keys[(x, y)]
                color_map = {
                    "red": COLOR_PAIR_KEY_RED,
                    "yellow": COLOR_PAIR_KEY_YELLOW,
                    "blue": COLOR_PAIR_KEY_BLUE
                }
                attr = curses.color_pair(color_map.get(key.color, 0)) | curses.A_BOLD
                char = "k"

            if (x, y) not in visible_set:
                char = " " if char == Tile.FLOOR else Tile.WALL

            self._safe_addch(y, x, char, attr)

        for room in level.rooms:
            for (x, y), items in room.items.items():
                if (x, y) in visible_set and items:
                    self._safe_addch(y, x, self._item_glyph(items[-1]))
        
        for (x, y), items in level.dropped_items.items():
            if (x, y) in visible_set and items:
                self._safe_addch(y, x, self._item_glyph(items[-1]))

    def _draw_actors(self, session: "GameSession", visible: Sequence[Tuple[int, int]]):
        player = session.player
        visible_set = set(visible)
        
        for enemy in session.level.get_all_enemies():
            if not enemy.is_alive():
                continue
            if (enemy.x, enemy.y) not in visible_set:
                continue

            if enemy.type == EnemyType.MIMIC and not enemy.awake:
                symbol = ITEM_SYMBOLS.get(getattr(enemy, "disguise_as", "treasure"), "$")
                self._safe_addch(enemy.y, enemy.x, symbol)
                continue

            if not enemy.visible:
                continue

            color_pair = 0
            ch = enemy.type.value
            if enemy.type == EnemyType.ZOMBIE:
                color_pair = COLOR_PAIR_ZOMBIE
            elif enemy.type == EnemyType.VAMPIRE:
                color_pair = COLOR_PAIR_VAMPIRE
            elif enemy.type == EnemyType.GHOST:
                color_pair = COLOR_PAIR_GHOST
            elif enemy.type == EnemyType.OGRE:
                color_pair = COLOR_PAIR_OGRE
            elif enemy.type == EnemyType.SNAKE_MAGE:
                color_pair = COLOR_PAIR_SNAKE_MAGE
            elif enemy.type == EnemyType.MIMIC:
                ch = "m"
                color_pair = curses.COLOR_MAGENTA

            if color_pair > 0:
                self._safe_addch_colored(enemy.y, enemy.x, ch, color_pair)
            else:
                self._safe_addch(enemy.y, enemy.x, ch)

        self._safe_addch(player.y, player.x, "@", curses.A_BOLD)

    def _draw_hud(self, session: "GameSession"):
        player = session.player
        stats = session.stats
        hud_y = min(25, self.height - 5)

        status = (
            f"HP {player.health}/{player.max_health}  "
            f"DEX {player.dexterity}  STR {player.power}  "
            f"WPN {player.current_weapon.name if player.current_weapon else 'none'}  "
            f"LVL {session.level_index}/{session.total_levels}  "
            f"GOLD {player.treasure_value}"
        )
        self._safe_addstr(hud_y, 0, status[: self.width - 1])

        try:
            diff = session.balancing.difficulty
            hp_lost = session.balancing.health_lost_recent

            icons = "▁▂▃▄▅▆▇█"
            bar = icons[-1] * diff + "░" * (10 - diff)
            color = curses.color_pair(3) if diff <= 4 else \
                    curses.color_pair(2) if diff <= 7 else \
                    curses.color_pair(1)

            diff_text = f" СЛОЖНОСТЬ [{bar}] {diff}/10  Урон за ур.: {hp_lost} HP"
            self._safe_addstr(hud_y + 1, 0, diff_text, color | curses.A_BOLD)

        except AttributeError:
            stats_line = (
                f"Steps {stats.steps}  Kills {stats.enemies_defeated}  "
                f"Food {stats.food_consumed}  Elixirs {stats.elixirs_used}  "
                f"Scrolls {stats.scrolls_used}"
            )
            self._safe_addstr(hud_y + 1, 0, stats_line[: self.width - 1])

        if player.backpack.keys:
            key_colors = [color.capitalize() for color in player.backpack.keys]
            keys_str = "Ключи: " + ", ".join(sorted(key_colors))
            self._safe_addstr(hud_y + 2, 0, keys_str[: self.width - 1])
            controls_y = hud_y + 3
        else:
            controls_y = hud_y + 2

        map_width = 80
        right_panel_x = map_width + 2

        if right_panel_x < self.width - 20:
            self._safe_addstr(1, right_panel_x, "Противники:")
            current_level = session.level_index

            zombie = Enemy.create(EnemyType.ZOMBIE, current_level)
            self._safe_addstr(2, right_panel_x, f"Зомби {EnemyType.ZOMBIE.value}:  HP {zombie.max_health}  POWER {zombie.power}  DEX {zombie.dexterity}")

            vampire = Enemy.create(EnemyType.VAMPIRE, current_level)
            self._safe_addstr(3, right_panel_x, f"Вампир {EnemyType.VAMPIRE.value}:  HP {vampire.max_health}  POWER {vampire.power}  DEX {vampire.dexterity}")

            ghost = Enemy.create(EnemyType.GHOST, current_level)
            self._safe_addstr(4, right_panel_x, f"Привидение {EnemyType.GHOST.value}:  HP {ghost.max_health}  POWER {ghost.power}  DEX {ghost.dexterity}")

            ogre = Enemy.create(EnemyType.OGRE, current_level)
            self._safe_addstr(5, right_panel_x, f"Огр {EnemyType.OGRE.value}:  HP {ogre.max_health}  POWER {ogre.power}  DEX {ogre.dexterity}")

            snake_mage = Enemy.create(EnemyType.SNAKE_MAGE, current_level)
            self._safe_addstr(6, right_panel_x, f"Змей-маг {EnemyType.SNAKE_MAGE.value}:  HP {snake_mage.max_health}  POWER {snake_mage.power}  DEX {snake_mage.dexterity}")

        if self.raycaster and self.raycaster.is_3d_mode:
            controls = "3D: W/S — вперед/назад  A/D — поворот  TAB — 2D  H/J/K/E — инвентарь  T — статистика  Q — выход"
        else:
            controls = "WASD/стрелки — движение  TAB — 3D  H/J/K/E — инвентарь  T — статистика  Q — выход"
        self._safe_addstr(controls_y, 0, controls[: self.width - 1])

        log_y = controls_y + 1
        for idx, message in enumerate(session.message_log):
            if log_y + idx >= self.height - 1:
                break
            self._safe_addstr(log_y + idx, 0, message[: self.width - 1])

    def prompt_resume(self, has_save: bool) -> str:
        if not has_save:
            return "new"
        while True:
            self.stdscr.erase()
            prompt = "Найдено сохранение. C — продолжить, N — новая игра, L — лидеры."
            self._safe_addstr(self.height // 2, max(0, (self.width - len(prompt)) // 2), prompt)
            self.stdscr.refresh()
            key = self.stdscr.getch()
            if key in (ord("c"), ord("C")):
                return "continue"
            if key in (ord("n"), ord("N")):
                return "new"
            if key in (ord("l"), ord("L")):
                return "leaderboard"

    def prompt_inventory_choice(
        self, item_type: str, items: List[Item], allow_unequip: bool = False
    ) -> Optional[int]:
        max_len = max((len(item.name) for item in items), default=10)
        height = max(6, len(items) + 5 + (1 if allow_unequip else 0))
        width = min(self.width - 4, max(30, max_len + 10))
        top = max(1, (self.height - height) // 2)
        left = max(1, (self.width - width) // 2)
        win = curses.newwin(height, width, top, left)
        win.box()
        title = f"{item_type.upper()} ({len(items)})"
        win.addstr(1, 2, title[: width - 4])

        if not items and not allow_unequip:
            win.addstr(3, 2, "Нет предметов.")
            win.addstr(height - 2, 2, "Esc — назад")
            win.refresh()
            win.getch()
            return None

        row = 3
        for idx, item in enumerate(items, start=1):
            text = f"{idx}. {item.name}"
            attr = 0
            if isinstance(item, Key):
                color_map = {"red": COLOR_PAIR_KEY_RED, "yellow": COLOR_PAIR_KEY_YELLOW, "blue": COLOR_PAIR_KEY_BLUE}
                attr = curses.color_pair(color_map.get(item.color, 0)) | curses.A_BOLD
            win.addstr(row, 2, text[: width - 4], attr)
            row += 1
        if allow_unequip:
            win.addstr(row, 2, "0. Убрать оружие")
            row += 1
        win.addstr(height - 2, 2, "Выбор (Esc — назад)")
        win.refresh()

        while True:
            key = win.getch()
            if key in (27, ord("q")):
                return None
            if allow_unequip and key in (ord("0"),):
                return -1
            if ord("1") <= key <= ord("9"):
                choice = int(chr(key)) - 1
                if 0 <= choice < len(items):
                    return choice

    def show_statistics(self, leaderboard: List[dict], current: Optional["GameStats"]):
        self.stdscr.erase()
        self._safe_addstr(1, 2, "Топ попыток (по золоту)")
        row = 3
        if not leaderboard:
            self._safe_addstr(row, 2, "Пока нет записей.")
            row += 2
        else:
            for idx, entry in enumerate(leaderboard[:10], start=1):
                line = (
                    f"{idx:2}. {entry.get('treasure', 0):>4} зол. "
                    f"lvl {entry.get('level_reached', 0)} "
                    f"({entry.get('result', '')})"
                )
                self._safe_addstr(row, 2, line[: self.width - 4])
                row += 1
            row += 1

        if current:
            self._safe_addstr(row, 2, "Текущая попытка:")
            row += 1
            self._safe_addstr(row, 4, f"Сокровища: {current.treasure_collected}")
            row += 1
            self._safe_addstr(row, 4, f"Достигнутый уровень: {current.levels_completed}")
            row += 1
            self._safe_addstr(row, 4, f"Побеждено врагов: {current.enemies_defeated}")
            row += 1
            self._safe_addstr(row, 4, f"Съедено еды: {current.food_consumed}")
            row += 1
            self._safe_addstr(row, 4, f"Использовано зелий: {current.elixirs_used}")
            row += 1
            self._safe_addstr(row, 4, f"Прочитано свитков: {current.scrolls_used}")
            row += 1
            self._safe_addstr(row, 4, f"Нанесено ударов: {current.hits_dealt}, Получено ударов: {current.hits_taken}")
            row += 1
            self._safe_addstr(row, 4, f"Пройдено клеток: {current.steps}")

        self._safe_addstr(self.height - 2, 2, "Нажмите любую клавишу...")
        self.stdscr.refresh()
        self.stdscr.getch()

    def game_over(self, session: "GameSession", victory: bool):
        self.stdscr.erase()

        title = "ПОБЕДА!" if victory else "ВЫ ПРОИГРАЛИ"
        subtitle = (
            f"Достигнут уровень: {session.level_index}    "
            f"Собрано золота: {session.player.treasure_value}    "
            f"Убито врагов: {session.stats.enemies_defeated}"
        )

        start_y = self.height // 2 - 5

        self._safe_addstr(start_y, max(0, (self.width - len(title)) // 2), title)
        self._safe_addstr(start_y + 2, max(0, (self.width - len(subtitle)) // 2), subtitle)

        menu_y = start_y + 5
        option1 = "N — Новая игра"
        option2 = "Q — Выйти из игры"
        self._safe_addstr(menu_y, max(0, (self.width - len(option1)) // 2), option1)
        self._safe_addstr(menu_y + 1, max(0, (self.width - len(option2)) // 2), option2)

        self.stdscr.refresh()

        while True:
            key = self.stdscr.getch()
            if key == -1:
                continue

            ch = chr(key).lower()

            if ch in ('n', 'н'):
                return "new"
            if ch in ('q', 'й'):
                return "quit"

    def _draw_3d_view(self, session: "GameSession"):
        if self.raycaster is None:
            return

        map_height = min(24, self.height - 6)
        map_width = self.width

        screen_3d = self.raycaster.render_3d_view(map_height, map_width)

        for y, row in enumerate(screen_3d):
            if y < map_height:
                self._safe_addstr(y, 0, ''.join(row)[:map_width])

        minimap = self.raycaster.render_minimap(20, 10)
        minimap_x = max(0, map_width - 22)
        for y, row in enumerate(minimap):
            if y < 10 and y < map_height:
                self._safe_addstr(y, minimap_x, ''.join(row))

        self._draw_hud(session)

    def _item_glyph(self, item: Item) -> str:
        return ITEM_SYMBOLS.get(item.item_type, "*")

    def _safe_addch(self, y: int, x: int, ch: str, attr: int = 0):
        if 0 <= y < self.height and 0 <= x < self.width:
            try:
                self.stdscr.addch(y, x, ch, attr)
            except curses.error:
                pass

    def _safe_addch_colored(self, y: int, x: int, ch: str, color_pair: int):
        self._safe_addch(y, x, ch, curses.color_pair(color_pair))

    def _safe_addstr(self, y: int, x: int, text: str, attr: int = 0):
        if 0 <= y < self.height:
            try:
                max_len = max(0, self.width - x)
                self.stdscr.addstr(y, x, text[:max_len], attr)
            except curses.error:
                pass
