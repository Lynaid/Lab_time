# Game Design Document
## Project: Lab Time

Author:  Makar Kopylov
Date:  22/02/2026

---

# 1. Game Concept

**Lab Time** is a 2D action roguelike game developed using **Python and Pygame**.  
The player explores procedurally generated laboratory floors filled with enemies, traps, and obstacles.

Each floor consists of interconnected rooms where the player must defeat enemies to unlock doors and progress further. The goal is to survive through multiple floors while improving abilities and defeating stronger enemies.

The game combines elements of:

- dungeon exploration
- real-time combat
- procedural level generation
- ability upgrades

Inspirations for the project include games such as **The Binding of Isaac**, **Enter the Gungeon**, and other top-down roguelike games.

Key gameplay loop:

1. Enter a room
2. Fight enemies
3. Clear the room
4. Collect rewards
5. Move to the next room
6. Reach and defeat the boss
7. Progress to the next floor

---

# 2. Main Screens

## Start Screen (Main Menu)

The start screen is the first interface shown to the player.

Main elements:

- Game logo
- Start Game button
- Exit button

The player can start a new run from this screen.

---

## Playing Screen (Gameplay)

The gameplay screen is where the main action happens.

Main elements:

- Player character
- Enemies
- Room environment (walls, floor, obstacles)
- Doors connecting rooms
- HUD interface

HUD displays:

- Player health
- Current weapon
- Ability cooldowns
- Enemy counter
- Floor seed

The player can move using keyboard controls and fight enemies using melee attacks and abilities.

---

## Win Screen

The win screen appears after defeating the final boss or completing the final floor.

Elements:

- Victory message
- Score or statistics
- Button to return to main menu

---

## Lose Screen

The lose screen appears when the player's health reaches zero.

Elements:

- "Game Over" message
- Option to restart
- Option to return to the main menu

---

# 3. Core Functionalities

The main functionalities of the game are listed below and correspond to the development backlog.

## Player Movement
- Move using WASD keys
- Directional aiming using arrow keys
- Collision detection with environment

## Combat System
- Melee attacks
- Hitboxes and damage system
- Enemy damage and knockback

## Enemy AI
Different enemy types with unique behaviors:

- Chaser enemies
- Shooter enemies
- Turrets
- Special enemies

Enemies can:
- move toward the player
- shoot projectiles
- avoid obstacles

## Room System
Each floor consists of multiple rooms:

- normal rooms
- boss room
- treasure room
- shop room
- secret room

Rooms unlock after all enemies are defeated.

## Procedural Level Generation
The dungeon layout is generated randomly each run using a seed system.

Features:

- grid-based map generation
- different room types
- connected room structure

## Abilities System

Player abilities include:

- Q ability
- R ability
- E ability
- F ability

Abilities have cooldown timers and special effects.

## Upgrade System

Players can obtain upgrades that improve abilities such as:

- faster projectiles
- stronger attacks
- increased health

## Visual Effects

The game includes:

- animated sprites
- attack effects
- projectile effects

## User Interface

The UI includes:

- health bar
- minimap
- ability indicators
- room information

---

# 4. Global Planning

The development of the game is divided into several stages.

## Day 1
- Define game concept
- Create game design document
- Set up project structure
- Basic player movement

## Day 2
- Implement combat system
- Add enemies
- Implement collision system

## Day 3
- Procedural room generation
- Door system
- Room transitions

## Day 4
- Ability system
- Upgrade system
- Player progression

## Day 5
- Add sprite animations
- Add visual effects
- Improve UI

## Day 6
- Boss fight implementation
- Final balancing
- Bug fixing
- Final presentation

---

# Conclusion

Lab Time aims to deliver a compact but functional roguelike experience built entirely with Python and Pygame. The focus of the project is on procedural gameplay, real-time combat mechanics, and modular system design that allows for further expansion of the game.