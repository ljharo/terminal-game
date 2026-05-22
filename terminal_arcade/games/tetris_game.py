#!/usr/bin/env python3
"""
╔╦╗╔═╗╔╦╗╦═╗╦╔═╗
 ║ ║╣  ║ ╠╦╝║╚═╗
 ╩ ╚═╝ ╩ ╩╚═╩╚═╝
Terminal Edition — Neon Arcade
Flechas / WASD  │  Z girar izq  │  X/↑ girar der  │  Espacio caída rápida  │  P pausar  │  Ctrl+C salir
"""

import curses
import random
import time
import sys

# ══════════════════════════════════════════════════════════════
#  PIEZAS  (cada una con rotaciones precalculadas)
# ══════════════════════════════════════════════════════════════

PIECES = {
    "I": {
        "rotations": [
            [(0,0),(0,1),(0,2),(0,3)],
            [(0,0),(1,0),(2,0),(3,0)],
        ],
        "color_id": 1,   # cyan
        "glyph":    "▓",
    },
    "O": {
        "rotations": [
            [(0,0),(0,1),(1,0),(1,1)],
        ],
        "color_id": 2,   # yellow
        "glyph":    "▓",
    },
    "T": {
        "rotations": [
            [(0,1),(1,0),(1,1),(1,2)],
            [(0,0),(1,0),(1,1),(2,0)],
            [(0,0),(0,1),(0,2),(1,1)],
            [(0,1),(1,0),(1,1),(2,1)],
        ],
        "color_id": 3,   # magenta
        "glyph":    "▓",
    },
    "S": {
        "rotations": [
            [(0,1),(0,2),(1,0),(1,1)],
            [(0,0),(1,0),(1,1),(2,1)],
        ],
        "color_id": 4,   # green
        "glyph":    "▓",
    },
    "Z": {
        "rotations": [
            [(0,0),(0,1),(1,1),(1,2)],
            [(0,1),(1,0),(1,1),(2,0)],
        ],
        "color_id": 5,   # red
        "glyph":    "▓",
    },
    "J": {
        "rotations": [
            [(0,0),(1,0),(1,1),(1,2)],
            [(0,0),(0,1),(1,0),(2,0)],
            [(0,0),(0,1),(0,2),(1,2)],
            [(0,1),(1,1),(2,0),(2,1)],
        ],
        "color_id": 6,   # blue
        "glyph":    "▓",
    },
    "L": {
        "rotations": [
            [(0,2),(1,0),(1,1),(1,2)],
            [(0,0),(1,0),(2,0),(2,1)],
            [(0,0),(0,1),(0,2),(1,0)],
            [(0,0),(0,1),(1,1),(2,1)],
        ],
        "color_id": 7,   # orange (white fallback)
        "glyph":    "▓",
    },
}

PIECE_NAMES = list(PIECES.keys())

# ══════════════════════════════════════════════════════════════
#  PUNTUACIÓN  (sistema clásico de Tetris)
# ══════════════════════════════════════════════════════════════

LINE_SCORES = {1: 100, 2: 300, 3: 500, 4: 800}
LEVEL_LINES = 10   # líneas para subir nivel

# ══════════════════════════════════════════════════════════════
#  COLORES
# ══════════════════════════════════════════════════════════════

def setup_colors():
    curses.start_color()
    curses.use_default_colors()
    # Piezas
    curses.init_pair(1, curses.COLOR_CYAN,    -1)   # I
    curses.init_pair(2, curses.COLOR_YELLOW,  -1)   # O
    curses.init_pair(3, curses.COLOR_MAGENTA, -1)   # T
    curses.init_pair(4, curses.COLOR_GREEN,   -1)   # S
    curses.init_pair(5, curses.COLOR_RED,     -1)   # Z
    curses.init_pair(6, curses.COLOR_BLUE,    -1)   # J
    curses.init_pair(7, curses.COLOR_WHITE,   -1)   # L (naranja → blanco)
    # UI
    curses.init_pair(8,  curses.COLOR_WHITE,   -1)  # borde / texto normal
    curses.init_pair(9,  curses.COLOR_YELLOW,  -1)  # títulos
    curses.init_pair(10, curses.COLOR_CYAN,    -1)  # valores HUD
    curses.init_pair(11, curses.COLOR_RED,     -1)  # peligro / game over
    curses.init_pair(12, curses.COLOR_GREEN,   -1)  # línea limpiada (flash)
    curses.init_pair(13, curses.COLOR_BLACK,   curses.COLOR_WHITE)  # ghost
    curses.init_pair(14, curses.COLOR_BLACK,   curses.COLOR_CYAN)   # flash línea

    return {
        "pieces":   [None] + [curses.color_pair(i) | curses.A_BOLD for i in range(1, 8)],
        "border":   curses.color_pair(8),
        "title":    curses.color_pair(9)  | curses.A_BOLD,
        "value":    curses.color_pair(10) | curses.A_BOLD,
        "label":    curses.color_pair(8),
        "danger":   curses.color_pair(11) | curses.A_BOLD,
        "ghost":    curses.color_pair(8)  | curses.A_DIM,
        "flash":    curses.color_pair(14) | curses.A_BOLD,
        "gameover": curses.color_pair(11) | curses.A_BOLD,
        "pause":    curses.color_pair(9)  | curses.A_BOLD,
    }

# ══════════════════════════════════════════════════════════════
#  TABLERO
# ══════════════════════════════════════════════════════════════

BOARD_W = 10
BOARD_H = 20

def empty_board():
    return [[0] * BOARD_W for _ in range(BOARD_H)]

# ══════════════════════════════════════════════════════════════
#  PIEZA ACTIVA
# ══════════════════════════════════════════════════════════════

class ActivePiece:
    def __init__(self, name):
        self.name   = name
        self.data   = PIECES[name]
        self.rot    = 0
        self.row    = 0
        self.col    = BOARD_W // 2 - 1

    def cells(self, rot=None, row=None, col=None):
        r = self.rot if rot is None else rot
        dr = self.row if row is None else row
        dc = self.col if col is None else col
        return [(dr + rr, dc + cc) for rr, cc in self.data["rotations"][r % len(self.data["rotations"])]]

    def color_id(self):
        return self.data["color_id"]

    def glyph(self):
        return self.data["glyph"]


def valid(cells, board):
    for r, c in cells:
        if r < 0 or r >= BOARD_H or c < 0 or c >= BOARD_W:
            return False
        if board[r][c]:
            return False
    return True


def ghost_row(piece, board):
    """Encuentra la fila más baja donde la pieza puede caer."""
    drop = 0
    while valid(piece.cells(row=piece.row + drop + 1), board):
        drop += 1
    return piece.row + drop


def lock_piece(piece, board):
    for r, c in piece.cells():
        if 0 <= r < BOARD_H and 0 <= c < BOARD_W:
            board[r][c] = piece.color_id()


def clear_lines(board):
    """Elimina líneas completas y devuelve cuántas."""
    full = [r for r in range(BOARD_H) if all(board[r])]
    for r in full:
        board.pop(r)
        board.insert(0, [0] * BOARD_W)
    return full   # índices de filas eliminadas (antes del pop)


def random_piece():
    return ActivePiece(random.choice(PIECE_NAMES))

# ══════════════════════════════════════════════════════════════
#  DIBUJO
# ══════════════════════════════════════════════════════════════

# El tablero ocupa columnas 0..BOARD_W*2+1 (cada celda = 2 chars)
# Panel lateral a la derecha

CELL  = "██"   # celda viva (2 chars)
EMPTY = "  "   # celda vacía

BORDER_CHARS = {
    "tl": "╔", "tr": "╗", "bl": "╚", "br": "╝",
    "h":  "═", "v":  "║", "ml": "╠", "mr": "╣",
}

def board_origin(term_rows, term_cols):
    """Calcula dónde centrar el tablero."""
    board_h_px = BOARD_H + 2          # +2 bordes
    board_w_px = BOARD_W * 2 + 2      # +2 bordes, cada celda = 2 chars
    panel_w    = 18
    total_w    = board_w_px + panel_w + 1
    top  = max(0, (term_rows - board_h_px) // 2)
    left = max(0, (term_cols - total_w)   // 2)
    return top, left


def draw_border(stdscr, top, left, colors):
    W = BOARD_W * 2
    H = BOARD_H
    B = colors["border"]
    try:
        stdscr.addstr(top,     left,          BORDER_CHARS["tl"], B)
        stdscr.addstr(top,     left + W + 1,  BORDER_CHARS["tr"], B)
        stdscr.addstr(top+H+1, left,          BORDER_CHARS["bl"], B)
        stdscr.addstr(top+H+1, left + W + 1,  BORDER_CHARS["br"], B)
        for c in range(1, W + 1):
            stdscr.addstr(top,     left + c, BORDER_CHARS["h"], B)
            stdscr.addstr(top+H+1, left + c, BORDER_CHARS["h"], B)
        for r in range(1, H + 1):
            stdscr.addstr(top + r, left,         BORDER_CHARS["v"], B)
            stdscr.addstr(top + r, left + W + 1, BORDER_CHARS["v"], B)
    except curses.error:
        pass


def draw_board(stdscr, board, top, left, colors, flash_rows=None):
    flash_rows = flash_rows or set()
    for r in range(BOARD_H):
        for c in range(BOARD_W):
            scr_r = top + 1 + r
            scr_c = left + 1 + c * 2
            if r in flash_rows:
                try:
                    stdscr.addstr(scr_r, scr_c, CELL, colors["flash"])
                except curses.error:
                    pass
            elif board[r][c]:
                color = colors["pieces"][board[r][c]]
                try:
                    stdscr.addstr(scr_r, scr_c, CELL, color)
                except curses.error:
                    pass
            else:
                try:
                    stdscr.addstr(scr_r, scr_c, "· ", colors["border"] | curses.A_DIM)
                except curses.error:
                    pass


def draw_ghost(stdscr, piece, board, top, left, colors):
    gr = ghost_row(piece, board)
    if gr == piece.row:
        return
    for r, c in piece.cells(row=gr):
        scr_r = top + 1 + r
        scr_c = left + 1 + c * 2
        try:
            stdscr.addstr(scr_r, scr_c, "░░", colors["ghost"])
        except curses.error:
            pass


def draw_piece(stdscr, piece, top, left, colors):
    color = colors["pieces"][piece.color_id()]
    for r, c in piece.cells():
        if r < 0:
            continue
        scr_r = top + 1 + r
        scr_c = left + 1 + c * 2
        try:
            stdscr.addstr(scr_r, scr_c, CELL, color)
        except curses.error:
            pass


def draw_panel(stdscr, next_piece, score, hi_score, level, lines, top, left, colors):
    """Panel lateral derecho."""
    px = left + BOARD_W * 2 + 3   # columna inicio del panel

    def put(row, text, color):
        try:
            stdscr.addstr(top + row, px, text, color)
        except curses.error:
            pass

    # Título
    put(0,  "╔════════════╗", colors["border"])
    put(1,  "║   TETRIS   ║", colors["title"])
    put(2,  "╠════════════╣", colors["border"])

    # Siguiente pieza
    put(3,  "║  SIGUIENTE ║", colors["label"])
    put(4,  "║            ║", colors["border"])
    put(5,  "║            ║", colors["border"])
    put(6,  "║            ║", colors["border"])
    put(7,  "╠════════════╣", colors["border"])

    # Dibujar siguiente pieza en el panel (centrada en rows 4-6)
    np_cells = next_piece.cells(rot=0, row=0, col=0)
    max_r = max(r for r, c in np_cells)
    max_c = max(c for r, c in np_cells)
    offset_r = (3 - max_r) // 2
    offset_c = (5 - max_c * 2) // 2
    ncolor = colors["pieces"][next_piece.color_id()]
    for r, c in np_cells:
        try:
            stdscr.addstr(top + 4 + r + offset_r, px + 1 + c * 2 + offset_c, CELL, ncolor)
        except curses.error:
            pass

    # Estadísticas
    put(8,  "║   PUNTOS   ║", colors["label"])
    put(9,  f"║ {score:>10} ║", colors["value"])
    put(10, "║   RÉCORD   ║", colors["label"])
    put(11, f"║ {hi_score:>10} ║", colors["value"])
    put(12, "╠════════════╣", colors["border"])
    put(13, "║   NIVEL    ║", colors["label"])
    put(14, f"║ {'★' * min(level,12):^10} ║", colors["value"])
    put(15, f"║ {level:^10} ║", colors["title"])
    put(16, "║   LÍNEAS   ║", colors["label"])
    put(17, f"║ {lines:>10} ║", colors["value"])
    put(18, "╠════════════╣", colors["border"])
    put(19, "║ ←→  Mover  ║", colors["label"])
    put(20, "║ ↓   Bajar  ║", colors["label"])
    put(21, "║ SPC Caída  ║", colors["label"])
    put(22, "║ Z/X Girar  ║", colors["label"])
    put(23, "║ P  Pausar  ║", colors["label"])
    put(24, "╚════════════╝", colors["border"])


def draw_pause(stdscr, top, left, colors):
    lines = [
        "╔══════════════════╗",
        "║                  ║",
        "║   ⏸  PAUSADO     ║",
        "║                  ║",
        "║  [P] Continuar   ║",
        "╚══════════════════╝",
    ]
    sr = top + BOARD_H // 2 - 2
    sc = left + BOARD_W - len(lines[0]) // 2 + 1
    for i, line in enumerate(lines):
        try:
            stdscr.addstr(sr + i, sc, line, colors["pause"])
        except curses.error:
            pass


def draw_gameover(stdscr, score, hi_score, top, left, colors):
    lines = [
        "╔════════════════════╗",
        "║                    ║",
        "║   💀  GAME OVER    ║",
        "║                    ║",
        f"║  Puntos: {score:>9}  ║",
        f"║  Récord: {hi_score:>9}  ║",
        "║                    ║",
        "║   [R] Reiniciar    ║",
        "║   [Ctrl+C] Salir   ║",
        "╚════════════════════╝",
    ]
    sr = top + BOARD_H // 2 - len(lines) // 2
    sc = left + 1
    for i, line in enumerate(lines):
        color = colors["gameover"] if i in (0, 2, 9) else colors["pause"]
        try:
            stdscr.addstr(sr + i, sc, line, color)
        except curses.error:
            pass

# ══════════════════════════════════════════════════════════════
#  LOOP PRINCIPAL
# ══════════════════════════════════════════════════════════════

def level_speed(level):
    """Segundos por caída automática según nivel."""
    return max(0.05, 0.5 - (level - 1) * 0.04)


def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(0)

    colors = setup_colors()

    # Estado global
    hi_score   = 0
    game_over  = False
    paused     = False

    def new_game():
        nonlocal game_over, paused
        board      = empty_board()
        piece      = random_piece()
        next_p     = random_piece()
        score      = 0
        level      = 1
        lines_done = 0
        game_over  = False
        paused     = False
        return board, piece, next_p, score, level, lines_done

    board, piece, next_p, score, level, lines_done = new_game()

    fall_timer  = time.time()
    flash_timer = None
    flash_rows_set = set()

    while True:
        now = time.time()

        # ── Input ──────────────────────────────────────────────
        try:
            key = stdscr.getch()
        except curses.error:
            key = -1

        if key in (ord('r'), ord('R')):
            board, piece, next_p, score, level, lines_done = new_game()
            fall_timer = now
            flash_timer = None
            flash_rows_set = set()
            stdscr.clear()
            continue

        if game_over:
            # Solo esperar R o Ctrl+C
            term_rows, term_cols = stdscr.getmaxyx()
            top, left = board_origin(term_rows, term_cols)
            stdscr.erase()
            draw_border(stdscr, top, left, colors)
            draw_board(stdscr, board, top, left, colors)
            draw_panel(stdscr, next_p, score, hi_score, level, lines_done, top, left, colors)
            draw_gameover(stdscr, score, hi_score, top, left, colors)
            stdscr.refresh()
            time.sleep(0.05)
            continue

        if key == ord('p') or key == ord('P'):
            paused = not paused
            fall_timer = now

        if not paused and flash_timer is None:
            if key == curses.KEY_LEFT or key == ord('a') or key == ord('A'):
                new_cells = piece.cells(col=piece.col - 1)
                if valid(new_cells, board):
                    piece.col -= 1

            elif key == curses.KEY_RIGHT or key == ord('d') or key == ord('D'):
                new_cells = piece.cells(col=piece.col + 1)
                if valid(new_cells, board):
                    piece.col += 1

            elif key == curses.KEY_DOWN or key == ord('s') or key == ord('S'):
                new_cells = piece.cells(row=piece.row + 1)
                if valid(new_cells, board):
                    piece.row += 1
                    fall_timer = now

            elif key == ord(' '):
                # Hard drop
                piece.row = ghost_row(piece, board)
                fall_timer = -1  # forzar bloqueo inmediato

            elif key in (ord('x'), ord('X'), curses.KEY_UP):
                # Girar derecha
                new_rot = (piece.rot + 1) % len(piece.data["rotations"])
                for kick in (0, 1, -1, 2, -2):
                    if valid(piece.cells(rot=new_rot, col=piece.col + kick), board):
                        piece.rot = new_rot
                        piece.col += kick
                        break

            elif key in (ord('z'), ord('Z')):
                # Girar izquierda
                new_rot = (piece.rot - 1) % len(piece.data["rotations"])
                for kick in (0, 1, -1, 2, -2):
                    if valid(piece.cells(rot=new_rot, col=piece.col + kick), board):
                        piece.rot = new_rot
                        piece.col += kick
                        break

        # ── Física de caída ────────────────────────────────────
        if not paused and flash_timer is None:
            if now - fall_timer >= level_speed(level):
                fall_timer = now
                new_cells = piece.cells(row=piece.row + 1)
                if valid(new_cells, board):
                    piece.row += 1
                else:
                    # Bloquear pieza
                    lock_piece(piece, board)
                    cleared = clear_lines(board)
                    if cleared:
                        flash_rows_set = set(cleared)
                        flash_timer    = now
                        n = len(cleared)
                        score      += LINE_SCORES.get(n, 0) * level
                        lines_done += n
                        level       = lines_done // LEVEL_LINES + 1
                        hi_score    = max(hi_score, score)
                    # Siguiente pieza
                    piece  = next_p
                    next_p = random_piece()
                    # Game over si la nueva pieza no cabe
                    if not valid(piece.cells(), board):
                        game_over = True
                        hi_score  = max(hi_score, score)

        # ── Flash de línea limpiada ────────────────────────────
        if flash_timer is not None:
            if now - flash_timer > 0.18:
                flash_timer    = None
                flash_rows_set = set()

        # ── Render ─────────────────────────────────────────────
        term_rows, term_cols = stdscr.getmaxyx()
        top, left = board_origin(term_rows, term_cols)

        stdscr.erase()
        draw_border(stdscr, top, left, colors)
        draw_board(stdscr, board, top, left, colors, flash_rows_set)

        if not game_over and flash_timer is None:
            draw_ghost(stdscr, piece, board, top, left, colors)
            draw_piece(stdscr, piece, top, left, colors)

        draw_panel(stdscr, next_p, score, hi_score, level, lines_done, top, left, colors)

        if paused:
            draw_pause(stdscr, top, left, colors)

        stdscr.refresh()
        time.sleep(0.016)   # ~60fps render


# ══════════════════════════════════════════════════════════════
#  ENTRADA
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        print("\n\033[36mGG! El Tetris terminal dice adiós. 🎮\033[0m")
        sys.exit(0)
