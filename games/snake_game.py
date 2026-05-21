#!/usr/bin/env python3
"""
Snake — Terminal Edition
Flechas o WASD para moverse | Espacio para pausar | R para reiniciar | Ctrl+C para salir
"""

import curses
import random
import time
import sys
from collections import deque

# ── Configuración ──────────────────────────────────────────────
FPS            = 10
HEAD_CHAR      = "█"
BODY_CHAR      = "█"
FOOD_CHAR      = "●"
BORDER_H       = "─"
BORDER_V       = "│"
CORNER_TL      = "╭"
CORNER_TR      = "╮"
CORNER_BL      = "╰"
CORNER_BR      = "╯"

# Direcciones (dy, dx)
UP    = (-1,  0)
DOWN  = ( 1,  0)
LEFT  = ( 0, -1)
RIGHT = ( 0,  1)

OPPOSITES = {UP: DOWN, DOWN: UP, LEFT: RIGHT, RIGHT: LEFT}


# ── Colores ────────────────────────────────────────────────────

def setup_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN,   -1)  # cuerpo serpiente
    curses.init_pair(2, curses.COLOR_WHITE,   -1)  # cabeza
    curses.init_pair(3, curses.COLOR_RED,     -1)  # comida
    curses.init_pair(4, curses.COLOR_YELLOW,  -1)  # HUD / borde
    curses.init_pair(5, curses.COLOR_CYAN,    -1)  # título
    curses.init_pair(6, curses.COLOR_MAGENTA, -1)  # pausa / game over
    return {
        "head":       curses.color_pair(2) | curses.A_BOLD,
        "body":       curses.color_pair(1) | curses.A_BOLD,
        "food":       curses.color_pair(3) | curses.A_BOLD,
        "border":     curses.color_pair(4),
        "title":      curses.color_pair(5) | curses.A_BOLD,
        "hud":        curses.color_pair(4),
        "highlight":  curses.color_pair(6) | curses.A_BOLD,
        "gameover":   curses.color_pair(3) | curses.A_BOLD,
    }


# ── Estado del juego ───────────────────────────────────────────

class Snake:
    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.reset()

    def reset(self):
        mid_r = self.rows // 2
        mid_c = self.cols // 2
        # Empieza con longitud 3
        self.body      = deque([(mid_r, mid_c), (mid_r, mid_c - 1), (mid_r, mid_c - 2)])
        self.direction = RIGHT
        self.grow      = False
        self.alive     = True
        self.score     = 0
        self.hi_score  = getattr(self, 'hi_score', 0)
        self.food      = self._place_food()
        self.steps     = 0

    def _place_food(self):
        body_set = set(self.body)
        while True:
            r = random.randint(0, self.rows - 1)
            c = random.randint(0, self.cols - 1)
            if (r, c) not in body_set:
                return (r, c)

    def set_direction(self, new_dir):
        # No permitir ir en dirección opuesta
        if new_dir != OPPOSITES.get(self.direction):
            self.direction = new_dir

    def step(self):
        if not self.alive:
            return

        head = self.body[0]
        dr, dc = self.direction
        new_head = (head[0] + dr, head[1] + dc)

        # Colisión con bordes
        r, c = new_head
        if not (0 <= r < self.rows and 0 <= c < self.cols):
            self.alive = False
            return

        # Colisión con sí misma
        if new_head in set(self.body):
            self.alive = False
            return

        self.body.appendleft(new_head)
        self.steps += 1

        if new_head == self.food:
            self.score += 10 + len(self.body) // 5
            self.hi_score = max(self.hi_score, self.score)
            self.food = self._place_food()
        else:
            self.body.pop()


# ── Dibujo ─────────────────────────────────────────────────────

def draw_border(stdscr, top, left, rows, cols, colors):
    """Dibuja un borde alrededor del área de juego."""
    bottom = top + rows + 1
    right  = left + cols + 1
    C = colors["border"]
    try:
        stdscr.addstr(top,    left,  CORNER_TL, C)
        stdscr.addstr(top,    right, CORNER_TR, C)
        stdscr.addstr(bottom, left,  CORNER_BL, C)
        stdscr.addstr(bottom, right, CORNER_BR, C)
        for c in range(left + 1, right):
            stdscr.addstr(top,    c, BORDER_H, C)
            stdscr.addstr(bottom, c, BORDER_H, C)
        for r in range(top + 1, bottom):
            stdscr.addstr(r, left,  BORDER_V, C)
            stdscr.addstr(r, right, BORDER_V, C)
    except curses.error:
        pass


def draw_game(stdscr, snake, top, left, colors):
    """Dibuja la serpiente y la comida."""
    # Comida
    fr, fc = snake.food
    try:
        stdscr.addstr(top + 1 + fr, left + 1 + fc, FOOD_CHAR, colors["food"])
    except curses.error:
        pass

    # Cuerpo
    for i, (r, c) in enumerate(snake.body):
        char  = HEAD_CHAR if i == 0 else BODY_CHAR
        color = colors["head"] if i == 0 else colors["body"]
        try:
            stdscr.addstr(top + 1 + r, left + 1 + c, char, color)
        except curses.error:
            pass


def draw_hud(stdscr, snake, paused, term_rows, term_cols, colors):
    """Barra superior con título y puntuación."""
    title = " 🐍 SNAKE "
    score_str  = f" Puntos: {snake.score:>5} "
    hi_str     = f" Récord: {snake.hi_score:>5} "
    len_str    = f" Largo: {len(snake.body):>4} "
    ctrl_str   = " [WASD/↑↓←→] Mover  [Espacio] Pausar  [R] Reiniciar  [Ctrl+C] Salir "

    # Línea 0: título + puntos
    try:
        stdscr.addstr(0, 0, " " * term_cols, colors["hud"])
        stdscr.addstr(0, 1, title,     colors["title"])
        stdscr.addstr(0, 1 + len(title) + 1, score_str, colors["hud"])
        stdscr.addstr(0, 1 + len(title) + 1 + len(score_str) + 1, hi_str, colors["hud"])
        stdscr.addstr(0, 1 + len(title) + 1 + len(score_str) + 1 + len(hi_str) + 1, len_str, colors["hud"])

        # Línea inferior: controles
        bottom = term_rows - 1
        stdscr.addstr(bottom, 0, " " * (term_cols - 1), colors["hud"])
        stdscr.addstr(bottom, 1, ctrl_str[:term_cols - 2], colors["hud"])

        if paused:
            pause_msg = "  ⏸  PAUSADO  "
            stdscr.addstr(bottom, term_cols - len(pause_msg) - 1, pause_msg, colors["highlight"])
    except curses.error:
        pass


def draw_gameover(stdscr, snake, game_rows, game_cols, top, left, colors):
    """Pantalla de game over centrada sobre el área de juego."""
    lines = [
        "",
        "  ╔══════════════════════╗  ",
        "  ║    💀  GAME OVER  💀   ║  ",
        f"  ║   Puntos: {snake.score:>7}     ║  ",
        f"  ║   Récord: {snake.hi_score:>7}     ║  ",
        "  ║                      ║  ",
        "  ║  [R] Reiniciar       ║  ",
        "  ║  [Ctrl+C] Salir      ║  ",
        "  ╚══════════════════════╝  ",
        "",
    ]
    start_r = top + 1 + (game_rows - len(lines)) // 2
    start_c = left + 1 + (game_cols - len(lines[1])) // 2

    for i, line in enumerate(lines):
        color = colors["gameover"] if i in (1, 2, 8) else colors["highlight"]
        try:
            stdscr.addstr(start_r + i, start_c, line, color)
        except curses.error:
            pass


# ── Loop principal ─────────────────────────────────────────────

def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(0)

    colors = setup_colors() if curses.has_colors() else {
        k: curses.A_BOLD if "head" in k or "food" in k else curses.A_NORMAL
        for k in ("head","body","food","border","title","hud","highlight","gameover")
    }

    term_rows, term_cols = stdscr.getmaxyx()

    # Área de juego: dentro del borde, debajo del HUD, encima del footer
    # Fila 0 = HUD, fila 1 = borde top, filas 2..N-3 = juego, fila N-2 = borde bot, fila N-1 = footer
    game_top  = 1           # donde va el borde superior
    game_left = 0           # borde izquierdo
    game_rows = term_rows - 4   # filas jugables
    game_cols = term_cols - 2   # cols jugables (borde izq + der)

    snake  = Snake(game_rows, game_cols)
    paused = False
    delay  = 1.0 / FPS

    while True:
        # ── Input ──────────────────────────────────────────────
        try:
            key = stdscr.getch()
        except curses.error:
            key = -1

        if key in (ord('q'), ord('Q')):
            break
        elif key == ord(' '):
            if snake.alive:
                paused = not paused
        elif key in (ord('r'), ord('R')):
            new_rows, new_cols = stdscr.getmaxyx()
            if new_rows != term_rows or new_cols != term_cols:
                term_rows, term_cols = new_rows, new_cols
                game_rows = term_rows - 4
                game_cols = term_cols - 2
            snake.rows = game_rows
            snake.cols = game_cols
            snake.reset()
            paused = False
            stdscr.clear()

        # Dirección
        if snake.alive and not paused:
            if key in (curses.KEY_UP,    ord('w'), ord('W')): snake.set_direction(UP)
            elif key in (curses.KEY_DOWN,  ord('s'), ord('S')): snake.set_direction(DOWN)
            elif key in (curses.KEY_LEFT,  ord('a'), ord('A')): snake.set_direction(LEFT)
            elif key in (curses.KEY_RIGHT, ord('d'), ord('D')): snake.set_direction(RIGHT)

        # ── Resize ─────────────────────────────────────────────
        new_rows, new_cols = stdscr.getmaxyx()
        if new_rows != term_rows or new_cols != term_cols:
            term_rows, term_cols = new_rows, new_cols
            game_rows = term_rows - 4
            game_cols = term_cols - 2
            snake.rows = game_rows
            snake.cols = game_cols
            snake.reset()
            stdscr.clear()

        # ── Actualizar ─────────────────────────────────────────
        if snake.alive and not paused:
            snake.step()
            # Velocidad progresiva según puntuación
            speed = min(FPS + snake.score // 30, 25)
            delay = 1.0 / speed

        # ── Dibujar ────────────────────────────────────────────
        stdscr.erase()
        draw_border(stdscr, game_top, game_left, game_rows, game_cols, colors)
        draw_game(stdscr, snake, game_top, game_left, colors)
        draw_hud(stdscr, snake, paused, term_rows, term_cols, colors)

        if not snake.alive:
            draw_gameover(stdscr, snake, game_rows, game_cols, game_top, game_left, colors)

        stdscr.refresh()
        time.sleep(delay)


# ── Entrada ────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        print("\n\033[32m¡Hasta luego! La serpiente descansa en paz. 🐍\033[0m")
        sys.exit(0)
