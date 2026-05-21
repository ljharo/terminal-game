wiu# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Games

Each game is a standalone Python 3 script using only the standard library:

```bash
python3 game_life.py    # Conway's Game of Life
python3 snake_game.py   # Snake
python3 tetris_game.py  # Tetris
python3 2048.py         # 2048
```

No dependencies to install. Requires a terminal with color support for the best experience.

## Architecture

All four games share the same structural pattern:

- **Single-file, no external dependencies** — only `curses`, `random`, `time`, `sys` (plus `collections.deque` in snake).
- **`curses.wrapper(main)`** as the entry point, with `KeyboardInterrupt` caught at the top level for a clean exit.
- **Three-layer structure** within each file:
  1. **Configuration constants** at the top (FPS, character glyphs, board dimensions, color pair IDs).
  2. **Game logic** — pure functions or a class (e.g., `Snake`) with no curses dependency.
  3. **Rendering** — `draw_*` functions that take `stdscr` and write via `stdscr.addstr(...)` wrapped in `try/except curses.error` to silently handle terminal overflow.
- **`setup_colors()`** initializes curses color pairs and returns a `colors` dict used by all draw functions.
- **Non-blocking input loop**: `stdscr.nodelay(True)` + `stdscr.timeout(0)` + `time.sleep(delay)` controls the game tick rate. Input is read via `stdscr.getch()` each frame.
- **Terminal resize** is handled by re-querying `stdscr.getmaxyx()` each frame and reinitializing the game state when dimensions change.

### Per-game notes

- **`game_life.py`**: Purely functional. Grid is `list[list[int]]`. Toroidal boundary wrapping.
- **`snake_game.py`**: Uses a `Snake` class with a `deque` for the body. Speed scales with score.
- **`tetris_game.py`**: Fixed 10x20 board (`BOARD_W`/`BOARD_H`). Pieces defined as pre-calculated rotation lists in `PIECES` dict. Wall-kick logic on rotation. Ghost piece rendered with `░░`. Line-clear flash effect with timer.
- **`2048.py`**: 4x4 grid. Movement uses grid rotation to reduce all 4 directions to a single left-slide implementation (`slide_row`). Merge flash highlighting via `merged_set`.
