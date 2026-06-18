# AC's My Take Ultra Snake 0.1
# Python 3.14 compatible
# Requirements: pip install pygame

import pygame
import sys
import random
import math
import struct

# --- Initialization ---
pygame.init()
pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.mixer.init()

# Window Setup
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
GRID_SIZE = 25
GRID_WIDTH = WINDOW_WIDTH // GRID_SIZE
GRID_HEIGHT = WINDOW_HEIGHT // GRID_SIZE

screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("ac's my take ultra snake 0.1")
clock = pygame.time.Clock()

# --- PS5-Style Neon Graphics Colors ---
BG_COLOR = (10, 10, 15)
GRID_COLOR = (20, 20, 30)
SNAKE_COLOR = (0, 255, 200) # Cyan Neon
SNAKE_HEAD_COLOR = (255, 255, 255)
APPLE_COLOR = (255, 50, 80) # Red Neon
TEXT_COLOR = (255, 255, 255)
ACCENT_COLOR = (100, 150, 255)

# --- Sound Engine (Beeps n Boops PS5 SFX) ---
def generate_sound(frequency, duration, volume=0.5, wave_type='square'):
    sample_rate = 44100
    num_samples = int(sample_rate * duration)
    buffer = bytearray()
    
    for i in range(num_samples):
        t = float(i) / sample_rate
        if wave_type == 'square':
            value = int(volume * 32767.0 * (1.0 if math.sin(2 * math.pi * frequency * t) > 0 else -1.0))
        elif wave_type == 'sine':
            value = int(volume * 32767.0 * math.sin(2 * math.pi * frequency * t))
        elif wave_type == 'noise':
            value = int(volume * 32767.0 * (random.random() * 2 - 1))
        
        buffer += struct.pack('<h', value)
        
    return pygame.mixer.Sound(buffer=buffer)

# Generating SFX
sfx_beep = generate_sound(880, 0.08, 0.4, 'square') # Eat apple
sfx_boop = generate_sound(220, 0.05, 0.3, 'square') # Turn / Menu move
sfx_crash = generate_sound(110, 0.4, 0.6, 'noise')  # Game Over
sfx_start = generate_sound(440, 0.1, 0.4, 'sine')   # Start game

# --- Fonts ---
font_large = pygame.font.SysFont("consolas", 64, bold=True)
font_medium = pygame.font.SysFont("consolas", 36, bold=True)
font_small = pygame.font.SysFont("consolas", 24)

# --- Drawing Helpers (PS5 Style Glow) ---
def draw_glow_rect(surface, rect, color, glow_radius=4):
    for i in range(glow_radius, 0, -1):
        alpha = int(255 * (1 - i / (glow_radius + 1)) * 0.3)
        glow_rect = rect.inflate(i*2, i*2)
        s = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(s, (*color, alpha), s.get_rect(), border_radius=6)
        surface.blit(s, glow_rect.topleft)
    pygame.draw.rect(surface, color, rect, border_radius=4)

def draw_text_glow(surface, text, font, color, x, y):
    glow_surf = font.render(text, True, color)
    for i in range(3, 0, -1):
        glow_surf.set_alpha(50)
        surface.blit(glow_surf, (x+i, y))
        surface.blit(glow_surf, (x-i, y))
        surface.blit(glow_surf, (x, y+i))
        surface.blit(glow_surf, (x, y-i))
    glow_surf.set_alpha(255)
    surface.blit(glow_surf, (x, y))

# --- Game States ---
MENU = "MENU"
PLAY = "PLAY"
HELP = "HELP"
ABOUT = "ABOUT"
GAME_OVER = "GAME_OVER"

class Snake:
    def __init__(self):
        self.positions = [(GRID_WIDTH // 2, GRID_HEIGHT // 2)]
        self.direction = (1, 0)
        self.next_direction = (1, 0)
        self.grow = False
        self.move_timer = 0
        self.move_delay = 110  # Famicom speed in ms

    def update(self, dt):
        self.move_timer += dt
        if self.move_timer >= self.move_delay:
            self.move_timer = 0
            self.direction = self.next_direction
            head_x, head_y = self.positions[0]
            dx, dy = self.direction
            new_head = ((head_x + dx) % GRID_WIDTH, (head_y + dy) % GRID_HEIGHT)
            
            # Check Collision
            if new_head in self.positions:
                sfx_crash.play()
                return True # Game Over signal
            
            self.positions.insert(0, new_head)
            if not self.grow:
                self.positions.pop()
            else:
                self.grow = False
        return False

    def set_direction(self, direction):
        # Prevent reversing directly
        if (direction[0] * -1, direction[1] * -1) != self.direction:
            if self.next_direction != direction:
                sfx_boop.play()
            self.next_direction = direction

    def draw(self, surface):
        for i, pos in enumerate(self.positions):
            rect = pygame.Rect(pos[0] * GRID_SIZE, pos[1] * GRID_SIZE, GRID_SIZE, GRID_SIZE)
            color = SNAKE_HEAD_COLOR if i == 0 else SNAKE_COLOR
            draw_glow_rect(surface, rect, color, glow_radius=3)

class Apple:
    def __init__(self):
        self.position = (0, 0)
        self.randomize_position([])
        self.pulse = 0

    def randomize_position(self, snake_positions):
        while True:
            self.position = (random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1))
            if self.position not in snake_positions:
                break

    def update(self, dt):
        self.pulse += dt * 0.005

    def draw(self, surface):
        pulse_offset = math.sin(self.pulse) * 2
        rect = pygame.Rect(self.position[0] * GRID_SIZE - pulse_offset, 
                           self.position[1] * GRID_SIZE - pulse_offset, 
                           GRID_SIZE + pulse_offset*2, 
                           GRID_SIZE + pulse_offset*2)
        draw_glow_rect(surface, rect, APPLE_COLOR, glow_radius=6)

# --- Main Application ---
def main():
    state = MENU
    menu_options = ["Play Game", "Help", "About", "Exit Game"]
    selected_option = 0
    
    snake = None
    apple = None
    score = 0

    running = True
    while running:
        dt = clock.tick(60) # Locked to 60 FPS
        
        # --- Events ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                
            if event.type == pygame.KEYDOWN:
                if state == MENU:
                    if event.key == pygame.K_UP:
                        selected_option = (selected_option - 1) % len(menu_options)
                        sfx_boop.play()
                    elif event.key == pygame.K_DOWN:
                        selected_option = (selected_option + 1) % len(menu_options)
                        sfx_boop.play()
                    elif event.key == pygame.K_RETURN:
                        if selected_option == 0: # Play
                            snake = Snake()
                            apple = Apple()
                            apple.randomize_position(snake.positions)
                            score = 0
                            state = PLAY
                            sfx_start.play()
                        elif selected_option == 1: # Help
                            state = HELP
                            sfx_boop.play()
                        elif selected_option == 2: # About
                            state = ABOUT
                            sfx_boop.play()
                        elif selected_option == 3: # Exit
                            running = False
                    elif event.key == pygame.K_ESCAPE:
                        running = False

                elif state == PLAY:
                    if event.key == pygame.K_UP or event.key == pygame.K_w:
                        snake.set_direction((0, -1))
                    elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                        snake.set_direction((0, 1))
                    elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
                        snake.set_direction((-1, 0))
                    elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                        snake.set_direction((1, 0))
                    elif event.key == pygame.K_ESCAPE:
                        state = MENU
                        sfx_boop.play()

                elif state in [HELP, ABOUT, GAME_OVER]:
                    if event.key in [pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_SPACE]:
                        state = MENU
                        sfx_boop.play()

        # --- Updates ---
        if state == PLAY:
            game_over = snake.update(dt)
            if game_over:
                state = GAME_OVER
            
            # Check apple collision
            if snake.positions[0] == apple.position:
                snake.grow = True
                score += 10
                apple.randomize_position(snake.positions)
                sfx_beep.play()
            
            apple.update(dt)

        # --- Drawing ---
        screen.fill(BG_COLOR)
        
        # Draw Grid
        for x in range(0, WINDOW_WIDTH, GRID_SIZE):
            pygame.draw.line(screen, GRID_COLOR, (x, 0), (x, WINDOW_HEIGHT))
        for y in range(0, WINDOW_HEIGHT, GRID_SIZE):
            pygame.draw.line(screen, GRID_COLOR, (0, y), (WINDOW_WIDTH, y))

        if state == MENU:
            # Logo
            logo_text = "AC's ULTRA SNAKE"
            logo_surf = font_large.render(logo_text, True, SNAKE_COLOR)
            logo_rect = logo_surf.get_rect(center=(WINDOW_WIDTH // 2, 150))
            draw_text_glow(screen, logo_text, font_large, SNAKE_COLOR, logo_rect.left, logo_rect.top)
            
            # Menu Options
            for i, option in enumerate(menu_options):
                color = SNAKE_HEAD_COLOR if i == selected_option else ACCENT_COLOR
                text_surf = font_medium.render(option, True, color)
                text_rect = text_surf.get_rect(center=(WINDOW_WIDTH // 2, 300 + i * 60))
                screen.blit(text_surf, text_rect)
                
                # Cursor
                if i == selected_option:
                    cursor_rect = pygame.Rect(text_rect.left - 30, text_rect.centery - 5, 10, 10)
                    draw_glow_rect(screen, cursor_rect, SNAKE_COLOR, glow_radius=2)

            # Footer
            footer_surf = font_small.render("v0.1 | 60 FPS | Python 3.14 | Beeps n Boops Engine", True, ACCENT_COLOR)
            screen.blit(footer_surf, (20, WINDOW_HEIGHT - 40))

        elif state == PLAY:
            snake.draw(screen)
            apple.draw(screen)
            
            # Score HUD
            score_surf = font_medium.render(f"SCORE: {score}", True, SNAKE_COLOR)
            screen.blit(score_surf, (20, 20))

        elif state == HELP:
            title_surf = font_large.render("HELP", True, SNAKE_COLOR)
            screen.blit(title_surf, (WINDOW_WIDTH//2 - title_surf.get_width()//2, 100))
            
            lines = [
                "Use ARROW KEYS or WASD to move.",
                "Eat the red apple to grow and score.",
                "Do not hit yourself.",
                "",
                "Press ENTER or ESC to return to Main Menu."
            ]
            for i, line in enumerate(lines):
                s = font_small.render(line, True, TEXT_COLOR)
                screen.blit(s, (WINDOW_WIDTH//2 - s.get_width()//2, 250 + i * 40))

        elif state == ABOUT:
            title_surf = font_large.render("ABOUT", True, SNAKE_COLOR)
            screen.blit(title_surf, (WINDOW_WIDTH//2 - title_surf.get_width()//2, 100))
            
            lines = [
                "AC's My Take Ultra Snake 0.1",
                "Built with pure Python 3.14 & Pygame.",
                "Features PS5-style neon graphics & synthesized SFX.",
                "",
                "Press ENTER or ESC to return to Main Menu."
            ]
            for i, line in enumerate(lines):
                s = font_small.render(line, True, TEXT_COLOR)
                screen.blit(s, (WINDOW_WIDTH//2 - s.get_width()//2, 250 + i * 40))

        elif state == GAME_OVER:
            go_surf = font_large.render("GAME OVER", True, APPLE_COLOR)
            screen.blit(go_surf, (WINDOW_WIDTH//2 - go_surf.get_width()//2, 200))
            
            score_surf = font_medium.render(f"Final Score: {score}", True, TEXT_COLOR)
            screen.blit(score_surf, (WINDOW_WIDTH//2 - score_surf.get_width()//2, 300))
            
            prompt_surf = font_small.render("Press ENTER to return to Menu", True, ACCENT_COLOR)
            screen.blit(prompt_surf, (WINDOW_WIDTH//2 - prompt_surf.get_width()//2, 400))

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()