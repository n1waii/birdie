# 2D Mini-Golf Game

This is a 2D top-down mini-golf game built in Python with Pygame. It features a stable game loop, ball physics with wall collisions, and multiple levels loaded from an external JSON file.

## Features

- **Data-Driven Levels**: Course layouts are loaded from `levels.json`, making it easy to create and modify levels without touching the game code.
- **Physics-Based Gameplay**: A simple physics engine handles ball movement, friction, and collisions.
- **Mouse Controls**: An intuitive "slingshot" mechanic to aim and shoot the ball.
- **HUD**: On-screen display for FPS, current hole, par, and stroke count.

## Quick-Start

To run this project, place all files in a new directory.

**On macOS / Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 main.py
```
