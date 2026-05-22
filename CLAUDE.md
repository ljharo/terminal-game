# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Games

```bash
# Install in editable mode (one-time setup)
pip install -e .

# Launch the menu
game
# or
python -m terminal_arcade

# Run a single game directly
python terminal_arcade/games/snake_game.py
```

No external dependencies — only stdlib (`curses`, `random`, `time`, `sys`, `collections.deque`).

## Architecture

The project is a Python package (`terminal_arcade`) with a curses-based launcher menu.

**Entry points:**
- `terminal_arcade/launcher.py:main()` — the `game` CLI command and `python -m terminal_arcade` both call this
- `terminal_arcade/__main__.py` — delegates to `launcher.main()`

**Game registry:**
- `terminal_arcade/games/manifest.py` — `GAMES` list of dicts with `name`, `file`, `description`
- Adding a game: create the `.py` file in `terminal_arcade/games/` and add an entry to `GAMES`
- The launcher spawns games via `subprocess.run([sys.executable, full_path])`, so each game is a self-contained script

**Game file pattern** (consistent across all games):
1. Configuration constants at the top (FPS, glyphs, board dimensions, color pair IDs)
2. Pure game logic — functions or a class with no curses dependency
3. Rendering — `draw_*` functions writing to `stdscr` via `stdscr.addstr(...)` wrapped in `try/except curses.error`
4. `setup_colors()` → returns a `colors` dict used by draw functions
5. Non-blocking input: `stdscr.nodelay(True)` + `stdscr.timeout(0)` + `time.sleep(delay)` for tick rate
6. `curses.wrapper(main)` as entry point with top-level `KeyboardInterrupt` catch
7. Terminal resize: re-query `stdscr.getmaxyx()` each frame, reinitialize state on dimension change

### Per-game notes

- **`game_life.py`**: Purely functional. Grid is `list[list[int]]`. Toroidal boundary wrapping.
- **`snake_game.py`**: Uses a `Snake` class with a `deque` for the body. Speed scales with score.
- **`tetris_game.py`**: Fixed 10×20 board. Pieces defined as pre-calculated rotation lists in `PIECES` dict. Wall-kick on rotation. Ghost piece rendered with `░░`. Line-clear flash effect with timer.
- **`2048.py`**: 4×4 grid. All 4 directions reduced to a single `slide_row` by rotating the grid. Merge flash via `merged_set`.
- **`minesweeper.py`**: Classic minesweeper on a configurable grid.
- **`pong.py`**: Player vs AI; first to 7 wins.
