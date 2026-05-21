#!/usr/bin/env python3
import curses
import importlib.util
import os
import subprocess
import sys

LAUNCHER_DIR = os.path.dirname(os.path.abspath(__file__))
GAMES_DIR    = os.path.join(LAUNCHER_DIR, "games")

# Color pair IDs
C_BORDER = 1
C_TITLE  = 2
C_SELECT = 3
C_HINT   = 4
C_ERROR  = 5


def load_games():
    manifest = os.path.join(GAMES_DIR, "manifest.py")
    if not os.path.isfile(manifest):
        return []
    spec = importlib.util.spec_from_file_location("manifest", manifest)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.GAMES


def setup_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(C_BORDER, curses.COLOR_CYAN,   -1)
    curses.init_pair(C_TITLE,  curses.COLOR_YELLOW, -1)
    curses.init_pair(C_SELECT, curses.COLOR_BLACK,  curses.COLOR_CYAN)
    curses.init_pair(C_HINT,   curses.COLOR_GREEN,  -1)
    curses.init_pair(C_ERROR,  curses.COLOR_RED,    -1)


def draw_menu(stdscr, games, selected):
    stdscr.erase()
    rows, cols = stdscr.getmaxyx()

    box_w = 52
    box_h = len(games) + 7

    if rows < box_h + 2 or cols < box_w + 2:
        msg = f"Terminal too small ({cols}x{rows}). Need {box_w + 2}x{box_h + 2}."
        try:
            stdscr.addstr(0, 0, msg, curses.color_pair(C_ERROR) | curses.A_BOLD)
        except curses.error:
            pass
        stdscr.refresh()
        return

    box_y = (rows - box_h) // 2
    box_x = (cols - box_w) // 2
    inner = box_w - 2

    border = curses.color_pair(C_BORDER)
    title  = curses.color_pair(C_TITLE)  | curses.A_BOLD
    hint   = curses.color_pair(C_HINT)

    def put(y, x, text, attr=0):
        try:
            stdscr.addstr(y, x, text, attr)
        except curses.error:
            pass

    # Top border + title
    put(box_y,     box_x, "+" + "=" * inner + "+", border)
    t = "TERMINAL ARCADE"
    pad_l = (inner - len(t)) // 2
    pad_r = inner - len(t) - pad_l
    put(box_y + 1, box_x, "|" + " " * pad_l + t + " " * pad_r + "|", title)
    put(box_y + 2, box_x, "+" + "-" * inner + "+", border)

    # Game entries
    for i, g in enumerate(games):
        label = f"  [{i + 1}]  {g['name']:<14}  {g['description']}"
        label = label[:inner].ljust(inner)
        gy    = box_y + 3 + i
        if i == selected:
            put(gy, box_x,         "|", border)
            put(gy, box_x + 1,     label, curses.color_pair(C_SELECT) | curses.A_BOLD)
            put(gy, box_x + box_w - 1, "|", border)
        else:
            put(gy, box_x, "|" + label + "|", border)

    # Separator + hints + bottom
    sep = box_y + 3 + len(games)
    put(sep,     box_x, "+" + "-" * inner + "+", border)
    put(sep + 1, box_x, "|" + "  Up/Down: navigate   Enter/Num: launch".ljust(inner) + "|", hint)
    put(sep + 2, box_x, "|" + "  Q / Ctrl+C: quit".ljust(inner) + "|", hint)
    put(sep + 3, box_x, "+" + "=" * inner + "+", border)

    stdscr.refresh()


def menu_loop(stdscr):
    setup_colors()
    curses.curs_set(0)
    stdscr.keypad(True)

    games    = load_games()
    selected = 0

    while True:
        draw_menu(stdscr, games, selected)
        key = stdscr.getch()

        if key in (ord('q'), ord('Q')):
            return None
        elif key == curses.KEY_UP:
            selected = (selected - 1) % len(games)
        elif key == curses.KEY_DOWN:
            selected = (selected + 1) % len(games)
        elif key in (curses.KEY_ENTER, ord('\n'), ord('\r')):
            return selected
        elif ord('1') <= key <= ord('0') + len(games):
            return key - ord('1')


def launch_game(game_file):
    full_path = os.path.join(GAMES_DIR, game_file)
    if not os.path.isfile(full_path):
        return f"File not found: {full_path}"
    try:
        subprocess.run([sys.executable, full_path], cwd=GAMES_DIR)
    except KeyboardInterrupt:
        pass
    return None


def main():
    while True:
        try:
            choice = curses.wrapper(menu_loop)
        except KeyboardInterrupt:
            break

        if choice is None:
            break

        games = load_games()
        error = launch_game(games[choice]["file"])
        if error:
            print(error, file=sys.stderr)
            input("Press Enter to return to menu...")


if __name__ == "__main__":
    main()
