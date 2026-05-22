#!/usr/bin/env python3
"""
Pong — player (left) vs AI (right)
W / Up   : move paddle up
S / Down : move paddle down
R        : restart after game ends
Q        : quit
First to 7 points wins.
"""
import curses
import math
import random
import sys
import time

# ─── Configuration ─────────────────────────────────────────────────────────────
WIN_SCORE  = 7
PADDLE_H   = 4
FPS        = 30
SPEED_INIT = 0.7   # cells per frame (initial)
SPEED_MAX  = 2.2   # cells per frame (cap)
AI_RATIO   = 0.80  # AI paddle speed as fraction of |vx|

CP_BORDER, CP_BALL, CP_PADDLE, CP_SCORE, CP_MSG = 1, 2, 3, 4, 5


def setup_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(CP_BORDER, curses.COLOR_WHITE,  -1)
    curses.init_pair(CP_BALL,   curses.COLOR_YELLOW, -1)
    curses.init_pair(CP_PADDLE, curses.COLOR_CYAN,   -1)
    curses.init_pair(CP_SCORE,  curses.COLOR_WHITE,  -1)
    curses.init_pair(CP_MSG,    curses.COLOR_GREEN,  -1)


# ─── Ball Factory ──────────────────────────────────────────────────────────────
def new_ball(cw, ch, toward):
    """Return (bx, by, vx, vy) in court-relative float coords."""
    angle = random.uniform(20, 50) * math.pi / 180
    return (
        float(cw) / 2,
        float(ch) / 2,
        SPEED_INIT * toward,
        SPEED_INIT * math.sin(angle) * random.choice([-1, 1]),
    )


# ─── Rendering ─────────────────────────────────────────────────────────────────
def draw(stdscr, H, W, p1y, p2y, bx, by, s1, s2, over, winner):
    stdscr.erase()

    def put(y, x, s, a=0):
        try:
            stdscr.addstr(y, x, s, a)
        except curses.error:
            pass

    border = curses.color_pair(CP_BORDER)

    # ── Border ──
    put(0,     0, "+" + "-" * (W - 2) + "+", border)
    put(H - 1, 0, "+" + "-" * (W - 2) + "+", border)
    for r in range(1, H - 1):
        put(r, 0,     "|", border)
        put(r, W - 1, "|", border)

    # ── Center dashes ──
    for r in range(1, H - 1, 2):
        put(r, W // 2, ":", curses.A_DIM)

    # ── Score ──
    score_str = f"  {s1}  :  {s2}  "
    put(0, max(1, (W - len(score_str)) // 2),
        score_str, curses.color_pair(CP_SCORE) | curses.A_BOLD)

    # ── Paddles (court y → screen y = court_y + 1) ──
    pattr = curses.color_pair(CP_PADDLE) | curses.A_BOLD
    for i in range(PADDLE_H):
        put(int(p1y) + 1 + i, 2,     "|", pattr)
        put(int(p2y) + 1 + i, W - 3, "|", pattr)

    # ── Ball ──
    put(int(by) + 1, int(bx) + 1, "O",
        curses.color_pair(CP_BALL) | curses.A_BOLD)

    # ── Win/lose message ──
    if over:
        msg = ("  YOU WIN!  " if winner == 1 else "  AI WINS!  ") + \
              "R: play again   Q: quit  "
        put(H // 2, max(1, (W - len(msg)) // 2),
            msg, curses.color_pair(CP_MSG) | curses.A_BOLD)

    # ── Controls hint ──
    hint = " W/S or Up/Dn or Scroll: move  Q: quit "
    put(H - 1, 2, hint, curses.A_DIM)

    stdscr.refresh()


# ─── Main Loop ─────────────────────────────────────────────────────────────────
def main(stdscr):
    setup_colors()
    curses.curs_set(0)
    stdscr.nodelay(True)
    curses.mousemask(curses.ALL_MOUSE_EVENTS)

    SCROLL_UP   = curses.BUTTON4_PRESSED
    SCROLL_DOWN = getattr(curses, "BUTTON5_PRESSED", 2097152)

    H, W   = stdscr.getmaxyx()
    CH     = H - 2   # court interior height
    CW     = W - 2   # court interior width

    p1y = p2y = CH // 2 - PADDLE_H // 2
    bx, by, vx, vy = new_ball(CW, CH, 1)
    s1 = s2  = 0
    over     = False
    winner   = 0

    frame_dt = 1.0 / FPS

    while True:
        t0 = time.time()

        # ── Resize ──
        nH, nW = stdscr.getmaxyx()
        if nH != H or nW != W:
            H, W   = nH, nW
            CH, CW = H - 2, W - 2
            p1y = p2y = CH // 2 - PADDLE_H // 2
            bx, by, vx, vy = new_ball(CW, CH, 1)
            s1 = s2 = 0
            over = False

        key = stdscr.getch()

        if key in (ord('q'), ord('Q')):
            break

        if over:
            if key in (ord('r'), ord('R')):
                p1y = p2y = CH // 2 - PADDLE_H // 2
                bx, by, vx, vy = new_ball(CW, CH, 1)
                s1 = s2 = 0
                over = False
        else:
            # ── Player input ──
            if key in (curses.KEY_UP, ord('w'), ord('W')):
                p1y = max(0, p1y - 1)
            elif key in (curses.KEY_DOWN, ord('s'), ord('S')):
                p1y = min(CH - PADDLE_H, p1y + 1)
            elif key == curses.KEY_MOUSE:
                try:
                    _, _, _, _, bstate = curses.getmouse()
                    if bstate & SCROLL_UP:
                        p1y = max(0, p1y - 1)
                    elif bstate & SCROLL_DOWN:
                        p1y = min(CH - PADDLE_H, p1y + 1)
                except curses.error:
                    pass

            # ── AI tracks ball ──
            ai_spd = max(1, round(abs(vx) * AI_RATIO))
            ai_mid = p2y + PADDLE_H // 2
            if ai_mid < int(by):
                p2y = min(CH - PADDLE_H, p2y + ai_spd)
            elif ai_mid > int(by):
                p2y = max(0, p2y - ai_spd)

            # ── Move ball ──
            bx += vx
            by += vy

            # ── Top / bottom wall ──
            if by < 0:
                by  = 0
                vy  = abs(vy)
            elif by > CH - 1:
                by  = CH - 1
                vy  = -abs(vy)

            # ── Left paddle (screen col 2 → court col 1) ──
            if vx < 0 and bx <= 1:
                if p1y <= by <= p1y + PADDLE_H - 1:
                    bx  = 1.0
                    hit = (by - (p1y + PADDLE_H / 2)) / (PADDLE_H / 2)
                    spd = min(math.hypot(vx, vy) * 1.05, SPEED_MAX)
                    ang = hit * 50 * math.pi / 180
                    vx  =  spd * math.cos(ang)
                    vy  =  spd * math.sin(ang)
                elif bx < 0:
                    s2 += 1
                    if s2 >= WIN_SCORE:
                        over   = True
                        winner = 2
                    else:
                        p1y = p2y = CH // 2 - PADDLE_H // 2
                        bx, by, vx, vy = new_ball(CW, CH, 1)

            # ── Right paddle (screen col W-3 → court col CW-2) ──
            elif vx > 0 and bx >= CW - 2:
                if p2y <= by <= p2y + PADDLE_H - 1:
                    bx  = float(CW - 2)
                    hit = (by - (p2y + PADDLE_H / 2)) / (PADDLE_H / 2)
                    spd = min(math.hypot(vx, vy) * 1.05, SPEED_MAX)
                    ang = hit * 50 * math.pi / 180
                    vx  = -spd * math.cos(ang)
                    vy  =  spd * math.sin(ang)
                elif bx >= CW:
                    s1 += 1
                    if s1 >= WIN_SCORE:
                        over   = True
                        winner = 1
                    else:
                        p1y = p2y = CH // 2 - PADDLE_H // 2
                        bx, by, vx, vy = new_ball(CW, CH, -1)

        draw(stdscr, H, W, p1y, p2y, bx, by, s1, s2, over, winner)

        elapsed = time.time() - t0
        if elapsed < frame_dt:
            time.sleep(frame_dt - elapsed)


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
