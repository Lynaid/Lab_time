# Lab Time

Lab Time is a 2D action roguelike prototype built with **Python** and **Pygame**.  
The project features procedurally generated dungeon floors, melee combat, enemies with AI, abilities, and sprite-based animations.

---

# Requirements

Before running the project make sure you have:

- **Python 3.11 – 3.13** (recommended: 3.13)
- **pip** package manager
- **Pygame 2.6+**

Optional but recommended:

- **Git**
- **VS Code / Visual Studio**

---

# Project Structure

The game expects the following directory structure:

```

Lab_time/
│
├── main.py
├── settings.py
│
├── actors/
├── combat/
├── core/
├── world/
├── ui/
│
└── assets/
└── sprites/
└── GEKKORAR-STUFF/
├── WALK/
├── IDLE/
└── HIT/

````

Important:

- The **assets folder must be in the project root**.
- Do **not place assets inside `actors/` or other subfolders**.

---

# Installation

## 1. Clone the repository

```bash
git clone <repository-url>
cd Lab_time
````

Or download the ZIP and extract it.

---

## 2. Install dependencies

Minimum dependency:

```bash
pip install pygame
```

---

# Running the Game

Run the game from the **project root folder**:

```bash
python main.py
```

Example:

```bash
cd Lab_time
python main.py
```

If everything is installed correctly the game window will appear.

---

# Controls

| Key            | Action               |
| -------------- | -------------------- |
| **W A S D**    | Move player          |
| **Arrow Keys** | Set attack direction |
| **SPACE**      | Melee attack         |
| **Q**          | Ability Q            |
| **R**          | Ability R            |
| **E**          | Ability E            |
| **F**          | Ability F            |

Some abilities may be locked depending on the current game state.

---

# Debug Features

Some debug options can be enabled in **settings.py**.

Example:

```python
DEBUG_MELEE_HITBOX = True
DEBUG_WALLS = True
```

Debug options may display:

* Melee hitboxes
* Room collision walls
* Additional gameplay debugging overlays

---

# Assets

Player animations use **separate PNG frames** organized like this:

```
assets/sprites/GEKKORAR-STUFF/

WALK/
 ├─ FRONT/
 ├─ BACK/
 └─ SIDE/

IDLE/
 ├─ FRONT/
 ├─ BACK/
 └─ SIDE/

HIT/
 ├─ FRONT/
 │   └─ white-stuff/
 ├─ BACK/
 │   └─ white-stuff/
 └─ SIDE/
     └─ white-stuff/
```

### Notes

* `white-stuff` contains **attack visual effects**.
* Some frames may be intentionally empty to synchronize with the attack animation timeline.

---

# Common Issues

## Game cannot find assets

Error example:

```
FileNotFoundError: assets/sprites/...
```

Fix:

Run the game from the **root folder**, not from inside `actors` or another directory.

Correct:

```
Lab_time/
python main.py
```

Incorrect:

```
Lab_time/actors/
python ../main.py
```

---

## Module Import Errors

If you see errors like:

```
ModuleNotFoundError: actors.enemy
```

Make sure you are running the game **from the root folder**.

---

## Pygame Not Installed

Install pygame manually:

```bash
pip install pygame
```

---

# Development Notes

The project includes systems for:

* Procedural dungeon generation
* Enemy AI (pathfinding, shooting, turrets)
* Melee combat with hitboxes
* Ability system
* Room layouts and events
* Minimap and HUD
* Sprite animation system

---

# Building an Executable (Optional)

You can package the game using **PyInstaller**.

Install:

```bash
pip install pyinstaller
```

Build:

```bash
pyinstaller --onefile main.py
```

The executable will appear in the `dist/` folder.

---

# Credits

* Engine: **Python + Pygame**
* Assets: Custom sprites
* Gameplay inspiration: roguelike dungeon crawlers
