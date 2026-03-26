# 🎾 Tennis Umpire Pro

**by MrNaNo — N4N0 Staff**

A desktop tennis scoring application built with Python and tkinter.
Tracks points, games, sets, tiebreaks, break points, aces and double faults
in real time — and generates a professional PNG match-report card when the
match ends.

---

## Features

| Feature | Detail |
|---------|--------|
| **Full scoring** | 0 / 15 / 30 / 40 / Deuce / Advantage |
| **Tiebreak** | Correct ATP/WTA serve rotation, change-ends every 6 pts |
| **Break points** | Live indicator + created/won stats |
| **Aces & DFs** | One-click buttons + keyboard shortcuts |
| **Undo** | Unlimited undo via lightweight serialisation history |
| **Save / Load** | Full match state as JSON (File menu) |
| **Match card** | Professional 1080 px PNG report on match completion |
| **Sound** | Desktop notifications via `canberra-gtk-play` (Linux) |
| **Live stats** | Aces, double faults, break points, total points |
| **Clock** | Elapsed match timer |

---

## Project Structure

```
tennis_umpire_pro/
│
├── main.py                   ← Entry point — startup dialogs & bootstrap
├── engine.py                 ← MatchEngine, MatchState, EventEmitter, Event
├── ui.py                     ← Main TennisUI window (assembles all components)
├── theme.py                  ← Theme (tkinter), CardPalette (PIL), MatchConfig
│
├── components/
│   ├── scoreboard.py         ← Sets / games / point score / serving dot / BP
│   ├── controls.py           ← Scoring buttons (point, ace, DF, undo)
│   ├── stats_panel.py        ← Live statistics table
│   └── feed.py               ← Timestamped event log
│
├── utils/
│   └── sound.py              ← SoundManager (canberra-gtk-play wrapper)
│
├── render/
│   └── match_card.py         ← PNG match-card generator (Pillow)
│
├── tests/
│   └── test_engine.py        ← 31 unit tests — engine only, no UI required
│
├── conftest.py               ← pytest path configuration
└── requirements.txt
```

### Architecture — Model / Controller / View

```
┌─────────────┐   score_point()   ┌──────────────────┐
│  TennisUI   │ ──────────────── ▶│  MatchEngine      │
│  (View)     │                   │  (Controller)     │
│             │ ◀─ Event.REFRESH ─│                   │
│  Components │                   │  MatchState       │
│  Scoreboard │                   │  (Model / data)   │
│  Controls   │                   │                   │
│  StatsPanel │                   │  EventEmitter     │
│  Feed       │                   │  (Event bus)      │
└─────────────┘                   └──────────────────┘
```

---

## Installation

```bash
# 1. Clone / unzip the project
cd tennis_umpire_pro

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. (Linux) Install sound support — optional
sudo apt install libcanberra-gtk-tools   # Ubuntu/Debian
# or
sudo pacman -S libcanberra              # Arch
```

> **Python ≥ 3.10** is required (uses `match` syntax patterns internally
> and `dataclasses` with `kw_only` defaults).  
> Tested on Python 3.10 – 3.12.

---

## Running

```bash
python main.py
```

Setup dialogs will ask for:

1. Player 1 name
2. Player 2 name
3. Best of 3 or 5 sets
4. Games-per-set before tiebreak (default 6)
5. Enable sound?

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `←` | Point — Player 1 |
| `→` | Point — Player 2 |
| `U` | Undo last point |

---

## Running Tests

The engine is fully testable without a display or tkinter.

```bash
# From inside tennis_umpire_pro/
python -m pytest tests/ -v
```

Expected output: **31 passed**.

---

## Extending

### Adding a new theme

Subclass `Theme` in `theme.py` and override any colour or font attribute:

```python
class LightTheme(Theme):
    BG_MAIN    = "#f5f5f5"
    FG_PRIMARY = "#1a1a1a"
    ACCENT_GREEN = "#007a3d"
```

Then pass `LightTheme` wherever `Theme` is used.

### Adding a new event

1. Add a member to `Event` in `engine.py`:
   ```python
   class Event(str, Enum):
       ...
       MY_NEW_EVENT = auto()
   ```
2. Emit it from the engine: `self.events.emit(Event.MY_NEW_EVENT, payload)`
3. Subscribe in `ui.py`: `e.on(Event.MY_NEW_EVENT, self._on_my_new_event)`

### Adding a new statistic

1. Add the counter field to `MatchState` in `engine.py`.
2. Increment it inside `score_point` or a helper.
3. Pass the new value to `StatsPanel.update()` in `components/stats_panel.py`
   and add a row to the formatted string.

---

## License

Personal / educational project — by **MrNaNo ✦ N4N0 Staff**.
