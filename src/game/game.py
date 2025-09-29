# game.py
import pygame
import sys
import time
from collections import deque
from level import Level, LEVEL_DATA
from ball import Ball
import math
from shot_data import get_latest_shot_data, start_new_swing
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
POWER_BAR_BG = (30, 30, 30, 200)
POWER_BAR_BORDER = (200, 200, 200)
POWER_BAR_FILL = (255, 255, 0)

# Preview floor so path dots appear before strike in socket mode (configurable)
PREVIEW_MIN_POWER = float(CONFIG.get("preview_min_power", 0.35))

class Game:
    def __init__(self, sensor_server):
        pygame.init()
        self.sensor_server = sensor_server
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
        
        self.dt = 1.0 / PHYSICS_HZ  # physics tick
        self.accumulator = 0.0
        self.frame_dt = 1.0 / TARGET_FPS  # render tick, updated each frame
        
        self.control_mode = 'socket'
        self.show_path = True
        
        self.is_aiming = False
        self.mouse_down_pos = None

        self.current_shot_angle = 0.0
        self.current_shot_power = 0.0       # smoothed/final power for actual shot
        self.current_shot_power_raw = 0.0   # instantaneous preview power for UI/path
        self.direction_vector = pygame.Vector2(0)
        self.direction_vector_goal = pygame.Vector2(0)
        self.ui_power_preview = 0.0  # 0..1 for the on-screen power bar

        # Auto-shoot debounce and edge detect
        self.last_auto_shot_time = 0.0
        self.auto_shot_cooldown_s = 0.25
        self._last_shoot_flag = False

        # Aim lock from sensor
        self.aim_locked = False
        self.lock_angle = 0.0  # radians

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
        start_new_swing()  # reset aim/swing detector for new level
        self._last_shoot_flag = False
        self.aim_locked = False
        self.lock_angle = 0.0

    def run(self):
        while self.is_running:
            self.frame_dt = min(self.clock.tick(TARGET_FPS) / 1000.0, MAX_DELTA_TIME)
            self.accumulator += self.frame_dt

            self.process_input()

            if self.game_state == 'PLAYING':
                if self.control_mode == 'socket':
                    shot_data = get_latest_shot_data(self.sensor_server)
                    # Use locked angle when armed
                    self.aim_locked = bool(shot_data.get("aim_locked", False))
                    self.lock_angle = float(shot_data.get("angle_locked", self.lock_angle))
                    current_angle = float(shot_data.get("angle", 0.0))
                    self.current_shot_angle = self.lock_angle if self.aim_locked else current_angle

                    # Power
                    self.current_shot_power = float(shot_data.get("power", 0.0))
                    self.current_shot_power_raw = float(shot_data.get("power_raw", self.current_shot_power))

                    # Auto-shoot only on rising edge of shoot flag
                    shoot_flag = bool(shot_data.get("shoot", False))
                    if shoot_flag and not self._last_shoot_flag:
                        self.try_auto_shoot()
                    self._last_shoot_flag = shoot_flag

                while self.accumulator >= self.dt:
                    self.update(self.dt)
                    self.accumulator -= self.dt
            
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
        # Manual override with keyboard for testing
        active_ball = self.player_manager.get_active_ball()
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            power = self.current_shot_power * CONFIG['socket_max_power']
            if power > 0.0:
                vel_x = power * math.cos(self.current_shot_angle)
                vel_y = -power * math.sin(self.current_shot_angle)
                active_ball.shoot(pygame.Vector2(vel_x, vel_y))
                self.player_manager.record_shot()
                start_new_swing()
                self._last_shoot_flag = False
                self.aim_locked = False
                self.lock_angle = 0.0

    def try_auto_shoot(self):
        now = time.time()
        if (now - self.last_auto_shot_time) < self.auto_shot_cooldown_s:
            return
        active_ball = self.player_manager.get_active_ball()
        if not active_ball.is_stationary():
            return
        power = self.current_shot_power * CONFIG['socket_max_power']
        if power <= 0.0:
            return
        vel_x = power * math.cos(self.current_shot_angle)
        vel_y = -power * math.sin(self.current_shot_angle)
        active_ball.shoot(pygame.Vector2(vel_x, vel_y))
        self.player_manager.record_shot()
        self.last_auto_shot_time = now
        start_new_swing()
        self._last_shoot_flag = False
        self.aim_locked = False
        self.lock_angle = 0.0

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
        else:
            self.ui_power_preview = 0.0  # hide power when ball is moving
        
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
        power_normalized = 0.0

        if self.control_mode == 'socket':
            # Framerate-independent lerp toward current aim
            lerp_speed = 100.0 
            alpha = min(lerp_speed * self.frame_dt, 1.0)

            angle_for_draw = self.current_shot_angle
            direction_x = math.cos(angle_for_draw)
            direction_y = -math.sin(angle_for_draw)
            self.direction_vector_goal = pygame.Vector2(direction_x, direction_y)
            self.direction_vector = self.direction_vector.lerp(self.direction_vector_goal, alpha)

            # Use raw power for preview responsiveness
            power_normalized = max(0.0, min(1.0, float(self.current_shot_power_raw)))
            self.ui_power_preview = power_normalized

        elif self.control_mode == 'manual' and self.is_aiming:
            vec = pygame.Vector2(self.mouse_down_pos) - pygame.Vector2(pygame.mouse.get_pos())
            if vec.length() > 0:
                self.direction_vector = vec.normalize()
            sensitivity_divisor = 200 / CONFIG['manual_sensitivity']
            power_normalized = min(vec.length() / sensitivity_divisor, 1.0)
            self.ui_power_preview = power_normalized
        else:
            self.ui_power_preview = 0.0

        if self.direction_vector.length() > 0:
            line_end = active_ball.pos - self.direction_vector * (50 + (power_normalized * 150))
            pygame.draw.line(surface, AIM_LINE_COLOR, active_ball.pos, line_end, 3)

            if self.show_path:
                # Use a preview floor in socket mode so dots appear before the strike
                sim_power_norm = max(power_normalized, PREVIEW_MIN_POWER) if self.control_mode == 'socket' else power_normalized
                power = sim_power_norm * CONFIG['socket_max_power']

                sim_vel = self.direction_vector * power
                sim_pos = active_ball.pos.copy()
                path_points = []
                all_current_walls = self.level.get_all_walls()

                for i in range(150):
                    sim_vel *= CONFIG['friction']
                    if sim_vel.length() < 1:
                        break
                    sim_pos += sim_vel * self.dt
                    for wall in all_current_walls:
                        if wall.collidepoint(int(sim_pos.x), int(sim_pos.y)):
                            if sim_pos.x < wall.left + active_ball.radius or sim_pos.x > wall.right - active_ball.radius:
                                sim_vel.x *= -1
                            if sim_pos.y < wall.top + active_ball.radius or sim_pos.y > wall.bottom - active_ball.radius:
                                sim_vel.y *= -1
                    if i % 5 == 0:
                        path_points.append(sim_pos.copy())

                if len(path_points) > 1:
                    for point in path_points:
                        pygame.draw.circle(surface, PATH_COLOR, (int(point.x), int(point.y)), 2)

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

        self.draw_power_bar(surface)

    def draw_power_bar(self, surface: pygame.Surface):
        # Bottom-center power bar
        bar_width = 360
        bar_height = 22
        bar_x = (SCREEN_WIDTH - bar_width) // 2
        bar_y = SCREEN_HEIGHT - 90

        # Background with alpha
        bg_surf = pygame.Surface((bar_width, bar_height), pygame.SRCALPHA)
        bg_surf.fill(POWER_BAR_BG)
        surface.blit(bg_surf, (bar_x, bar_y))

        # Border
        pygame.draw.rect(surface, POWER_BAR_BORDER, pygame.Rect(bar_x, bar_y, bar_width, bar_height), 2, border_radius=6)

        # Fill
        fill_w = int(max(0.0, min(1.0, self.ui_power_preview)) * (bar_width - 4))
        if fill_w > 0:
            fill_rect = pygame.Rect(bar_x + 2, bar_y + 2, fill_w, bar_height - 4)
            pygame.draw.rect(surface, POWER_BAR_FILL, fill_rect, border_radius=4)

        # Label and percent
        label = self.font.render("Power", True, UI_TEXT_COLOR)
        pct_text = self.font.render(f"{int(self.ui_power_preview * 100):d}%", True, UI_TEXT_COLOR)
        label_rect = label.get_rect(midright=(bar_x - 10, bar_y + bar_height // 2))
        pct_rect = pct_text.get_rect(midleft=(bar_x + bar_width + 10, bar_y + bar_height // 2))
        surface.blit(label, label_rect)
        surface.blit(pct_text, pct_rect)

    def draw_button(self, surface, rect, text, color):
        pygame.draw.rect(surface, color, rect, border_radius=8)
        text_surf = self.font.render(text, True, BUTTON_TEXT_COLOR)
        text_rect = text_surf.get_rect(center=rect.center)
        surface.blit(text_surf, text_rect)

    def cleanup(self):
        pygame.quit()
        sys.exit()
