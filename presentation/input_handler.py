import curses


class InputHandler:
    def __init__(self):
        self.mapping = {
            curses.KEY_UP: "w",
            curses.KEY_DOWN: "s",
            curses.KEY_LEFT: "a",
            curses.KEY_RIGHT: "d",
        }
        self.button_actions = {
            "q": "quit",
            "h": "use_weapon",
            "j": "use_food",
            "k": "use_elixir",
            "e": "use_scroll",
            "t": "show_stats",
            "\t": "toggle_3d",
        }

    def get_action(self, stdscr) -> str:
        key = stdscr.getch()
        if key == -1:
            return ""
        
        if key == ord('\t') or key == 9:
            return "toggle_3d"
        
        if key in self.mapping:
            return self.mapping[key]
        if 0 <= key <= 255:
            ch = chr(key).lower()
            if ch in {"w", "a", "s", "d"}:
                return ch
            return self.button_actions.get(ch, "")
        return ""
