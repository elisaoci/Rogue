import curses

from datalayer.leaderboard import load_leaderboard, record_attempt
from datalayer.save_load import clear_session, has_session, load_session, save_session
from game import GameSession
from presentation.input_handler import InputHandler
from presentation.renderer import Renderer


def _handle_inventory(renderer: Renderer, session: GameSession, item_type: str):
    allow_unequip = item_type == "weapon" and session.player.current_weapon is not None
    items = session.player.backpack.list_items(item_type)
    choice = renderer.prompt_inventory_choice(item_type, items, allow_unequip)
    if choice is None:
        return
    index = None if choice == -1 else choice
    success = session.use_item(item_type, index)
    if not success:
        session.log("Не удалось использовать предмет.")


def run(stdscr):
    renderer = Renderer(stdscr)
    input_handler = InputHandler()

    session: GameSession | None = None
    while session is None:
        if has_session():
            decision = renderer.prompt_resume(True)
            if decision == "continue":
                try:
                    data = load_session()
                    if data:
                        session = GameSession(state=data)
                    else:
                        clear_session()
                        session = GameSession()
                except Exception as e:
                    clear_session()
                    session = GameSession()
            elif decision == "leaderboard":
                renderer.show_statistics(load_leaderboard(), None)
            else:
                clear_session()
                session = GameSession()
        else:
            session = GameSession()

    while True:
        renderer.draw(session)
        action = input_handler.get_action(stdscr)
        if not action:
            continue

        if action == "quit":
            save_session(session.to_dict())
            break
        
        if action == "toggle_3d":
            if renderer.raycaster:
                renderer.raycaster.toggle_3d_mode()
            continue
        
        if renderer.raycaster and renderer.raycaster.is_3d_mode:
            if action in {"w", "a", "s", "d"}:
                key_code = ord(action)
                if renderer.raycaster.handle_3d_input(key_code):
                    save_session(session.to_dict())
                    continue
        
        if action == "use_weapon":
            _handle_inventory(renderer, session, "weapon")
            save_session(session.to_dict())
            continue
        if action == "use_food":
            _handle_inventory(renderer, session, "food")
            save_session(session.to_dict())
            continue
        if action == "use_elixir":
            _handle_inventory(renderer, session, "elixir")
            save_session(session.to_dict())
            continue
        if action == "use_scroll":
            _handle_inventory(renderer, session, "scroll")
            save_session(session.to_dict())
            continue
        if action == "show_stats":
            renderer.show_statistics(load_leaderboard(), session.stats)
            continue

        result = session.perform_turn(action)
        save_session(session.to_dict())
        
        if result == "victory":
            record_attempt(session.leaderboard_entry("victory"))
            clear_session()
            choice = renderer.game_over(session, True)
            if choice == "new":
                session = GameSession()
                continue
            else:
                break

        elif result == "game_over":
            record_attempt(session.leaderboard_entry("defeat"))
            clear_session()
            choice = renderer.game_over(session, False)
            if choice == "new":
                session = GameSession()
                continue
            else:
                break

if __name__ == "__main__":
    curses.wrapper(run)