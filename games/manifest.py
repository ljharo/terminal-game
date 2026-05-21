# ─── Game Registry ────────────────────────────────────────────────────────────
# To add a new game: create the .py file in this directory and add an entry here.
# Fields: name (display), file (filename), description (short, shown in menu).

GAMES = [
    {
        "name":        "Snake",
        "file":        "snake_game.py",
        "description": "Eat food, grow longer",
    },
    {
        "name":        "Tetris",
        "file":        "tetris_game.py",
        "description": "Stack pieces, clear lines",
    },
    {
        "name":        "2048",
        "file":        "2048.py",
        "description": "Slide tiles, reach 2048",
    },
    {
        "name":        "Game of Life",
        "file":        "game_life.py",
        "description": "Conway's automaton",
    },
    {
        "name":        "Minesweeper",
        "file":        "minesweeper.py",
        "description": "Clear the minefield",
    },
    {
        "name":        "Pong",
        "file":        "pong.py",
        "description": "Paddle vs AI, first to 7",
    },
]
