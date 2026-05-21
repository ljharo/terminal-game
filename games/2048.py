#!/usr/bin/env python3
"""
████████╗ ██████╗ ██╗  ██╗ █████╗
╚══██╔══╝██╔═████╗██║  ██║██╔══██╗
   ██║   ██║██╔██║███████║╚█████╔╝
   ██║   ████╔╝██║╚════██║██╔══██╗
   ██║   ╚██████╔╝     ██║╚█████╔╝
   ╚═╝    ╚═════╝      ╚═╝ ╚════╝
Terminal Edition — Neon Style
Flechas / WASD mover │ R reiniciar │ Ctrl+C salir
"""

import curses
import random
import sys
import time
import copy

# ══════════════════════════════════════════════════════════════
#  CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════

GRID_SIZE   = 4
CELL_W      = 8    # ancho de cada celda en chars
CELL_H      = 3    # alto de cada celda en líneas
WIN_TILE    = 2048

# Colores por valor de tile (color_pair_id)
TILE_COLORS = {
    0:    1,   # vacío
    2:    2,
    4:    3,
    8:    4,
    16:   5,
    32:   6,
    64:   7,
    128:  8,
    256:  9,
    512:  10,
    1024: 11,
    2048: 12,
}

# ══════════════════════════════════════════════════════════════
#  COLORES
# ══════════════════════════════════════════════════════════════

def setup_colors():
    curses.start_color()
    curses.use_default_colors()

    # Tiles: (fg, bg)
    pairs = [
        (curses.COLOR_BLACK,   -1),                          # 1  vacío
        (curses.COLOR_WHITE,   curses.COLOR_BLACK),          # 2  → 2
        (curses.COLOR_BLACK,   curses.COLOR_WHITE),          # 3  → 4
        (curses.COLOR_WHITE,   curses.COLOR_RED),            # 4  → 8
        (curses.COLOR_BLACK,   curses.COLOR_RED),            # 5  → 16
        (curses.COLOR_WHITE,   curses.COLOR_MAGENTA),        # 6  → 32
        (curses.COLOR_BLACK,   curses.COLOR_MAGENTA),        # 7  → 64
        (curses.COLOR_WHITE,   curses.COLOR_BLUE),           # 8  → 128
        (curses.COLOR_BLACK,   curses.COLOR_CYAN),           # 9  → 256
        (curses.COLOR_WHITE,   curses.COLOR_GREEN),          # 10 → 512
        (curses.COLOR_BLACK,   curses.COLOR_YELLOW),         # 11 → 1024
        (curses.COLOR_BLACK,   curses.COLOR_WHITE),          # 12 → 2048 (override bold)
    ]
    for i, (fg, bg) in enumerate(pairs, start=1):
        curses.init_pair(i, fg, bg)

    # UI
    curses.init_pair(13, curses.COLOR_YELLOW,  -1)   # título
    curses.init_pair(14, curses.COLOR_CYAN,    -1)   # valores
    curses.init_pair(15, curses.COLOR_WHITE,   -1)   # borde / texto
    curses.init_pair(16, curses.COLOR_GREEN,   -1)   # win
    curses.init_pair(17, curses.COLOR_RED,     -1)   # game over
    curses.init_pair(18, curses.COLOR_MAGENTA, -1)   # merged flash
    curses.init_pair(19, curses.COLOR_BLACK,   curses.COLOR_GREEN)   # WIN tile bg

    def pc(n, bold=False, dim=False):
        a = curses.color_pair(n)
        if bold: a |= curses.A_BOLD
        if dim:  a |= curses.A_DIM
        return a

    return {
        "tiles":    {v: pc(TILE_COLORS.get(v, 12), bold=True) for v in list(TILE_COLORS.keys()) + [4096, 8192]},
        "empty":    pc(1, dim=True),
        "border":   pc(15),
        "title":    pc(13, bold=True),
        "value":    pc(14, bold=True),
        "label":    pc(15),
        "win":      pc(16, bold=True),
        "gameover": pc(17, bold=True),
        "merged":   pc(18, bold=True),
        "wintile":  pc(19, bold=True),
    }

# ══════════════════════════════════════════════════════════════
#  LÓGICA DEL JUEGO
# ══════════════════════════════════════════════════════════════

def new_grid():
    g = [[0]*GRID_SIZE for _ in range(GRID_SIZE)]
    add_tile(g)
    add_tile(g)
    return g

def empty_cells(grid):
    return [(r, c) for r in range(GRID_SIZE) for c in range(GRID_SIZE) if grid[r][c] == 0]

def add_tile(grid):
    cells = empty_cells(grid)
    if not cells:
        return
    r, c = random.choice(cells)
    grid[r][c] = 4 if random.random() < 0.1 else 2

def compress(row):
    """Mueve todos los valores no-cero a la izquierda."""
    return [v for v in row if v != 0]

def merge(row):
    """Combina pares iguales y devuelve (nueva_fila, puntos, merged_positions)."""
    pts     = 0
    merged  = []   # posiciones donde hubo merge
    i = 0
    result = []
    while i < len(row):
        if i + 1 < len(row) and row[i] == row[i+1]:
            val = row[i] * 2
            result.append(val)
            pts += val
            merged.append(len(result) - 1)
            i += 2
        else:
            result.append(row[i])
            i += 1
    return result, pts, merged

def slide_row(row):
    """Desliza y fusiona una fila hacia la izquierda."""
    r = compress(row)
    r, pts, merged = merge(r)
    r += [0] * (GRID_SIZE - len(r))
    return r, pts, merged

def move(grid, direction):
    """direction: 'L','R','U','D'. Devuelve (new_grid, score_delta, moved, merged_cells)."""
    rotations = {'L': 0, 'R': 2, 'U': 1, 'D': 3}
    k = rotations[direction]

    # Rotar para que siempre deslicemos a la izquierda
    g = rotate_grid(grid, k)
    new_g   = []
    total   = 0
    any_merged = []
    changed = False

    for ri, row in enumerate(g):
        new_row, pts, merged = slide_row(row)
        new_g.append(new_row)
        total += pts
        for ci in merged:
            any_merged.append((ri, ci))
        if new_row != row:
            changed = True

    # Rotar de vuelta
    result = rotate_grid(new_g, (4 - k) % 4)
    # Convertir merged coords de vuelta
    merged_real = []
    for (ri, ci) in any_merged:
        r2, c2 = rotate_coord(ri, ci, (4 - k) % 4)
        merged_real.append((r2, c2))

    return result, total, changed, merged_real

def rotate_grid(grid, times):
    g = [row[:] for row in grid]
    for _ in range(times):
        g = [list(row) for row in zip(*g[::-1])]
    return g

def rotate_coord(r, c, times):
    n = GRID_SIZE
    for _ in range(times):
        r, c = c, n - 1 - r
    return r, c

def has_moves(grid):
    if empty_cells(grid):
        return True
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            v = grid[r][c]
            if c+1 < GRID_SIZE and grid[r][c+1] == v:
                return True
            if r+1 < GRID_SIZE and grid[r+1][c] == v:
                return True
    return False

def has_won(grid):
    return any(grid[r][c] >= WIN_TILE for r in range(GRID_SIZE) for c in range(GRID_SIZE))

# ══════════════════════════════════════════════════════════════
#  DIBUJO
# ══════════════════════════════════════════════════════════════

# Tablero: 4 celdas × CELL_W + 5 separadores (│)
# Cada celda CELL_H líneas + 1 separador horizontal

BOARD_PX_W = GRID_SIZE * CELL_W + GRID_SIZE + 1
BOARD_PX_H = GRID_SIZE * CELL_H + GRID_SIZE + 1


def board_origin(term_rows, term_cols):
    panel_w = 22
    total_w = BOARD_PX_W + panel_w + 2
    top  = max(1, (term_rows - BOARD_PX_H - 4) // 2)
    left = max(0, (term_cols - total_w) // 2)
    return top, left


def tile_color(val, colors):
    if val == 0:
        return colors["empty"]
    if val >= WIN_TILE:
        return colors["wintile"]
    return colors["tiles"].get(val, colors["tiles"][2048])


def draw_board(stdscr, grid, merged_set, top, left, colors):
    """Dibuja la cuadrícula completa."""
    sep_h = "─" * CELL_W
    sep_row_mid = "┼".join([sep_h] * GRID_SIZE)
    sep_row_top = "┬".join([sep_h] * GRID_SIZE)
    sep_row_bot = "┴".join([sep_h] * GRID_SIZE)

    for r in range(GRID_SIZE):
        # Separador horizontal
        if r == 0:
            line = "┌" + sep_row_top + "┐"
        else:
            line = "├" + sep_row_mid + "┤"
        try:
            stdscr.addstr(top + r * (CELL_H + 1), left, line, colors["border"])
        except curses.error:
            pass

        # Filas de la celda
        for ch in range(CELL_H):
            row_str_parts = []
            for c in range(GRID_SIZE):
                val   = grid[r][c]
                color = tile_color(val, colors)
                is_merged = (r, c) in merged_set

                if ch == CELL_H // 2:
                    # Fila del número
                    if val == 0:
                        text = " " * CELL_W
                    else:
                        s = str(val)
                        text = s.center(CELL_W)
                    row_str_parts.append((text, color, is_merged))
                else:
                    row_str_parts.append((" " * CELL_W, color, False))

            scr_r = top + r * (CELL_H + 1) + 1 + ch
            try:
                stdscr.addstr(scr_r, left, "│", colors["border"])
            except curses.error:
                pass
            scr_c = left + 1
            for text, color, flash in row_str_parts:
                attr = colors["merged"] if flash else color
                try:
                    stdscr.addstr(scr_r, scr_c, text, attr)
                    stdscr.addstr(scr_r, scr_c + CELL_W, "│", colors["border"])
                except curses.error:
                    pass
                scr_c += CELL_W + 1

    # Fila inferior
    bot_line = "└" + sep_row_bot + "┘"
    try:
        stdscr.addstr(top + GRID_SIZE * (CELL_H + 1), left, bot_line, colors["border"])
    except curses.error:
        pass


def draw_panel(stdscr, score, hi_score, moves, top, left, colors, won, game_over):
    px = left + BOARD_PX_W + 2

    def put(row, text, color):
        try:
            stdscr.addstr(top + row, px, text, color)
        except curses.error:
            pass

    put(0,  "╔════════════════╗", colors["border"])
    put(1,  "║     2 0 4 8    ║", colors["title"])
    put(2,  "╠════════════════╣", colors["border"])
    put(3,  "║   PUNTUACIÓN   ║", colors["label"])
    put(4,  f"║ {score:>14} ║", colors["value"])
    put(5,  "║    RÉCORD      ║", colors["label"])
    put(6,  f"║ {hi_score:>14} ║", colors["value"])
    put(7,  "╠════════════════╣", colors["border"])
    put(8,  "║   MOVIMIENTOS  ║", colors["label"])
    put(9,  f"║ {moves:>14} ║", colors["value"])
    put(10, "╠════════════════╣", colors["border"])

    if won:
        put(11, "║  🏆 ¡GANASTE!  ║", colors["win"])
        put(12, "║  Sigue jugando ║", colors["label"])
    elif game_over:
        put(11, "║  💀 GAME OVER  ║", colors["gameover"])
        put(12, "║  [R] Reinicia  ║", colors["label"])
    else:
        put(11, "║                ║", colors["border"])
        put(12, "║                ║", colors["border"])

    put(13, "╠════════════════╣", colors["border"])
    put(14, "║ ↑↓←→  Mover    ║", colors["label"])
    put(15, "║ WASD  Mover    ║", colors["label"])
    put(16, "║ R     Reiniciar║", colors["label"])
    put(17, "║ Ctrl+C Salir   ║", colors["label"])
    put(18, "╚════════════════╝", colors["border"])


def draw_title(stdscr, top, left, colors):
    try:
        stdscr.addstr(top - 2, left,
            "╔══ 2048 ══╗  Llega al tile  \033[33m2048\033[0m  para ganar",
            colors["title"])
    except curses.error:
        try:
            stdscr.addstr(top - 2, left, "[ 2048 — Terminal Edition ]", colors["title"])
        except curses.error:
            pass


# ══════════════════════════════════════════════════════════════
#  LOOP PRINCIPAL
# ══════════════════════════════════════════════════════════════

def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(0)

    colors    = setup_colors()
    hi_score  = 0
    won_shown = False   # mostrar mensaje de victoria solo una vez

    def new_game():
        nonlocal won_shown
        won_shown = False
        return new_grid(), 0, 0, False, False

    grid, score, moves, game_over, won = new_game()
    merged_set   = set()
    flash_until  = 0

    DIR_MAP = {
        curses.KEY_LEFT:  'L', ord('a'): 'L', ord('A'): 'L',
        curses.KEY_RIGHT: 'R', ord('d'): 'R', ord('D'): 'R',
        curses.KEY_UP:    'U', ord('w'): 'U', ord('W'): 'U',
        curses.KEY_DOWN:  'D', ord('s'): 'D', ord('S'): 'D',
    }

    while True:
        now = time.time()

        # ── Input ──────────────────────────────────────────────
        try:
            key = stdscr.getch()
        except curses.error:
            key = -1

        if key in (ord('r'), ord('R')):
            grid, score, moves, game_over, won = new_game()
            merged_set  = set()
            flash_until = 0
            stdscr.clear()

        elif key in DIR_MAP and not game_over:
            direction = DIR_MAP[key]
            new_grid_, delta, changed, merged_cells = move(grid, direction)
            if changed:
                grid        = new_grid_
                score      += delta
                moves      += 1
                hi_score    = max(hi_score, score)
                add_tile(grid)
                merged_set  = set(merged_cells)
                flash_until = now + 0.25

                if not won_shown and has_won(grid):
                    won       = True
                    won_shown = True

                if not has_moves(grid):
                    game_over = True

        # Limpiar flash
        if now > flash_until:
            merged_set = set()

        # ── Render ─────────────────────────────────────────────
        term_rows, term_cols = stdscr.getmaxyx()
        top, left = board_origin(term_rows, term_cols)

        stdscr.erase()
        draw_title(stdscr, top, left, colors)
        draw_board(stdscr, grid, merged_set, top, left, colors)
        draw_panel(stdscr, score, hi_score, moves, top, left, colors, won, game_over)
        stdscr.refresh()

        time.sleep(0.016)


# ══════════════════════════════════════════════════════════════
#  ENTRADA
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        print("\n\033[33m¡Hasta la próxima! El 2048 te espera. 🎯\033[0m")
        sys.exit(0)
