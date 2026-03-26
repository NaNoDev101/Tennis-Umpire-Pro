<div align="center">

```
████████╗███████╗███╗   ██╗███╗   ██╗██╗███████╗
    ╚══██╔══╝██╔════╝████╗  ██║████╗  ██║██║██╔════╝
          ██║   █████╗  ██╔██╗ ██║██╔██╗ ██║██║███████╗
          ██║   ██╔══╝  ██║╚██╗██║██║╚██╗██║██║╚════██║
          ██║   ███████╗██║ ╚████║██║ ╚████║██║███████║
           ╚═╝   ╚══════╝╚═╝  ╚═══╝╚═╝  ╚═══╝╚═╝╚══════╝
         U M P I R E   P R O  🎾
```

**A professional desktop tennis scoring app — built with Python & tkinter**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-Personal%2FEducational-green?style=for-the-badge)](#license)
[![Tests](https://img.shields.io/badge/Tests-31%20passing-brightgreen?style=for-the-badge&logo=pytest)](#running-tests)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey?style=for-the-badge)]()

<br>

*Track every point, game, set, and tiebreak in real time — then generate a beautiful PNG match card when it's all over.*

</div>

---

## ✨ Features

| 🏆 Feature | 📋 Detail |
|---|---|
| **Full Scoring** | `0` / `15` / `30` / `40` / `Deuce` / `Advantage` |
| **Tiebreak** | Correct ATP/WTA serve rotation, change ends every 6 pts |
| **Break Points** | Live indicator + created/won stats |
| **Aces & DFs** | One-click buttons + keyboard shortcuts |
| **Undo** | Unlimited undo via lightweight serialization history |
| **Save / Load** | Full match state persisted as JSON |
| **Match Card** | Professional **1080px PNG** report on match completion |
| **Sound** | Desktop notifications via `canberra-gtk-play` *(Linux)* |
| **Live Stats** | Aces, double faults, break points, total points |
| **Clock** | Live elapsed match timer |

---

## 📁 Project Structure

```
tennis_umpire_pro/
│
├── 🚀 main.py                ← Entry point — setup dialogs & app bootstrap
├── ⚙️  engine.py              ← MatchEngine, MatchState, EventEmitter
├── 🖥️  ui.py                  ← Main TennisUI window (assembles all components)
├── 🎨 theme.py               ← Theme (tkinter), CardPalette (PIL), MatchConfig
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
│   └── test_engine.py        ← 31 unit tests — engine only, no UI needed
│
├── conftest.py               ← pytest path configuration
└── requirements.txt
```

---

## 🏗️ Architecture

Clean **Model / Controller / View** separation — the engine is 100% UI-free and independently testable.

```
┌─────────────────────┐    score_point()    ┌──────────────────────┐
│     TennisUI        │ ──────────────────▶ │    MatchEngine        │
│      (View)         │                     │    (Controller)       │
│                     │ ◀── Event.REFRESH ─ │                       │
│  ┌─────────────┐    │                     │  ┌────────────────┐   │
│  │ Scoreboard  │    │                     │  │  MatchState    │   │
│  │ Controls    │    │                     │  │  (Model/data)  │   │
│  │ StatsPanel  │    │                     │  └────────────────┘   │
│  │ Feed        │    │                     │  ┌────────────────┐   │
│  └─────────────┘    │                     │  │ EventEmitter   │   │
└─────────────────────┘                     │  │ (Event bus)    │   │
                                            │  └────────────────┘   │
                                            └──────────────────────┘
```

---

## ⚡ Quick Start

### 1 — Clone / unzip the project

```bash
git clone https://github.com/yourusername/tennis-umpire-pro.git
cd tennis-umpire-pro
```

### 2 — Install dependencies

```bash
pip install -r requirements.txt
```

### 3 — *(Linux only)* Optional sound support

```bash
# Ubuntu / Debian
sudo apt install libcanberra-gtk-tools

# Arch Linux
sudo pacman -S libcanberra
```

### 4 — Run

```bash
python main.py
```

> **Python ≥ 3.10** is required — the engine uses `match` statement syntax and `dataclasses` with `kw_only` defaults.  
> Tested on Python **3.10 – 3.12**.

On launch, setup dialogs will ask for:

1. 🧑 Player 1 name
2. 🧑 Player 2 name
3. 🏆 Best of 3 or 5 sets
4. 🎾 Games per set before tiebreak *(default: 6)*
5. 🔔 Enable sound?

---

## ⌨️ Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `←` | Point → Player 1 |
| `→` | Point → Player 2 |
| `U` | Undo last point |

---

## 🧪 Running Tests

The engine is fully testable **without a display or tkinter** — no GUI required.

```bash
# From the project root
python -m pytest tests/ -v
```

Expected result: ✅ **31 passed**

---

## 🔧 Extending

<details>
<summary><b>Adding a new theme</b></summary>

Subclass `Theme` in `theme.py` and override any colour or font attribute:

```python
class LightTheme(Theme):
    BG_MAIN      = "#f5f5f5"
    FG_PRIMARY   = "#1a1a1a"
    ACCENT_GREEN = "#007a3d"
```

Pass `LightTheme` wherever `Theme` is used.

</details>

<details>
<summary><b>Adding a new event</b></summary>

1. Add a member to `Event` in `engine.py`:
   ```python
   class Event(str, Enum):
       ...
       MY_NEW_EVENT = auto()
   ```
2. Emit it from the engine:
   ```python
   self.events.emit(Event.MY_NEW_EVENT, payload)
   ```
3. Subscribe in `ui.py`:
   ```python
   engine.on(Event.MY_NEW_EVENT, self._on_my_new_event)
   ```

</details>

<details>
<summary><b>Adding a new statistic</b></summary>

1. Add the counter field to `MatchState` in `engine.py`
2. Increment it inside `score_point()` or a helper method
3. Pass the new value to `StatsPanel.update()` in `components/stats_panel.py` and add a row to the formatted string

</details>

---

## 📦 Dependencies

```
Pillow >= 10.0.0    # PNG match-card generation
pytest >= 7.0.0     # Unit-test runner (dev only)
```

Everything else (`tkinter`, `json`, `logging`, `subprocess`, `dataclasses`, `datetime`) is part of the Python standard library.

---

## 📄 License

Personal / educational project — by **MrNaNo ✦ N4N0 Staff**

---

<div align="center">
  <sub>Built with 🎾 and Python by <b>MrNaNo</b></sub>
</div>
