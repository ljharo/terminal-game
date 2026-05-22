#!/usr/bin/env python3
"""
Minesweeper
Arrow keys: move  |  Space/Enter: reveal  |  F: flag  |  R: new game  |  Q: quit
Space on a revealed number: chord-reveal neighbors when flag count matches.
"""
import curses
import random
import sys
import time

# ─── Configuration ─────────────────────────────────────────────────────────────
ROWS  = 16
COLS  = 16
MINES = 40

HIDDEN, REVEALED, FLAGGED = 0, 1, 2

CP_HIDDEN  = 1
CP_FLAG    = 2
CP_MINE    = 3
CP_CURSOR  = 4
CP_STATUS  = 5
CP_WIN     = 6
CP_LOSE    = 7
# CP_N[1..8] mapped to pairs 8–15
CP_N = [0, 8, 9, 10, 11, 12, 13, 14, 15]


def setup_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(CP_HIDDEN, curses.COLOR_WHITE,  curses.COLOR_WHITE)
    curses.init_pair(CP_FLAG,   curses.COLOR_YELLOW, -1)
    curses.init_pair(CP_MINE,   curses.COLOR_WHITE,  curses.COLOR_RED)
    curses.init_pair(CP_CURSOR, curses.COLOR_BLACK,  curses.COLOR_YELLOW)
    curses.init_pair(CP_STATUS, curses.COLOR_CYAN,   -1)
    curses.init_pair(CP_WIN,    curses.COLOR_BLACK,  curses.COLOR_GREEN)
    curses.init_pair(CP_LOSE,   curses.COLOR_WHITE,  curses.COLOR_RED)
    fgs = [
        curses.COLOR_BLUE, curses.COLOR_GREEN, curses.COLOR_RED,
        curses.COLOR_BLUE, curses.COLOR_RED,   curses.COLOR_CYAN,
        curses.COLOR_MAGENTA, curses.COLOR_WHITE,
    ]
    for i, fg in enumerate(fgs, 1):
        curses.init_pair(CP_N[i], fg, -1)


# ─── Game Logic ────────────────────────────────────────────────────────────────
class Board:
    def __init__(self, rows=ROWS, cols=COLS, mines=MINES):
        self.rows  = rows
        self.cols  = cols
        self.mines = mines
        # Each cell: {'s': state, 'm': is_mine, 'a': adjacent_count}
        self.cells   = [[{'s': HIDDEN, 'm': False, 'a': 0}
                          for _ in range(cols)] for _ in range(rows)]
        self.started = False
        self.over    = False
        self.won     = False
        self.flags   = 0
        self.safe_revealed = 0
        self._t0     = None

    @property
    def elapsed(self):
        return 0 if self._t0 is None else int(time.time() - self._t0)

    def _nbrs(self, r, c):
        return [(r + dr, c + dc)
                for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                if (dr or dc) and 0 <= r + dr < self.rows and 0 <= c + dc < self.cols]

    def _seed(self, sr, sc):
        safe = set(self._nbrs(sr, sc)) | {(sr, sc)}
        pool = [(r, c) for r in range(self.rows) for c in range(self.cols)
                if (r, c) not in safe]
        for r, c in random.sample(pool, min(self.mines, len(pool))):
            self.cells[r][c]['m'] = True
        for r in range(self.rows):
            for c in range(self.cols):
                self.cells[r][c]['a'] = sum(
                    1 for nr, nc in self._nbrs(r, c) if self.cells[nr][nc]['m'])

    def _do_reveal(self, r, c):
        if not self.started:
            self._seed(r, c)
            self.started = True
            self._t0 = time.time()
        cell = self.cells[r][c]
        if cell['m']:
            cell['s'] = REVEALED
            self.over = True
            for row in self.cells:
                for ce in row:
                    if ce['m']:
                        ce['s'] = REVEALED
            return
        # BFS flood fill
        q, seen = [(r, c)], set()
        while q:
            cr, cc = q.pop()
            if (cr, cc) in seen:
                continue
            seen.add((cr, cc))
            ce = self.cells[cr][cc]
            if ce['s'] != HIDDEN or ce['m']:
                continue
            ce['s'] = REVEALED
            self.safe_revealed += 1
            if ce['a'] == 0:
                q.extend(self._nbrs(cr, cc))
        if self.safe_revealed >= self.rows * self.cols - self.mines:
            self.over = True
            self.won  = True

    def reveal(self, r, c):
        if self.over:
            return
        cell = self.cells[r][c]
        if cell['s'] == FLAGGED:
            return
        if cell['s'] == REVEALED:
            # Chord: reveal hidden neighbors if flag count matches number
            if cell['a'] and sum(1 for nr, nc in self._nbrs(r, c)
                                  if self.cells[nr][nc]['s'] == FLAGGED) == cell['a']:
                for nr, nc in self._nbrs(r, c):
                    if self.cells[nr][nc]['s'] == HIDDEN:
                        self._do_reveal(nr, nc)
            return
        self._do_reveal(r, c)

    def flag(self, r, c):
        if self.over:
            return
        s = self.cells[r][c]['s']
        if s == HIDDEN:
            self.cells[r][c]['s'] = FLAGGED
            self.flags += 1
        elif s == FLAGGED:
            self.cells[r][c]['s'] = HIDDEN
            self.flags -= 1


# ─── Rendering ─────────────────────────────────────────────────────────────────
def draw(stdscr, board, cur_r, cur_c):
    stdscr.erase()
    rows, cols = stdscr.getmaxyx()

    bw = board.cols * 2 + 4   # board display width
    bh = board.rows + 4        # status + border top + rows + border bot + help

    oy = max(0, (rows - bh) // 2)
    ox = max(0, (cols - bw) // 2)

    def put(y, x, s, a=0):
        try:
            stdscr.addstr(y, x, s, a)
        except curses.error:
            pass

    # ── Status line ──
    mines_left = board.mines - board.flags
    status = f"Mines: {mines_left:3d}   Time: {board.elapsed:4d}s"
    put(oy, ox + 2, status, curses.color_pair(CP_STATUS) | curses.A_BOLD)
    if board.over:
        if board.won:
            put(oy, ox + 2 + len(status) + 3,
                f" YOU WIN! ({board.elapsed}s) ",
                curses.color_pair(CP_WIN) | curses.A_BOLD)
        else:
            put(oy, ox + 2 + len(status) + 3,
                " BOOM! GAME OVER ",
                curses.color_pair(CP_LOSE) | curses.A_BOLD)

    # ── Top border ──
    put(oy + 1, ox, "+" + "-" * (bw - 2) + "+")

    # ── Cells ──
    for r in range(board.rows):
        y = oy + 2 + r
        put(y, ox, "| ")
        for c in range(board.cols):
            x   = ox + 2 + c * 2
            cell = board.cells[r][c]
            at_cursor = (r == cur_r and c == cur_c)
            s = cell['s']

            if s == HIDDEN:
                attr = (curses.color_pair(CP_CURSOR) | curses.A_BOLD
                        if at_cursor else curses.color_pair(CP_HIDDEN))
                put(y, x, "##", attr)

            elif s == FLAGGED:
                attr = (curses.color_pair(CP_CURSOR) | curses.A_BOLD
                        if at_cursor else curses.color_pair(CP_FLAG) | curses.A_BOLD)
                put(y, x, "FF", attr)

            else:  # REVEALED
                if cell['m']:
                    put(y, x, "**", curses.color_pair(CP_MINE) | curses.A_BOLD)
                elif cell['a'] == 0:
                    attr = curses.color_pair(CP_CURSOR) if at_cursor else curses.A_DIM
                    put(y, x, "..", attr)
                else:
                    attr = curses.color_pair(CP_N[cell['a']]) | curses.A_BOLD
                    if at_cursor:
                        attr |= curses.A_REVERSE
                    put(y, x, f" {cell['a']}", attr)

        put(y, ox + 2 + board.cols * 2, " |")

    # ── Bottom border ──
    put(oy + 2 + board.rows, ox, "+" + "-" * (bw - 2) + "+")

    # ── Help ──
    put(oy + 3 + board.rows, ox,
        " Arrows:Move  Space:Reveal  F:Flag  LClick:Reveal  RClick:Flag  R:New  Q:Quit",
        curses.A_DIM)

    stdscr.refresh()


# ─── Main Loop ─────────────────────────────────────────────────────────────────
def _mouse_to_cell(my, mx, stdscr, board):
    """Convierte coordenadas del mouse a (row, col) del tablero, o (None, None)."""
    rows, cols = stdscr.getmaxyx()
    bw = board.cols * 2 + 4
    bh = board.rows + 4
    oy = max(0, (rows - bh) // 2)
    ox = max(0, (cols - bw) // 2)
    r = my - (oy + 2)
    c = (mx - (ox + 2)) // 2
    if 0 <= r < board.rows and 0 <= c < board.cols:
        return r, c
    return None, None


def main(stdscr):
    setup_colors()
    curses.curs_set(0)
    stdscr.nodelay(True)
    curses.mousemask(curses.ALL_MOUSE_EVENTS)

    board = Board()
    cur_r, cur_c = 0, 0

    LEFT  = curses.BUTTON1_PRESSED | curses.BUTTON1_CLICKED
    RIGHT = curses.BUTTON3_PRESSED | curses.BUTTON3_CLICKED

    while True:
        draw(stdscr, board, cur_r, cur_c)
        time.sleep(0.05)
        key = stdscr.getch()
        if key == -1:
            continue

        if key in (ord('q'), ord('Q')):
            break
        elif key in (ord('r'), ord('R')):
            board = Board()
            cur_r = cur_c = 0
        elif key == curses.KEY_UP:
            cur_r = max(0, cur_r - 1)
        elif key == curses.KEY_DOWN:
            cur_r = min(board.rows - 1, cur_r + 1)
        elif key == curses.KEY_LEFT:
            cur_c = max(0, cur_c - 1)
        elif key == curses.KEY_RIGHT:
            cur_c = min(board.cols - 1, cur_c + 1)
        elif key in (ord(' '), ord('\n'), curses.KEY_ENTER):
            board.reveal(cur_r, cur_c)
        elif key in (ord('f'), ord('F')):
            board.flag(cur_r, cur_c)
        elif key == curses.KEY_MOUSE:
            try:
                _, mx, my, _, bstate = curses.getmouse()
                r, c = _mouse_to_cell(my, mx, stdscr, board)
                if r is not None:
                    cur_r, cur_c = r, c
                    if bstate & LEFT:
                        board.reveal(cur_r, cur_c)
                    elif bstate & RIGHT:
                        board.flag(cur_r, cur_c)
            except curses.error:
                pass


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
