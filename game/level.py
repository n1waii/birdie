# level.py
import pygame
import json
import time
import math

# --- Colors for Simple Mode ---
WALL_COLOR = (139, 69, 19)
HOLE_BLACK = (0, 0, 0)
# --- Colors for Enhanced Mode ---
WALL_SHADOW_COLOR = (0, 0, 0, 100)
HOLE_RADIUS = 18

class MovingWall:
    """Represents a single wall that moves between two points."""
    def __init__(self, rect_data, end_pos_data, speed):
        self.start_pos = pygame.Vector2(rect_data[0], rect_data[1])
        self.end_pos = pygame.Vector2(end_pos_data)
        self.speed = speed
        self.rect = pygame.Rect(rect_data)
    
    def update(self):
        """Updates the wall's position using a smooth sine wave oscillation."""
        lerp_t = (math.sin(time.time() * self.speed) + 1) / 2
        new_pos = self.start_pos.lerp(self.end_pos, lerp_t)
        self.rect.topleft = new_pos

def load_level_data(filepath: str) -> dict:
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            return {int(k): v for k, v in data.items()}
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading level data: {e}")
        return {}

class Level:
    """Stores and draws the layout for a single golf hole."""
    def __init__(self, level_data: dict):
        self.walls = [pygame.Rect(r) for r in level_data["walls"]]
        self.moving_walls = []
        if "moving_walls" in level_data:
            for mw_data in level_data["moving_walls"]:
                self.moving_walls.append(
                    MovingWall(mw_data["rect"], mw_data["end_pos"], mw_data["speed"])
                )

        self.start_pos = pygame.Vector2(level_data["start"])
        self.hole_pos = pygame.Vector2(level_data["hole"])
        self.hole_rect = pygame.Rect(self.hole_pos.x - HOLE_RADIUS, self.hole_pos.y - HOLE_RADIUS, HOLE_RADIUS * 2, HOLE_RADIUS * 2)
        self.par = level_data["par"]

    def update(self):
        """Update all moving elements in the level."""
        for wall in self.moving_walls:
            wall.update()

    def get_all_walls(self):
        """Return a combined list of static and moving wall rects for physics."""
        return self.walls + [mw.rect for mw in self.moving_walls]

    def draw(self, surface: pygame.Surface, assets: dict, graphics_mode: str):
        """Draws the level based on the current graphics mode."""
        all_wall_rects = self.get_all_walls()

        if graphics_mode == 'enhanced' and assets:
            # --- Enhanced Drawing ---
            for wall_rect in all_wall_rects:
                shadow_rect = wall_rect.copy()
                shadow_rect.move_ip(5, 5)
                pygame.draw.rect(surface, WALL_SHADOW_COLOR, shadow_rect)
            
            for wall_rect in all_wall_rects:
                pygame.draw.rect(surface, WALL_COLOR, wall_rect)
            
            hole_rect = assets['hole'].get_rect(center=self.hole_pos)
            surface.blit(assets['hole'], hole_rect)
            
            flag_rect = assets['flag'].get_rect(midbottom=self.hole_pos + pygame.Vector2(0, 5))
            surface.blit(assets['flag'], flag_rect)
        else:
            # --- Simple Drawing (Fallback) ---
            for wall_rect in all_wall_rects:
                pygame.draw.rect(surface, WALL_COLOR, wall_rect)
            pygame.draw.circle(surface, HOLE_BLACK, self.hole_pos, HOLE_RADIUS)

LEVEL_DATA = load_level_data('levels.json')