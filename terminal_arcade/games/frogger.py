#!/usr/bin/env python3
"""
Frogger — Terminal Edition
Cruza la autopista sin ser atropellado.
WASD / flechas para moverse | Espacio para pausar | R para reiniciar | Q para salir
"""

import curses
import random
import sys
import time

# ── Configuracion ──────────────────────────────────────────────────────────────
FPS         = 20
FROG_CHAR   = "o"
DEAD_CHAR   = "X"
GOAL_CHAR   = "#"
MEDIAN_CHAR = "-"
START_CHAR  = "."
ROAD_CHAR   = " "
LIVES_INIT  = 3

# IDs de pares de color
CP_FROG,   CP_CAR_R, CP_CAR_L = 1, 2, 3
CP_GOAL,   CP_MEDIAN, CP_ROAD  = 4, 5, 6
CP_HUD,    CP_BORDER            = 7, 8
CP_DEAD,   CP_WIN,    CP_START  = 9, 10, 11


# ── Colores ────────────────────────────────────────────────────────────────────

def setup_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(CP_FROG,   curses.COLOR_GREEN,  -1)
    curses.init_pair(CP_CAR_R,  curses.COLOR_RED,    -1)
    curses.init_pair(CP_CAR_L,  curses.COLOR_YELLOW, -1)
    curses.init_pair(CP_GOAL,   curses.COLOR_GREEN,  -1)
    curses.init_pair(CP_MEDIAN, curses.COLOR_WHITE,  -1)
    curses.init_pair(CP_ROAD,   curses.COLOR_WHITE,  -1)
    curses.init_pair(CP_HUD,    curses.COLOR_CYAN,   -1)
    curses.init_pair(CP_BORDER, curses.COLOR_YELLOW, -1)
    curses.init_pair(CP_DEAD,   curses.COLOR_RED,    -1)
    curses.init_pair(CP_WIN,    curses.COLOR_GREEN,  -1)
    curses.init_pair(CP_START,  curses.COLOR_WHITE,  -1)
    return {
        "frog":   curses.color_pair(CP_FROG)   | curses.A_BOLD,
        "car_r":  curses.color_pair(CP_CAR_R)  | curses.A_BOLD,
        "car_l":  curses.color_pair(CP_CAR_L)  | curses.A_BOLD,
        "goal":   curses.color_pair(CP_GOAL)   | curses.A_BOLD,
        "median": curses.color_pair(CP_MEDIAN),
        "road":   curses.color_pair(CP_ROAD),
        "hud":    curses.color_pair(CP_HUD),
        "title":  curses.color_pair(CP_HUD)    | curses.A_BOLD,
        "border": curses.color_pair(CP_BORDER),
        "dead":   curses.color_pair(CP_DEAD)   | curses.A_BOLD,
        "win":    curses.color_pair(CP_WIN)    | curses.A_BOLD,
        "start":  curses.color_pair(CP_START),
    }


# ── Logica pura ────────────────────────────────────────────────────────────────

class Car:
    """Vehiculo que se desplaza horizontalmente en su carril."""

    def __init__(self, x, width, speed, direction, lane_width, color_key):
        self.x         = float(x)
        self.width     = width
        self.speed     = speed
        self.direction = direction   # +1 derecha, -1 izquierda
        self.lw        = lane_width
        self.color_key = color_key

    def update(self, dt):
        self.x += self.speed * self.direction * dt
        span = self.lw + self.width
        if self.direction > 0 and self.x >= self.lw:
            self.x -= span
        elif self.direction < 0 and self.x + self.width <= 0:
            self.x += span

    def glyph(self):
        w = self.width
        if w == 1:
            return ">" if self.direction > 0 else "<"
        if self.direction > 0:
            return ">" + "=" * (w - 1)
        return "=" * (w - 1) + "<"

    def hits_col(self, col):
        start = int(self.x)
        return start <= col < start + self.width


class GameState:
    """Estado completo de la partida de Frogger."""

    def __init__(self, game_rows, game_cols,
                 level=1, score=0, hi_score=0, lives=LIVES_INIT):
        self.game_rows = game_rows
        self.game_cols = game_cols
        self.level     = level
        self.score     = score
        self.hi_score  = hi_score
        self.lives     = lives
        self._build_lanes()
        self._reset_frog()
        self._spawn_cars()
        self.state      = "playing"
        self.anim_timer = 0.0

    def _build_lanes(self):
        inner           = self.game_rows - 2
        self.median_row = 1 + inner // 2
        self.lane_rows  = [r for r in range(1, self.game_rows - 1)
                           if r != self.median_row]

    def _reset_frog(self):
        self.frog_row = self.game_rows - 1
        self.frog_col = self.game_cols // 2

    def _spawn_cars(self):
        speed_mult = 1.0 + (self.level - 1) * 0.25
        self.cars  = {}
        for i, row in enumerate(self.lane_rows):
            direction = 1 if i % 2 == 0 else -1
            num_cars  = max(1, min(4, self.game_cols // 8))
            color_key = "car_r" if direction > 0 else "car_l"
            gap       = self.game_cols // num_cars
            lane_cars = []
            for j in range(num_cars):
                w     = max(2, min(5, gap - 3))
                speed = random.uniform(4, 10) * speed_mult
                x     = float(j * gap + random.randint(0, max(0, gap - w - 1)))
                lane_cars.append(Car(x, w, speed, direction, self.game_cols, color_key))
            self.cars[row] = lane_cars

    def move_frog(self, dr, dc):
        nr = self.frog_row + dr
        nc = self.frog_col + dc
        if 0 <= nr < self.game_rows and 0 <= nc < self.game_cols:
            self.frog_row, self.frog_col = nr, nc

    def _frog_hit(self):
        row = self.frog_row
        if row not in self.cars:
            return False
        col = self.frog_col
        return any(car.hits_col(col) for car in self.cars[row])

    def update(self, dt):
        if self.state == "dead":
            self.anim_timer -= dt
            if self.anim_timer <= 0:
                if self.lives <= 0:
                    self.state = "game_over"
                else:
                    self._reset_frog()
                    self.state = "playing"
            return

        if self.state == "won_level":
            self.anim_timer -= dt
            if self.anim_timer <= 0:
                self.level += 1
                self._spawn_cars()
                self._reset_frog()
                self.state = "playing"
            return

        if self.state != "playing":
            return

        for lane_cars in self.cars.values():
            for car in lane_cars:
                car.update(dt)

        if self._frog_hit():
            self.lives     -= 1
            self.state      = "dead"
            self.anim_timer = 1.2
            return

        if self.frog_row == 0:
            self.score    += 100 + self.level * 20
            self.hi_score  = max(self.hi_score, self.score)
            self.state     = "won_level"
            self.anim_timer = 1.5


# ── Dibujo ─────────────────────────────────────────────────────────────────────

def _put(stdscr, r, c, s, attr=0):
    try:
        stdscr.addstr(r, c, s, attr)
    except curses.error:
        pass


def draw_border(stdscr, top, left, rows, cols, colors):
    bottom = top + rows + 1
    right  = left + cols + 1
    C = colors["border"]
    try:
        stdscr.addstr(top,    left,  "\u256d", C)
        stdscr.addstr(top,    right, "\u256e", C)
        stdscr.addstr(bottom, left,  "\u2570", C)
        stdscr.addstr(bottom, right, "\u256f", C)
        for c in range(left + 1, right):
            stdscr.addstr(top,    c, "\u2500", C)
            stdscr.addstr(bottom, c, "\u2500", C)
        for r in range(top + 1, bottom):
            stdscr.addstr(r, left,  "\u2502", C)
            stdscr.addstr(r, right, "\u2502", C)
    except curses.error:
        pass


def draw_board(stdscr, gs, top, left, colors):
    gcols = gs.game_cols

    # Meta (fila 0 del juego)
    _put(stdscr, top, left, GOAL_CHAR * gcols, colors["goal"])
    label = "[ LLEGADA ]"
    if len(label) <= gcols:
        lc = left + (gcols - len(label)) // 2
        _put(stdscr, top, lc, label, colors["goal"])

    # Zona de inicio (ultima fila)
    _put(stdscr, top + gs.game_rows - 1, left, START_CHAR * gcols, colors["start"])

    # Mediana (zona segura central)
    _put(stdscr, top + gs.median_row, left, MEDIAN_CHAR * gcols, colors["median"])

    # Carriles de carretera
    for row in gs.lane_rows:
        _put(stdscr, top + row, left, ROAD_CHAR * gcols, colors["road"])

    # Vehiculos
    for row, lane_cars in gs.cars.items():
        for car in lane_cars:
            cx    = int(car.x)
            glyph = car.glyph()
            color = colors[car.color_key]
            vis_s = max(cx, 0)
            vis_e = min(cx + car.width, gcols)
            if vis_s < vis_e:
                _put(stdscr, top + row, left + vis_s,
                     glyph[vis_s - cx: vis_e - cx], color)


def draw_frog(stdscr, gs, top, left, colors):
    r = top + gs.frog_row
    c = left + gs.frog_col
    if gs.state == "dead":
        if int(gs.anim_timer * 5) % 2 == 0:
            _put(stdscr, r, c, DEAD_CHAR, colors["dead"])
    elif gs.state in ("playing", "won_level"):
        _put(stdscr, r, c, FROG_CHAR, colors["frog"])


def draw_hud(stdscr, gs, paused, term_rows, term_cols, colors):
    lives_str = "* " * gs.lives + "  " * max(0, LIVES_INIT - gs.lives)
    title     = " FROGGER "
    parts = [
        (title,                          colors["title"]),
        (f" Vidas: {lives_str}",          colors["hud"]),
        (f" Pts: {gs.score:>6} ",         colors["hud"]),
        (f" Record: {gs.hi_score:>6} ",   colors["hud"]),
        (f" Nivel: {gs.level:>2} ",       colors["hud"]),
    ]
    ctrl = " [WASD/flechas] Mover  [Espacio] Pausar  [R] Reiniciar  [Q] Salir "

    try:
        stdscr.addstr(0, 0, " " * (term_cols - 1), colors["hud"])
        col = 1
        for text, attr in parts:
            if col + len(text) >= term_cols - 1:
                break
            stdscr.addstr(0, col, text, attr)
            col += len(text) + 1

        bot = term_rows - 1
        stdscr.addstr(bot, 0, " " * (term_cols - 1), colors["hud"])
        stdscr.addstr(bot, 1, ctrl[:term_cols - 2], colors["hud"])
        if paused:
            msg = " PAUSADO "
            stdscr.addstr(bot, term_cols - len(msg) - 1, msg, colors["dead"])
    except curses.error:
        pass


def draw_overlay(stdscr, gs, top, left, colors):
    W = 23
    if gs.state == "won_level":
        bonus = 100 + gs.level * 20
        lines = [
            "+" + "=" * W + "+",
            "|" + f" NIVEL {gs.level} SUPERADO! ".center(W) + "|",
            "|" + f"+{bonus} puntos".center(W) + "|",
            "+" + "=" * W + "+",
        ]
        color = colors["win"]
    elif gs.state == "game_over":
        lines = [
            "+" + "=" * W + "+",
            "|" + "  GAME  OVER  ".center(W) + "|",
            "|" + f"Puntos: {gs.score}".center(W) + "|",
            "|" + f"Record: {gs.hi_score}".center(W) + "|",
            "|" + " " * W + "|",
            "|" + "[R] Reiniciar".center(W) + "|",
            "|" + "[Q] Salir".center(W) + "|",
            "+" + "=" * W + "+",
        ]
        color = colors["dead"]
    else:
        return

    box_width = W + 2
    mid_r = top + gs.game_rows // 2 - len(lines) // 2
    mid_c = left + max(0, (gs.game_cols - box_width) // 2)
    for i, line in enumerate(lines):
        _put(stdscr, mid_r + i, mid_c, line, color)


# ── Loop principal ─────────────────────────────────────────────────────────────

def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(0)

    colors = (setup_colors() if curses.has_colors()
              else {k: curses.A_BOLD for k in
                    ("frog", "car_r", "car_l", "goal", "median", "road",
                     "hud", "title", "border", "dead", "win", "start")})

    term_rows, term_cols = stdscr.getmaxyx()
    game_top  = 1
    game_left = 0
    game_rows = term_rows - 4
    game_cols = term_cols - 2

    gs        = GameState(game_rows, game_cols)
    paused    = False
    last_time = time.time()

    while True:
        now = time.time()
        dt  = min(now - last_time, 0.1)
        last_time = now

        # ── Input ──────────────────────────────────────────────────────────────
        try:
            key = stdscr.getch()
        except curses.error:
            key = -1

        if key in (ord('q'), ord('Q')):
            break
        elif key == ord(' '):
            if gs.state == "playing":
                paused = not paused
        elif key in (ord('r'), ord('R')):
            new_rows, new_cols = stdscr.getmaxyx()
            term_rows, term_cols = new_rows, new_cols
            game_rows = term_rows - 4
            game_cols = term_cols - 2
            gs = GameState(game_rows, game_cols)
            paused = False
            stdscr.clear()
        elif gs.state == "playing" and not paused:
            if key in (curses.KEY_UP,    ord('w'), ord('W')):
                gs.move_frog(-1,  0)
            elif key in (curses.KEY_DOWN,  ord('s'), ord('S')):
                gs.move_frog( 1,  0)
            elif key in (curses.KEY_LEFT,  ord('a'), ord('A')):
                gs.move_frog( 0, -1)
            elif key in (curses.KEY_RIGHT, ord('d'), ord('D')):
                gs.move_frog( 0,  1)

        # ── Resize ─────────────────────────────────────────────────────────────
        new_rows, new_cols = stdscr.getmaxyx()
        if new_rows != term_rows or new_cols != term_cols:
            term_rows, term_cols = new_rows, new_cols
            game_rows = term_rows - 4
            game_cols = term_cols - 2
            gs = GameState(game_rows, game_cols,
                           level=gs.level, score=gs.score, hi_score=gs.hi_score)
            stdscr.clear()

        # ── Actualizar ─────────────────────────────────────────────────────────
        if not paused:
            gs.update(dt)

        # ── Dibujar ────────────────────────────────────────────────────────────
        stdscr.erase()
        draw_border(stdscr, game_top, game_left, game_rows, game_cols, colors)
        ctop  = game_top  + 1
        cleft = game_left + 1
        draw_board(stdscr, gs, ctop, cleft, colors)
        draw_frog(stdscr, gs, ctop, cleft, colors)
        draw_hud(stdscr, gs, paused, term_rows, term_cols, colors)
        draw_overlay(stdscr, gs, ctop, cleft, colors)
        stdscr.refresh()
        time.sleep(1.0 / FPS)


# ── Entrada ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        print("\n\033[32mHasta luego! La rana descansa en paz.\033[0m")
        sys.exit(0)
