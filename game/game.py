# game.py
import pygame
import sys
from collections import deque
from level import Level, LEVEL_DATA
from ball import Ball
import math
from shot_data import get_latest_shot_data
from config import CONFIG
from player import PlayerManager

# --- Constants ---
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
TARGET_FPS = 60
PHYSICS_HZ = 240
MAX_DELTA_TIME = 0.1

# --- Colors ---
COURSE_GREEN = (34, 139, 34)
UI_TEXT_COLOR = (240, 240, 240)
AIM_LINE_COLOR = (255, 255, 0)
PATH_COLOR = (255, 255, 255, 150)
BUTTON_BG_COLOR = (60, 60, 60)
BUTTON_HOVER_COLOR = (90, 90, 90)
BUTTON_TEXT_COLOR = (255, 255, 255)
OVERLAY_COLOR = (0, 0, 0, 180)
HUD_BG_COLOR = (40, 40, 40, 200)
HUD_HIGHLIGHT_COLOR = (80, 80, 80, 200)

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("2D Mini-Golf")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.title_font = pygame.font.Font(None, 96)
        self.is_running = True
        
        # --- State Management ---
        self.game_state = 'START_MENU'
        self.player_manager = PlayerManager()
        self.final_scores = {}
        self.next_level_index = 1
        
        self.dt = 1.0 / PHYSICS_HZ 
        self.accumulator = 0.0
        
        self.control_mode = 'socket'
        self.show_path = True
        
        self.is_aiming = False
        self.mouse_down_pos = None

        self.current_shot_angle = 0.0
        self.current_shot_power = 0.0

        # --- UI Buttons ---
        self.mode_button_rect = pygame.Rect(SCREEN_WIDTH - 220, SCREEN_HEIGHT - 110, 210, 40)
        self.path_button_rect = pygame.Rect(SCREEN_WIDTH - 220, SCREEN_HEIGHT - 60, 210, 40)
        self.p1_button_rect = pygame.Rect(SCREEN_WIDTH/2 - 100, SCREEN_HEIGHT/2, 200, 50)
        self.p2_button_rect = pygame.Rect(SCREEN_WIDTH/2 - 100, SCREEN_HEIGHT/2 + 70, 200, 50)
        
        self.current_level_index = 1

    def start_game(self, num_players):
        """Initializes game state for a new game."""
        self.player_manager.setup_new_game(num_players)
        self.current_level_index = 1
        self.load_level(self.current_level_index)
        self.game_state = 'PLAYING'

    def load_level(self, level_index):
        if not LEVEL_DATA: self.is_running = False; return
        if level_index not in LEVEL_DATA: level_index = 1
        
        self.current_level_index = level_index
        level_info = LEVEL_DATA[self.current_level_index]
        self.level = Level(level_info)
        
        self.player_manager.prepare_for_level(self.level.start_pos)

    def run(self):
        while self.is_running:
            raw_delta_time = self.clock.tick(TARGET_FPS) / 1000.0
            delta_time = min(raw_delta_time, MAX_DELTA_TIME)
            self.accumulator += delta_time

            self.process_input()

            if self.game_state == 'PLAYING':
                if self.control_mode == 'socket':
                    shot_data = get_latest_shot_data()
                    self.current_shot_angle = shot_data["angle"]
                    self.current_shot_power = shot_data["power"]
                
                while self.accumulator >= self.dt: self.update(self.dt); self.accumulator -= self.dt
            
            self.render(self.screen)
        self.cleanup()

    def process_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                self.is_running = False; return

            if self.game_state == 'START_MENU': self.handle_menu_input(event)
            elif self.game_state == 'PLAYING': self.handle_playing_input(event)
            elif self.game_state == 'SCORE_SCREEN': self.handle_scorescreen_input(event)
                
    def handle_menu_input(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.p1_button_rect.collidepoint(event.pos): self.start_game(1)
            elif self.p2_button_rect.collidepoint(event.pos): self.start_game(2)
    
    def handle_scorescreen_input(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            self.load_level(self.next_level_index)
            self.game_state = 'PLAYING'

    def handle_playing_input(self, event):
        active_ball = self.player_manager.get_active_ball()
        if not active_ball.is_stationary(): return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.mode_button_rect.collidepoint(event.pos):
                self.control_mode = 'manual' if self.control_mode == 'socket' else 'socket'; self.is_aiming = False; return
            if self.path_button_rect.collidepoint(event.pos):
                self.show_path = not self.show_path; return

        if self.control_mode == 'manual': self.handle_manual_input(event)
        else: self.handle_socket_input(event)

    def handle_manual_input(self, event):
        active_ball = self.player_manager.get_active_ball()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.is_aiming = True; self.mouse_down_pos = event.pos
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.is_aiming:
            self.is_aiming = False
            direction_vector = pygame.Vector2(self.mouse_down_pos) - pygame.Vector2(event.pos)
            if direction_vector.length() > 0:
                sensitivity_divisor = 200 / CONFIG['manual_sensitivity']
                power_normalized = direction_vector.length() / sensitivity_divisor
                final_power = min(power_normalized, 1.0) * CONFIG['socket_max_power']
                velocity = direction_vector.normalize() * final_power
                active_ball.shoot(velocity)
                self.player_manager.record_shot()
    
    def handle_socket_input(self, event):
        active_ball = self.player_manager.get_active_ball()
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            power = self.current_shot_power * CONFIG['socket_max_power']
            vel_x = power * math.cos(self.current_shot_angle)
            vel_y = -power * math.sin(self.current_shot_angle)
            active_ball.shoot(pygame.Vector2(vel_x, vel_y))
            self.player_manager.record_shot()

    def update(self, dt: float):
        self.level.update()
        all_walls = self.level.get_all_walls()
        
        active_ball = self.player_manager.get_active_ball()
        was_moving = not active_ball.is_stationary()

        for ball in self.player_manager.balls.values():
            if not ball.in_hole:
                ball.update(dt, all_walls)
        
        stopped_moving = was_moving and active_ball.is_stationary()

        if self.level.hole_rect.colliderect(active_ball.rect) and active_ball.vel.length() < 20:
            self.player_manager.finish_turn_for_player()
            stopped_moving = True

        if self.player_manager.all_players_finished():
            self.final_scores = self.player_manager.scores.copy()
            self.next_level_index = self.current_level_index + 1
            if self.next_level_index > len(LEVEL_DATA): self.next_level_index = 1
            self.game_state = 'SCORE_SCREEN'
        elif stopped_moving:
            self.player_manager.next_turn()

    def render(self, surface: pygame.Surface):
        if self.game_state == 'START_MENU': self.draw_start_menu(surface)
        elif self.game_state == 'PLAYING': self.draw_playing_state(surface)
        elif self.game_state == 'SCORE_SCREEN':
            self.draw_playing_state(surface) 
            self.draw_score_screen(surface)
        pygame.display.flip()

    def draw_start_menu(self, surface: pygame.Surface):
        surface.fill(COURSE_GREEN)
        title_text = self.title_font.render("2D Mini-Golf", True, UI_TEXT_COLOR)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/3))
        surface.blit(title_text, title_rect)
        
        mouse_pos = pygame.mouse.get_pos()
        p1_color = BUTTON_HOVER_COLOR if self.p1_button_rect.collidepoint(mouse_pos) else BUTTON_BG_COLOR
        p2_color = BUTTON_HOVER_COLOR if self.p2_button_rect.collidepoint(mouse_pos) else BUTTON_BG_COLOR
        self.draw_button(surface, self.p1_button_rect, "1 Player", p1_color)
        self.draw_button(surface, self.p2_button_rect, "2 Players", p2_color)

    def draw_playing_state(self, surface: pygame.Surface):
        self.draw_background(surface)
        self.level.draw(surface, None, 'simple')
        
        active_ball = self.player_manager.get_active_ball()
        if active_ball.is_stationary():
            self.draw_aiming_elements(surface, active_ball)
        
        for player_num, ball in self.player_manager.balls.items():
            if not ball.in_hole:
                is_active = (player_num == self.player_manager.current_player_idx)
                ball.draw(surface, is_active)
        
        self.draw_hud(surface)

    def draw_score_screen(self, surface: pygame.Surface):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill(OVERLAY_COLOR)
        surface.blit(overlay, (0, 0))
        
        title_text = f"Hole {self.current_level_index} Complete!"
        title_surf = self.title_font.render(title_text, True, UI_TEXT_COLOR)
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/4))
        surface.blit(title_surf, title_rect)
        
        score_terms = { -2: "Eagle!", -1: "Birdie!", 0: "Par", 1: "Bogey", 2: "Double Bogey" }

        for i in range(1, self.player_manager.num_players + 1):
            strokes = self.final_scores[i]
            score_diff = strokes - self.level.par
            term = score_terms.get(score_diff, f"+{score_diff}")
            player_text = f"Player {i}: {strokes} strokes ({term})"
            player_surf = self.font.render(player_text, True, UI_TEXT_COLOR)
            player_rect = player_surf.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2 + (i-1)*50))
            surface.blit(player_surf, player_rect)
            
        continue_text = self.font.render("Press SPACE to continue", True, UI_TEXT_COLOR)
        continue_rect = continue_text.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT * 0.8))
        surface.blit(continue_text, continue_rect)

    def draw_background(self, surface: pygame.Surface):
        surface.fill(COURSE_GREEN)

    def draw_aiming_elements(self, surface: pygame.Surface, active_ball: Ball):
        direction_vector = pygame.Vector2(0)
        power_normalized = 0.0

        if self.control_mode == 'socket':
            direction_x = math.cos(self.current_shot_angle); direction_y = -math.sin(self.current_shot_angle)
            direction_vector.update(direction_x, direction_y); power_normalized = self.current_shot_power
        elif self.control_mode == 'manual' and self.is_aiming:
            vec = pygame.Vector2(self.mouse_down_pos) - pygame.Vector2(pygame.mouse.get_pos())
            if vec.length() > 0: direction_vector = vec.normalize()
            sensitivity_divisor = 200 / CONFIG['manual_sensitivity']
            power_normalized = min(vec.length() / sensitivity_divisor, 1.0)

        if direction_vector.length() > 0:
            line_end = active_ball.pos - direction_vector * (50 + (power_normalized * 150))
            pygame.draw.line(surface, AIM_LINE_COLOR, active_ball.pos, line_end, 3)
            if self.show_path:
                power = power_normalized * CONFIG['socket_max_power']
                sim_vel = direction_vector * power; sim_pos = active_ball.pos.copy(); path_points = []
                all_current_walls = self.level.get_all_walls()
                for i in range(150):
                    sim_vel *= CONFIG['friction']
                    if sim_vel.length() < 1: break
                    sim_pos += sim_vel * self.dt
                    for wall in all_current_walls:
                        if wall.collidepoint(sim_pos):
                            if sim_pos.x < wall.left + active_ball.radius or sim_pos.x > wall.right-active_ball.radius: sim_vel.x *= -1
                            if sim_pos.y < wall.top + active_ball.radius or sim_pos.y > wall.bottom-active_ball.radius: sim_vel.y *= -1
                    if i % 5 == 0: path_points.append(sim_pos.copy())
                if len(path_points) > 1:
                    for point in path_points: pygame.draw.circle(surface, PATH_COLOR, point, 2)

    def draw_hud(self, surface: pygame.Surface):
        info_texts = [f"Hole: {self.current_level_index}", f"Par: {self.level.par}"]
        for i, text in enumerate(info_texts):
            text_surface = self.font.render(text, True, UI_TEXT_COLOR)
            surface.blit(text_surface, (10, 10 + i * 35))
        
        for i in range(1, self.player_manager.num_players + 1):
            is_active = (i == self.player_manager.current_player_idx)
            box_color = HUD_HIGHLIGHT_COLOR if is_active else HUD_BG_COLOR
            box_rect = pygame.Rect(10, SCREEN_HEIGHT - (self.player_manager.num_players - i + 1) * 70, 240, 60)
            
            box_surf = pygame.Surface(box_rect.size, pygame.SRCALPHA)
            box_surf.fill(box_color)
            surface.blit(box_surf, box_rect.topleft)

            player_text_surf = self.font.render(f"Player {i}", True, UI_TEXT_COLOR)
            strokes_text_surf = self.font.render(f"{self.player_manager.scores[i]} Strokes", True, UI_TEXT_COLOR)
            
            player_text_rect = player_text_surf.get_rect(midleft=(box_rect.left + 15, box_rect.centery))
            strokes_text_rect = strokes_text_surf.get_rect(midright=(box_rect.right - 15, box_rect.centery))
            
            surface.blit(player_text_surf, player_text_rect)
            surface.blit(strokes_text_surf, strokes_text_rect)

        mouse_pos = pygame.mouse.get_pos()
        mode_text = f"Mode: {self.control_mode.capitalize()}"; path_text = f"Path: {'On' if self.show_path else 'Off'}"
        mode_color = BUTTON_HOVER_COLOR if self.mode_button_rect.collidepoint(mouse_pos) else BUTTON_BG_COLOR
        path_color = BUTTON_HOVER_COLOR if self.path_button_rect.collidepoint(mouse_pos) else BUTTON_BG_COLOR
        self.draw_button(surface, self.mode_button_rect, mode_text, mode_color)
        self.draw_button(surface, self.path_button_rect, path_text, path_color)

    def draw_button(self, surface, rect, text, color):
        pygame.draw.rect(surface, color, rect, border_radius=8)
        text_surf = self.font.render(text, True, BUTTON_TEXT_COLOR)
        text_rect = text_surf.get_rect(center=rect.center)
        surface.blit(text_surf, text_rect)

    def cleanup(self):
        pygame.quit()
        sys.exit()