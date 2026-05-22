# Terminal Arcade

A collection of classic games that run entirely in your terminal, built with Python's `curses` library. No external dependencies — pure stdlib.

```
pip install terminal-arcade
game
```

![Python](https://img.shields.io/badge/python-3.9+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Games

| Game | Description |
|------|-------------|
| **Snake** | Eat food, grow longer, don't hit yourself |
| **Tetris** | Stack falling pieces and clear lines |
| **2048** | Slide tiles and reach 2048 |
| **Game of Life** | Conway's cellular automaton |
| **Minesweeper** | Clear the minefield without hitting a mine |
| **Pong** | Paddle vs AI, first to 7 wins |
| **Solitaire** | Klondike card solitaire |

## Installation

```bash
pip install terminal-arcade
```

> **Windows users:** `curses` is not bundled with Python on Windows.
> It is installed automatically as a dependency (`windows-curses`).

## Usage

```bash
# Open the game menu
game

# Or run a specific game directly
python -m terminal_arcade
```

## Controls

Each game shows its controls at the bottom of the screen. Common keys:

| Key | Action |
|-----|--------|
| Arrow keys | Move / navigate |
| Enter / Space | Confirm / action |
| `R` | New game |
| `Q` | Quit to menu |

### Solitaire-specific

| Key | Action |
|-----|--------|
| `D` | Draw card from stock |
| `U` | Undo last move |

## Requirements

- Python 3.9+
- A terminal with at least 80×24 characters
- Unix/Linux/macOS: works out of the box
- Windows: `windows-curses` (installed automatically)

## License

MIT — see [LICENSE](LICENSE)
