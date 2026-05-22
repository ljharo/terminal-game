#!/usr/bin/env python3
"""
Conway's Game of Life — Terminal Edition
Presiona Ctrl+C para salir | 'r' para reiniciar | espacio para pausar
"""

import curses
import random
import time
import sys

# ── Configuración ──────────────────────────────────────────────
FPS          = 12          # fotogramas por segundo
ALIVE_CHAR   = "█"         # carácter para célula viva
DEAD_CHAR    = " "         # carácter para célula muerta
FILL_RATIO   = 0.30        # densidad inicial de células vivas (0.0 - 1.0)
COLOR_PAIRS  = True        # usar colores si la terminal los soporta


# ── Lógica del Juego ───────────────────────────────────────────

def create_grid(rows: int, cols: int) -> list[list[int]]:
    """Genera una grilla aleatoria."""
    return [
        [1 if random.random() < FILL_RATIO else 0 for _ in range(cols)]
        for _ in range(rows)
    ]


def count_neighbors(grid: list[list[int]], row: int, col: int, rows: int, cols: int) -> int:
    """Cuenta los vecinos vivos de una célula (con bordes toroidales)."""
    count = 0
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            r = (row + dr) % rows
            c = (col + dc) % cols
            count += grid[r][c]
    return count


def next_generation(grid: list[list[int]], rows: int, cols: int) -> tuple[list[list[int]], int]:
    """Calcula la siguiente generación. Devuelve (nueva_grilla, células_vivas)."""
    new_grid = [[0] * cols for _ in range(rows)]
    alive = 0
    for r in range(rows):
        for c in range(cols):
            neighbors = count_neighbors(grid, r, c, rows, cols)
            cell = grid[r][c]
            # Reglas de Conway
            if cell == 1 and neighbors in (2, 3):
                new_grid[r][c] = 1
                alive += 1
            elif cell == 0 and neighbors == 3:
                new_grid[r][c] = 1
                alive += 1
    return new_grid, alive


# ── Renderizado ────────────────────────────────────────────────

def setup_colors() -> dict[str, int]:
    """Inicializa pares de colores."""
    curses.start_color()
    curses.use_default_colors()

    # Célula viva: verde brillante sobre fondo negro
    curses.init_pair(1, curses.COLOR_GREEN, -1)
    # HUD: cyan sobre fondo negro
    curses.init_pair(2, curses.COLOR_CYAN, -1)
    # Título: amarillo
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    # Pausa: rojo
    curses.init_pair(4, curses.COLOR_RED, -1)

    return {
        "alive": curses.color_pair(1) | curses.A_BOLD,
        "hud":   curses.color_pair(2),
        "title": curses.color_pair(3) | curses.A_BOLD,
        "pause": curses.color_pair(4) | curses.A_BOLD,
    }


def draw_grid(stdscr, grid: list[list[int]], rows: int, cols: int, colors: dict):
    """Dibuja la grilla en pantalla."""
    alive_attr = colors["alive"]
    for r in range(rows):
        for c in range(cols):
            try:
                if grid[r][c]:
                    stdscr.addstr(r + 1, c, ALIVE_CHAR, alive_attr)
                else:
                    stdscr.addstr(r + 1, c, DEAD_CHAR)
            except curses.error:
                pass  # ignorar desbordamiento de pantalla


def draw_hud(stdscr, generation: int, alive: int, total: int,
             paused: bool, colors: dict, term_rows: int, term_cols: int):
    """Dibuja la barra de información."""
    # Título superior
    title = " JUEGO DE LA VIDA DE CONWAY "
    try:
        stdscr.addstr(0, 0, "─" * term_cols, colors["hud"])
        stdscr.addstr(0, (term_cols - len(title)) // 2, title, colors["title"])
    except curses.error:
        pass

    # Barra inferior
    density = (alive / total * 100) if total > 0 else 0
    status  = "  ⏸ PAUSADO  " if paused else ""
    info    = (
        f"  Gen: {generation:>6}  │  Vivas: {alive:>6}  │  "
        f"Densidad: {density:4.1f}%  │  "
        f"[Espacio] Pausar  [R] Reiniciar  [Ctrl+C] Salir{status}"
    )

    hud_row = term_rows - 1
    try:
        stdscr.addstr(hud_row, 0, "─" * term_cols, colors["hud"])
        stdscr.addstr(hud_row, 0, info[:term_cols - 1],
                      colors["pause"] if paused else colors["hud"])
    except curses.error:
        pass


# ── Loop principal ─────────────────────────────────────────────

def main(stdscr):
    # Configurar curses
    curses.curs_set(0)          # ocultar cursor
    stdscr.nodelay(True)        # no bloquear en getch()
    stdscr.timeout(0)

    has_colors = curses.has_colors()
    colors = setup_colors() if has_colors else {
        "alive": curses.A_BOLD,
        "hud":   curses.A_NORMAL,
        "title": curses.A_BOLD,
        "pause": curses.A_REVERSE,
    }

    # Dimensiones de la grilla (dejamos 2 filas para el HUD)
    term_rows, term_cols = stdscr.getmaxyx()
    grid_rows = term_rows - 2
    grid_cols = term_cols

    grid       = create_grid(grid_rows, grid_cols)
    generation = 0
    paused     = False
    delay      = 1.0 / FPS

    while True:
        # ── Entrada del usuario ────────────────────────────────
        try:
            key = stdscr.getch()
        except curses.error:
            key = -1

        if key == ord(' '):
            paused = not paused
        elif key in (ord('r'), ord('R')):
            term_rows, term_cols = stdscr.getmaxyx()
            grid_rows = term_rows - 2
            grid_cols = term_cols
            grid       = create_grid(grid_rows, grid_cols)
            generation = 0
            paused     = False

        # ── Actualizar estado ──────────────────────────────────
        if not paused:
            grid, alive = next_generation(grid, grid_rows, grid_cols)
            generation += 1
        else:
            alive = sum(sum(row) for row in grid)

        total = grid_rows * grid_cols

        # ── Redibujar ──────────────────────────────────────────
        # Verificar si la terminal cambió de tamaño
        new_rows, new_cols = stdscr.getmaxyx()
        if new_rows != term_rows or new_cols != term_cols:
            term_rows, term_cols = new_rows, new_cols
            grid_rows = term_rows - 2
            grid_cols = term_cols
            grid       = create_grid(grid_rows, grid_cols)
            generation = 0
            stdscr.clear()

        stdscr.erase()
        draw_grid(stdscr, grid, grid_rows, grid_cols, colors)
        draw_hud(stdscr, generation, alive, total, paused, colors, term_rows, term_cols)
        stdscr.refresh()

        time.sleep(delay)


# ── Entrada ────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        # Ctrl+C limpio — sin stack trace
        print("\n\033[32m¡Hasta luego! El universo de Conway se detuvo.\033[0m")
        sys.exit(0)
