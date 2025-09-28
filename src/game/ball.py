# ball.py
import pygame
from config import CONFIG # Import the config object

# --- Colors for Simple Mode ---
BALL_WHITE = (255, 255, 255)

class Ball:
    def __init__(self, pos, color=(255, 255, 255)):
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(0, 0)
        self.radius = 12
        self.color = color
        self.in_hole = False
        self.rect = pygame.Rect(0, 0, self.radius * 2, self.radius * 2)
        self.rect.center = self.pos

    def update(self, dt, walls):
        # UPDATED: Use friction from the config file
        self.vel *= CONFIG['friction']

        if self.vel.length() < 1: self.vel = pygame.Vector2(0, 0)
        self.pos += self.vel * dt
        self.rect.center = self.pos
        for wall in walls:
            if self.rect.colliderect(wall):
                closest_point = pygame.Vector2(max(wall.left, min(self.pos.x, wall.right)), max(wall.top, min(self.pos.y, wall.bottom)))
                collision_vec = self.pos - closest_point
                if 0 < collision_vec.length() < self.radius:
                    self.pos += collision_vec.normalize() * (self.radius - collision_vec.length())
                    if abs(collision_vec.x) > abs(collision_vec.y): self.vel.x *= -1
                    else: self.vel.y *= -1
        self.rect.center = self.pos

    def draw(self, surface: pygame.Surface, is_active: bool):
        """Draws the ball. If inactive, it's semi-transparent."""
        if not is_active:
            temp_surf = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(temp_surf, (*self.color, 128), (self.radius, self.radius), self.radius)
            surface.blit(temp_surf, self.rect.topleft)
        else:
            pygame.draw.circle(surface, self.color, self.pos, self.radius)

    def shoot(self, velocity: pygame.Vector2):
        self.vel = velocity

    def is_stationary(self) -> bool:
        return self.vel.length() < 1

    def stop(self):
        self.vel = pygame.Vector2(0,0)
        
    def putt_in_hole(self):
        self.stop()
        self.in_hole = True