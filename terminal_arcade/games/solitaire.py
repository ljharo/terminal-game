#!/usr/bin/env python3
"""
Klondike Solitaire
Arrows: move cursor  |  Enter/Space: select/place  |  D: draw from stock
U: undo  |  R: new game  |  Q: quit
"""
import curses
import random
import sys
import time

# ─── Configuration ─────────────────────────────────────────────────────────────
SUITS  = ["C", "D", "H", "S"]   # Clubs, Diamonds, Hearts, Spades
SUIT_SYM = {"C": "\u2663", "D": "\u2666", "H": "\u2665", "S": "\u2660"}
RANKS  = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
RANK_VAL = {r: i for i, r in enumerate(RANKS)}  # A=0 .. K=12
RED_SUITS   = {"D", "H"}
BLACK_SUITS = {"C", "S"}

# Cursor zones: 0=stock, 1=waste, 2-5=foundations(0-3), 6-12=tableau(0-6)
ZONE_STOCK      = 0
ZONE_WASTE      = 1
ZONE_FOUND_BASE = 2   # foundations 2..5
ZONE_TAB_BASE   = 6   # tableau     6..12

# Color pairs
CP_RED    = 1
CP_BLACK  = 2
CP_BACK   = 3   # card back
CP_EMPTY  = 4   # empty slot
CP_SEL    = 5   # selected highlight
CP_HUD    = 6
CP_WIN    = 7
CP_CURSOR = 8


def setup_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(CP_RED,    curses.COLOR_RED,     curses.COLOR_WHITE)
    curses.init_pair(CP_BLACK,  curses.COLOR_BLACK,   curses.COLOR_WHITE)
    curses.init_pair(CP_BACK,   curses.COLOR_BLUE,    curses.COLOR_BLUE)
    curses.init_pair(CP_EMPTY,  curses.COLOR_WHITE,   -1)
    curses.init_pair(CP_SEL,    curses.COLOR_BLACK,   curses.COLOR_YELLOW)
    curses.init_pair(CP_HUD,    curses.COLOR_CYAN,    -1)
    curses.init_pair(CP_WIN,    curses.COLOR_BLACK,   curses.COLOR_GREEN)
    curses.init_pair(CP_CURSOR, curses.COLOR_YELLOW,  -1)


# ─── Game Logic ─────────────────────────────────────────────────────────────────
class Card:
    __slots__ = ("rank", "suit", "face_up")

    def __init__(self, rank, suit, face_up=False):
        self.rank    = rank
        self.suit    = suit
        self.face_up = face_up

    @property
    def value(self):
        return RANK_VAL[self.rank]

    @property
    def is_red(self):
        return self.suit in RED_SUITS

    def __repr__(self):
        return f"{self.rank}{self.suit}({'U' if self.face_up else 'D'})"


class Game:
    def __init__(self):
        self.stock       = []
        self.waste       = []
        self.foundations = [[] for _ in range(4)]   # indexed by suit order
        self.tableau     = [[] for _ in range(7)]
        self.moves       = 0
        self._t0         = time.time()
        self._history    = []   # list of snapshots for undo
        self._won        = False
        self._deal()

    # ── Internal helpers ────────────────────────────────────────────────────────
    def _deal(self):
        deck = [Card(r, s) for s in SUITS for r in RANKS]
        random.shuffle(deck)
        for col in range(7):
            for row in range(col + 1):
                card = deck.pop()
                card.face_up = (row == col)
                self.tableau[col].append(card)
        for card in deck:
            card.face_up = False
            self.stock.append(card)

    def _snapshot(self):
        import copy
        return (
            [copy.copy(c) for c in self.stock],
            [copy.copy(c) for c in self.waste],
            [[copy.copy(c) for c in f] for f in self.foundations],
            [[copy.copy(c) for c in t] for t in self.tableau],
            self.moves,
        )

    def _restore(self, snap):
        self.stock, self.waste, self.foundations, self.tableau, self.moves = snap

    # ── Foundation index for a suit ─────────────────────────────────────────────
    @staticmethod
    def _found_idx(suit):
        return SUITS.index(suit)

    # ── Move validation ─────────────────────────────────────────────────────────
    def can_place_on_tableau(self, card, pile):
        if not pile:
            return card.rank == "K"
        top = pile[-1]
        if not top.face_up:
            return False
        return (card.is_red != top.is_red) and (card.value == top.value - 1)

    def can_place_on_foundation(self, card, fidx):
        f = self.foundations[fidx]
        if not f:
            return card.rank == "A"
        top = f[-1]
        return card.suit == top.suit and card.value == top.value + 1

    # ── Actions ─────────────────────────────────────────────────────────────────
    def draw_stock(self):
        self._push_history()
        if self.stock:
            card = self.stock.pop()
            card.face_up = True
            self.waste.append(card)
        else:
            # Recycle waste back to stock (face down)
            for card in reversed(self.waste):
                card.face_up = False
                self.stock.append(card)
            self.waste.clear()
        self.moves += 1

    def move_waste_to_foundation(self):
        if not self.waste:
            return False
        card = self.waste[-1]
        fidx = self._found_idx(card.suit)
        if self.can_place_on_foundation(card, fidx):
            self._push_history()
            self.foundations[fidx].append(self.waste.pop())
            self.moves += 1
            self._check_win()
            return True
        return False

    def move_waste_to_tableau(self, col):
        if not self.waste:
            return False
        card = self.waste[-1]
        if self.can_place_on_tableau(card, self.tableau[col]):
            self._push_history()
            self.tableau[col].append(self.waste.pop())
            self.moves += 1
            return True
        return False

    def move_tableau_to_foundation(self, col):
        pile = self.tableau[col]
        if not pile:
            return False
        card = pile[-1]
        if not card.face_up:
            return False
        fidx = self._found_idx(card.suit)
        if self.can_place_on_foundation(card, fidx):
            self._push_history()
            self.foundations[fidx].append(pile.pop())
            if pile and not pile[-1].face_up:
                pile[-1].face_up = True
            self.moves += 1
            self._check_win()
            return True
        return False

    def move_tableau_to_tableau(self, src_col, card_idx, dst_col):
        """Move cards from src_col[card_idx:] to dst_col."""
        src = self.tableau[src_col]
        dst = self.tableau[dst_col]
        if card_idx >= len(src):
            return False
        moving = src[card_idx:]
        if not moving[0].face_up:
            return False
        if not self.can_place_on_tableau(moving[0], dst):
            return False
        self._push_history()
        dst.extend(moving)
        del src[card_idx:]
        if src and not src[-1].face_up:
            src[-1].face_up = True
        self.moves += 1
        return True

    def move_foundation_to_tableau(self, fidx, col):
        f = self.foundations[fidx]
        if not f:
            return False
        card = f[-1]
        if self.can_place_on_tableau(card, self.tableau[col]):
            self._push_history()
            self.tableau[col].append(f.pop())
            self.moves += 1
            return True
        return False

    def _push_history(self):
        if len(self._history) > 50:
            self._history.pop(0)
        self._history.append(self._snapshot())

    def undo(self):
        if self._history:
            self._restore(self._history.pop())
            self._won = False

    def _check_win(self):
        self._won = all(len(f) == 13 for f in self.foundations)

    @property
    def won(self):
        return self._won

    @property
    def elapsed(self):
        return int(time.time() - self._t0)


# ─── Rendering ──────────────────────────────────────────────────────────────────
CARD_W = 4   # " A♠ " — 4 chars wide
CARD_H = 1   # single-line card representation


def _card_str(card):
    if not card.face_up:
        return "####"
    r = card.rank
    s = SUIT_SYM[card.suit]
    label = r + s
    return label.ljust(3)[:3] + " "


def _card_attr(card, selected=False, cursor=False):
    if not card.face_up:
        attr = curses.color_pair(CP_BACK)
    elif card.is_red:
        attr = curses.color_pair(CP_RED) | curses.A_BOLD
    else:
        attr = curses.color_pair(CP_BLACK) | curses.A_BOLD
    if selected:
        attr = curses.color_pair(CP_SEL) | curses.A_BOLD
    if cursor:
        attr |= curses.A_REVERSE
    return attr


def draw(stdscr, game, cursor_zone, sel):
    """
    sel: None or (zone, col_or_fidx, card_idx) — what's picked up
    cursor_zone: int in 0..12
    """
    stdscr.erase()
    sh, sw = stdscr.getmaxyx()

    MIN_W, MIN_H = 80, 24
    if sw < MIN_W or sh < MIN_H:
        try:
            stdscr.addstr(0, 0, f"Terminal too small ({sw}x{sh}). Need {MIN_W}x{MIN_H}.")
        except curses.error:
            pass
        stdscr.refresh()
        return

    def put(y, x, s, a=0):
        try:
            stdscr.addstr(y, x, s, a)
        except curses.error:
            pass

    # Layout: 7 columns * 4 chars + 6 gaps * 1 = 34, center it
    board_w = 7 * CARD_W + 6   # 34
    ox = max(0, (sw - board_w) // 2)
    oy = 1

    # ── HUD ──
    hud = f"Moves: {game.moves}  Time: {game.elapsed}s"
    put(0, ox, hud, curses.color_pair(CP_HUD))
    if game.won:
        msg = " YOU WIN! Press R for new game "
        put(0, ox + len(hud) + 2, msg, curses.color_pair(CP_WIN) | curses.A_BOLD)

    help_y = sh - 1
    put(help_y, 0,
        " Arrows:Move  Enter/Click:Pick/Place  RClick:Desel  D:Draw  U:Undo  R:New  Q:Quit",
        curses.A_DIM)

    # Column x positions
    col_x = [ox + i * (CARD_W + 1) for i in range(7)]

    def is_cursor(zone):
        return zone == cursor_zone

    def is_selected_src(zone, cidx=None):
        if sel is None:
            return False
        sz, _, si = sel
        if zone != sz:
            return False
        if cidx is None:
            return True
        return cidx >= si

    # ── Stock ──
    sx = col_x[0]
    if game.stock:
        attr = _card_attr(game.stock[-1])
        if is_cursor(ZONE_STOCK):
            attr |= curses.A_REVERSE
        put(oy, sx, "####", attr)
    else:
        attr = curses.color_pair(CP_EMPTY)
        if is_cursor(ZONE_STOCK):
            attr |= curses.A_REVERSE
        put(oy, sx, "[  ]", attr)

    # ── Waste ──
    wx = col_x[1]
    if game.waste:
        card = game.waste[-1]
        selected = is_selected_src(ZONE_WASTE)
        cur = is_cursor(ZONE_WASTE)
        attr = _card_attr(card, selected, cur)
        put(oy, wx, _card_str(card), attr)
    else:
        attr = curses.color_pair(CP_EMPTY)
        if is_cursor(ZONE_WASTE):
            attr |= curses.A_REVERSE
        put(oy, wx, "[  ]", attr)

    # ── Foundations ──
    for fi in range(4):
        fx = col_x[3 + fi]
        zone = ZONE_FOUND_BASE + fi
        f = game.foundations[fi]
        if f:
            card = f[-1]
            selected = is_selected_src(zone)
            cur = is_cursor(zone)
            attr = _card_attr(card, selected, cur)
            put(oy, fx, _card_str(card), attr)
        else:
            attr = curses.color_pair(CP_EMPTY)
            if is_cursor(zone):
                attr |= curses.A_REVERSE
            sym = SUIT_SYM[SUITS[fi]]
            put(oy, fx, f"[{sym} ]", attr)

    # ── Tableau ──
    tab_oy = oy + 2
    for ci in range(7):
        cx   = col_x[ci]
        zone = ZONE_TAB_BASE + ci
        pile = game.tableau[ci]
        cur  = is_cursor(zone)

        if not pile:
            attr = curses.color_pair(CP_EMPTY)
            if cur:
                attr |= curses.A_REVERSE
            put(tab_oy, cx, "[  ]", attr)
        else:
            for ri, card in enumerate(pile):
                y        = tab_oy + ri
                selected = is_selected_src(zone, ri)
                # cursor on zone highlights the bottom-most face-up card (or top card)
                at_cur   = cur and (ri == _cursor_card_idx(pile))
                attr     = _card_attr(card, selected, at_cur)
                put(y, cx, _card_str(card), attr)

    stdscr.refresh()


def _cursor_card_idx(pile):
    """Index of the top face-up card (the 'active' card for cursor highlight)."""
    for i in range(len(pile) - 1, -1, -1):
        if pile[i].face_up:
            return i
    return len(pile) - 1


def _first_faceup_idx(pile):
    """Index of the first face-up card (start of movable sequence)."""
    for i, c in enumerate(pile):
        if c.face_up:
            return i
    return len(pile) - 1


# ─── Input / Controller ─────────────────────────────────────────────────────────
def _zone_neighbors():
    """
    Adjacency for arrow navigation.
    Returns dict: zone -> {UP, DOWN, LEFT, RIGHT} -> zone
    Layout row 0: stock(0) waste(1) _ found0(2) found1(3) found2(4) found3(5)
    Layout row 1: tab0(6) tab1(7) tab2(8) tab3(9) tab4(10) tab5(11) tab6(12)
    """
    nav = {}

    # Top row: 0,1,_,2,3,4,5  mapped to col positions 0,1,2,3,4,5,6
    top = [0, 1, -1, 2, 3, 4, 5]   # zone at each col position (-1 = skip)
    top_valid = [z for z in top if z != -1]

    for idx, zone in enumerate(top):
        if zone == -1:
            continue
        nav[zone] = {}
        # LEFT
        li = idx - 1
        while li >= 0 and top[li] == -1:
            li -= 1
        nav[zone]["LEFT"]  = top[li] if li >= 0 else zone
        # RIGHT
        ri = idx + 1
        while ri < len(top) and top[ri] == -1:
            ri += 1
        nav[zone]["RIGHT"] = top[ri] if ri < len(top) else zone
        # UP stays same row
        nav[zone]["UP"]    = zone
        # DOWN -> tableau at same column position
        nav[zone]["DOWN"]  = ZONE_TAB_BASE + min(idx, 6)

    # Bottom row: tab 0-6 at col positions 0-6
    for ci in range(7):
        zone = ZONE_TAB_BASE + ci
        nav[zone] = {
            "LEFT":  ZONE_TAB_BASE + max(0, ci - 1),
            "RIGHT": ZONE_TAB_BASE + min(6, ci + 1),
            "DOWN":  zone,
            "UP":    top[min(ci, len(top) - 1)],
        }
        # Map up: find nearest valid top zone at or left of ci
        for ti in range(min(ci, len(top) - 1), -1, -1):
            if top[ti] != -1:
                nav[zone]["UP"] = top[ti]
                break

    return nav


NAV = _zone_neighbors()


def _screen_to_zone(my, mx, sh, sw, game):
    """Convierte posicion del mouse a (zone, card_idx). Retorna (None, None) si no hay hit."""
    board_w = 7 * CARD_W + 6
    ox      = max(0, (sw - board_w) // 2)
    oy      = 1
    tab_oy  = oy + 2
    col_x   = [ox + i * (CARD_W + 1) for i in range(7)]

    # Columna 0-6 segun x del mouse
    ci = -1
    for i, cx in enumerate(col_x):
        if cx <= mx < cx + CARD_W:
            ci = i
            break
    if ci == -1:
        return None, None

    if my == oy:  # fila superior: stock, waste, foundations
        if ci == 0:
            return ZONE_STOCK, None
        if ci == 1:
            return ZONE_WASTE, None
        if ci >= 3:
            return ZONE_FOUND_BASE + (ci - 3), None
        return None, None  # ci == 2: hueco vacio entre waste y foundations

    if my >= tab_oy:  # tableau
        ri   = my - tab_oy
        pile = game.tableau[ci]
        if ri < len(pile):
            return ZONE_TAB_BASE + ci, ri
        if not pile:
            return ZONE_TAB_BASE + ci, None

    return None, None


def handle_select(game, cursor_zone, sel, tab_card_idx=None):
    """
    Returns new sel state after Enter/Space/Click on cursor_zone.
    sel: None or (zone, col_or_fidx, card_idx)
    tab_card_idx: card row clicked in tableau (mouse only), para pick up exacto.
    """
    if sel is None:
        # Pick up
        if cursor_zone == ZONE_STOCK:
            game.draw_stock()
            return None
        elif cursor_zone == ZONE_WASTE:
            if game.waste:
                return (ZONE_WASTE, 0, 0)
        elif ZONE_FOUND_BASE <= cursor_zone < ZONE_TAB_BASE:
            fidx = cursor_zone - ZONE_FOUND_BASE
            if game.foundations[fidx]:
                return (cursor_zone, fidx, 0)
        else:  # tableau
            col  = cursor_zone - ZONE_TAB_BASE
            pile = game.tableau[col]
            if pile:
                if (tab_card_idx is not None
                        and 0 <= tab_card_idx < len(pile)
                        and pile[tab_card_idx].face_up):
                    cidx = tab_card_idx
                else:
                    cidx = _first_faceup_idx(pile)
                return (cursor_zone, col, cidx)
        return None
    else:
        # Place down
        src_zone, src_colidx, card_idx = sel

        if cursor_zone == sel[0]:
            # Clicking same zone deselects
            return None

        # Destination is foundation
        if ZONE_FOUND_BASE <= cursor_zone < ZONE_TAB_BASE:
            fidx = cursor_zone - ZONE_FOUND_BASE
            moved = False
            if src_zone == ZONE_WASTE:
                moved = game.move_waste_to_foundation()
            elif src_zone >= ZONE_TAB_BASE:
                # Only single card (top) to foundation
                col = src_colidx
                pile = game.tableau[col]
                if card_idx == len(pile) - 1:
                    moved = game.move_tableau_to_foundation(col)
            elif ZONE_FOUND_BASE <= src_zone < ZONE_TAB_BASE:
                # Foundation to foundation not allowed
                pass
            return None if moved or True else sel

        # Destination is tableau
        if cursor_zone >= ZONE_TAB_BASE:
            dst_col = cursor_zone - ZONE_TAB_BASE
            moved = False
            if src_zone == ZONE_WASTE:
                moved = game.move_waste_to_tableau(dst_col)
            elif src_zone >= ZONE_TAB_BASE:
                src_col = src_colidx
                moved = game.move_tableau_to_tableau(src_col, card_idx, dst_col)
            elif ZONE_FOUND_BASE <= src_zone < ZONE_TAB_BASE:
                fi = src_colidx
                moved = game.move_foundation_to_tableau(fi, dst_col)
            return None

        return None


# ─── Main Loop ──────────────────────────────────────────────────────────────────
def main(stdscr):
    setup_colors()
    curses.curs_set(0)
    stdscr.nodelay(True)
    curses.mousemask(curses.ALL_MOUSE_EVENTS)

    game        = Game()
    cursor_zone = ZONE_STOCK
    sel         = None   # currently selected/picked-up source

    LEFT  = curses.BUTTON1_PRESSED | curses.BUTTON1_CLICKED
    RIGHT = curses.BUTTON3_PRESSED | curses.BUTTON3_CLICKED

    while True:
        draw(stdscr, game, cursor_zone, sel)
        time.sleep(0.05)
        key = stdscr.getch()
        if key == -1:
            continue

        if key in (ord('q'), ord('Q')):
            break

        elif key in (ord('r'), ord('R')):
            game        = Game()
            cursor_zone = ZONE_STOCK
            sel         = None

        elif key in (ord('d'), ord('D')):
            game.draw_stock()
            sel = None

        elif key in (ord('u'), ord('U')):
            game.undo()
            sel = None

        elif key == curses.KEY_LEFT:
            cursor_zone = NAV[cursor_zone]["LEFT"]

        elif key == curses.KEY_RIGHT:
            cursor_zone = NAV[cursor_zone]["RIGHT"]

        elif key == curses.KEY_UP:
            cursor_zone = NAV[cursor_zone]["UP"]

        elif key == curses.KEY_DOWN:
            cursor_zone = NAV[cursor_zone]["DOWN"]

        elif key in (ord(' '), ord('\n'), curses.KEY_ENTER):
            sel = handle_select(game, cursor_zone, sel)

        elif key == curses.KEY_MOUSE:
            try:
                _, mx, my, _, bstate = curses.getmouse()
                sh, sw = stdscr.getmaxyx()
                if bstate & LEFT:
                    zone, ri = _screen_to_zone(my, mx, sh, sw, game)
                    if zone is not None:
                        cursor_zone = zone
                        sel = handle_select(game, zone, sel, ri)
                elif bstate & RIGHT:
                    sel = None
            except curses.error:
                pass


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
