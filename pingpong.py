import pygame
import sys
import random
import cv2
import mediapipe as mp
import math  # Add this import

# ----------------------------
# Hand Tracker - Direct Movement
# ----------------------------
class HandTracker:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.3
        )
        
    def get_hand_x(self):
        success, img = self.cap.read()
        if not success:
            return None

        img = cv2.flip(img, 1)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = self.hands.process(img_rgb)

        if results.multi_hand_landmarks:
            for handLms in results.multi_hand_landmarks:
                h, w, _ = img.shape
                lm = handLms.landmark[8]
                cx = int(lm.x * w)
                return cx, w
        return None
    
    def __del__(self):
        self.cap.release()


# ----------------------------
# Game Setup
# ----------------------------
pygame.init()
pygame.mixer.init()
WIDTH, HEIGHT = 900, 650
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Air Pong - Ultimate Edition")
clock = pygame.time.Clock()

tracker = HandTracker()

# Fonts
font_big = pygame.font.SysFont(None, 72)
font = pygame.font.SysFont(None, 40)
font_small = pygame.font.SysFont(None, 24)
font_tiny = pygame.font.SysFont(None, 20)

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 50, 50)
GREEN = (50, 255, 50)
BLUE = (50, 50, 255)
YELLOW = (255, 255, 50)
PURPLE = (255, 50, 255)
CYAN = (50, 255, 255)
ORANGE = (255, 150, 50)
DARK_BLUE = (15, 15, 30)

game_state = "menu"
current_level = 1
max_level = 5
score = 0
high_score = 0

# Initialize game objects
paddle = None
balls = []
targets = []
powerups = []
particles = []
base_ball_speed = 5  # Base speed that stays constant for the level
ball_speed_multiplier = 1.0  # Temporary multiplier for power-ups
HAND_DETECTED_SPEED_MULTIPLIER = 1.35
HAND_NOT_DETECTED_SPEED_MULTIPLIER = 0.75

# Audio
hit_sound = None
try:
    # Background music (loops forever)
    pygame.mixer.music.load("bgmusic.mp3")
    pygame.mixer.music.set_volume(0.4)
    pygame.mixer.music.play(-1)
except Exception:
    pass

try:
    # Touch sound when ball hits paddle or target
    hit_sound = pygame.mixer.Sound("touchsound.mp3")
    hit_sound.set_volume(0.7)
except Exception:
    hit_sound = None


# ----------------------------
# Particle Effect Class
# ----------------------------
class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.vx = random.uniform(-3, 3)
        self.vy = random.uniform(-3, 3)
        self.color = color
        self.lifetime = 30
        self.size = random.randint(2, 5)
        
    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.lifetime -= 1
        return self.lifetime > 0
        
    def draw(self, screen):
        alpha = self.lifetime / 30
        size = int(self.size * alpha)
        if size > 0:
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), size)


# ----------------------------
# Power-up Class
# ----------------------------
class PowerUp:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 25, 25)
        self.type = random.choice(['expand', 'multiball', 'score'])
        self.color = {
            'expand': GREEN,
            'multiball': YELLOW,
            'score': PURPLE
        }[self.type]
        self.active = True
        self.float_offset = 0
        self.float_direction = 1
        self.duration = 300  # frames
        self.timer = 0
        
    def update(self):
        self.float_offset += 0.1 * self.float_direction
        if abs(self.float_offset) > 5:
            self.float_direction *= -1
            
    def draw(self, screen):
        y_offset = self.rect.y + self.float_offset
        pygame.draw.rect(screen, self.color, (self.rect.x, y_offset, self.rect.width, self.rect.height))
        # Draw icon
        if self.type == 'expand':
            pygame.draw.line(screen, WHITE, (self.rect.x + 5, y_offset + 12), (self.rect.x + 20, y_offset + 12), 3)
            pygame.draw.line(screen, WHITE, (self.rect.x + 12, y_offset + 5), (self.rect.x + 12, y_offset + 20), 3)
        elif self.type == 'multiball':
            pygame.draw.circle(screen, WHITE, (self.rect.x + 8, int(y_offset + 8)), 3)
            pygame.draw.circle(screen, WHITE, (self.rect.x + 17, int(y_offset + 17)), 3)
        elif self.type == 'score':
            text = font_tiny.render("+5", True, WHITE)
            screen.blit(text, (self.rect.x + 5, y_offset + 8))


# ----------------------------
# Reset Game
# ----------------------------
def reset_game():
    global paddle, balls, targets, score, particles, powerups, base_ball_speed, ball_speed_multiplier
    
    # Paddle at bottom
    paddle = pygame.Rect(WIDTH//2 - 60, HEIGHT - 40, 120, 20)
    
    # Ball setup with base speed
    balls = []
    main_ball = {
        'rect': pygame.Rect(WIDTH//2, HEIGHT//2, 20, 20),
        'speed': [base_ball_speed, -base_ball_speed],
        'color': WHITE
    }
    balls.append(main_ball)

    # Targets based on level (more bricks as level increases)
    targets = []
    # Classic brick-breaker feel: many more bricks on higher levels
    if current_level == 1:
        num_targets = 20
    elif current_level == 2:
        num_targets = 30
    elif current_level == 3:
        num_targets = 40
    elif current_level == 4:
        num_targets = 50
    else:  # level 5 and above
        num_targets = 60
    target_colors = [RED, ORANGE, YELLOW, GREEN, BLUE, PURPLE]
    
    # Arrange targets like a classic brick-breaker wall:
    # uniform bricks, tight rows, filling the top width.
    cols = 10  # fixed number of columns across the screen
    rows = max(1, (num_targets + cols - 1) // cols)  # ceil division based on num_targets

    side_margin = 10
    available_width = WIDTH - 2 * side_margin
    brick_width = available_width / cols
    brick_height = 25
    vertical_gap = 8

    start_y = 60

    created = 0
    for row in range(rows):
        y = start_y + row * (brick_height + vertical_gap)
        for col in range(cols):
            if created >= num_targets:
                break
            x = int(side_margin + col * brick_width)
            target = {
                'rect': pygame.Rect(x, y, int(brick_width), brick_height),
                # Brick-breaker style: each brick is 1-hit
                'health': 1,
                'color': target_colors[created % len(target_colors)],
                'points': 10 * current_level
            }
            targets.append(target)
            created += 1

    # Power-ups
    powerups = []
    
    # Effects
    particles = []
    score = 0
    ball_speed_multiplier = 1.0


# ----------------------------
# Level Configuration
# ----------------------------
def configure_level(level):
    global base_ball_speed, paddle, current_level, ball_speed_multiplier
    
    current_level = level
    
    if level == 1:
        base_ball_speed = 5
    elif level == 2:
        base_ball_speed = 7
    elif level == 3:
        base_ball_speed = 9
    elif level == 4:
        base_ball_speed = 12
    elif level == 5:
        base_ball_speed = 15
    
    ball_speed_multiplier = 1.0
    
    # Create paddle if it doesn't exist
    if paddle is None:
        paddle = pygame.Rect(WIDTH//2 - 60, HEIGHT - 40, 120, 20)
    else:
        # Adjust paddle size based on level (gets smaller as levels progress)
        paddle_width = max(60, 120 - (level * 10))
        paddle.width = paddle_width
    
    reset_game()


# ----------------------------
# Create particles
# ----------------------------
def create_particles(x, y, color, count=10):
    for _ in range(count):
        particles.append(Particle(x, y, color))


# ----------------------------
# Initialize first level
# ----------------------------
configure_level(1)


# ----------------------------
# Main Loop
# ----------------------------
# Keyboard control variables
key_left_pressed = False
key_right_pressed = False
paddle_speed = 12

while True:
    screen.fill(DARK_BLUE)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            tracker.__del__()
            pygame.quit()
            sys.exit()

        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()

            # MENU
            if game_state == "menu":
                # Define buttons here to avoid NameError
                level1_btn = pygame.Rect(WIDTH//2 - 100, 180, 200, 40)
                level2_btn = pygame.Rect(WIDTH//2 - 100, 230, 200, 40)
                level3_btn = pygame.Rect(WIDTH//2 - 100, 280, 200, 40)
                level4_btn = pygame.Rect(WIDTH//2 - 100, 330, 200, 40)
                level5_btn = pygame.Rect(WIDTH//2 - 100, 380, 200, 40)
                
                if level1_btn.collidepoint(mouse_pos):
                    configure_level(1)
                    game_state = "playing"
                elif level2_btn.collidepoint(mouse_pos):
                    configure_level(2)
                    game_state = "playing"
                elif level3_btn.collidepoint(mouse_pos):
                    configure_level(3)
                    game_state = "playing"
                elif level4_btn.collidepoint(mouse_pos):
                    configure_level(4)
                    game_state = "playing"
                elif level5_btn.collidepoint(mouse_pos):
                    configure_level(5)
                    game_state = "playing"

            # PLAYING
            elif game_state == "playing":
                menu_btn = pygame.Rect(WIDTH - 150, 20, 130, 40)
                if menu_btn.collidepoint(mouse_pos):
                    game_state = "menu"

            # GAME OVER
            elif game_state == "gameover":
                replay_btn = pygame.Rect(WIDTH//2 - 120, 280, 240, 50)
                next_level_btn = pygame.Rect(WIDTH//2 - 120, 340, 240, 50)
                menu_over_btn = pygame.Rect(WIDTH//2 - 120, 400, 240, 50)
                exit_btn = pygame.Rect(WIDTH//2 - 120, 460, 240, 50)
                
                if replay_btn.collidepoint(mouse_pos):
                    configure_level(current_level)
                    game_state = "playing"
                elif exit_btn.collidepoint(mouse_pos):
                    tracker.__del__()
                    pygame.quit()
                    sys.exit()
                elif menu_over_btn.collidepoint(mouse_pos):
                    game_state = "menu"
                elif next_level_btn.collidepoint(mouse_pos) and current_level < max_level:
                    configure_level(current_level + 1)
                    game_state = "playing"
            
            # LEVEL COMPLETE
            elif game_state == "level_complete":
                next_level_btn = pygame.Rect(WIDTH//2 - 120, 320, 240, 60)
                menu_over_btn = pygame.Rect(WIDTH//2 - 120, 400, 240, 60)
                
                if next_level_btn.collidepoint(mouse_pos):
                    configure_level(current_level + 1)
                    game_state = "playing"
                elif menu_over_btn.collidepoint(mouse_pos):
                    game_state = "menu"
            
            # GAME COMPLETE
            elif game_state == "game_complete":
                replay_btn = pygame.Rect(WIDTH//2 - 120, 350, 240, 60)
                menu_over_btn = pygame.Rect(WIDTH//2 - 120, 430, 240, 60)
                
                if replay_btn.collidepoint(mouse_pos):
                    configure_level(1)
                    game_state = "playing"
                elif menu_over_btn.collidepoint(mouse_pos):
                    game_state = "menu"
        
        # Keyboard controls - KEY DOWN (start moving)
        if event.type == pygame.KEYDOWN:
            if game_state == "playing" and paddle is not None:
                if event.key == pygame.K_LEFT:
                    key_left_pressed = True
                elif event.key == pygame.K_RIGHT:
                    key_right_pressed = True
        
        # Keyboard controls - KEY UP (stop moving)
        if event.type == pygame.KEYUP:
            if game_state == "playing" and paddle is not None:
                if event.key == pygame.K_LEFT:
                    key_left_pressed = False
                elif event.key == pygame.K_RIGHT:
                    key_right_pressed = False

    # ----------------------------
    # MENU SCREEN
    # ----------------------------
    if game_state == "menu":
        title = font_big.render("AIR PONG", True, CYAN)
        screen.blit(title, (WIDTH//2 - 200, 50))
        
        subtitle = font_small.render("ULTIMATE EDITION", True, YELLOW)
        screen.blit(subtitle, (WIDTH//2 - 100, 120))

        # Level buttons
        level1_btn = pygame.Rect(WIDTH//2 - 100, 180, 200, 40)
        level2_btn = pygame.Rect(WIDTH//2 - 100, 230, 200, 40)
        level3_btn = pygame.Rect(WIDTH//2 - 100, 280, 200, 40)
        level4_btn = pygame.Rect(WIDTH//2 - 100, 330, 200, 40)
        level5_btn = pygame.Rect(WIDTH//2 - 100, 380, 200, 40)

        pygame.draw.rect(screen, GREEN, level1_btn)
        pygame.draw.rect(screen, YELLOW, level2_btn)
        pygame.draw.rect(screen, ORANGE, level3_btn)
        pygame.draw.rect(screen, RED, level4_btn)
        pygame.draw.rect(screen, PURPLE, level5_btn)

        screen.blit(font_small.render("LEVEL 1 - EASY", True, BLACK), (WIDTH//2 - 65, 190))
        screen.blit(font_small.render("LEVEL 2 - MEDIUM", True, BLACK), (WIDTH//2 - 75, 240))
        screen.blit(font_small.render("LEVEL 3 - HARD", True, BLACK), (WIDTH//2 - 65, 290))
        screen.blit(font_small.render("LEVEL 4 - EXPERT", True, BLACK), (WIDTH//2 - 70, 340))
        screen.blit(font_small.render("LEVEL 5 - NIGHTMARE", True, BLACK), (WIDTH//2 - 90, 390))
        
        # Instructions
        inst_text = font_small.render("Move finger OR press LEFT/RIGHT arrows", True, WHITE)
        screen.blit(inst_text, (WIDTH//2 - 200, 480))
        
        high_score_text = font_small.render(f"High Score: {high_score}", True, YELLOW)
        screen.blit(high_score_text, (WIDTH//2 - 80, 540))

    # ----------------------------
    # PLAYING
    # ----------------------------
    elif game_state == "playing" and paddle is not None:
        # Hand control
        hand_data = tracker.get_hand_x()
        hand_detected = False
        
        if hand_data is not None:
            hand_x, cam_width = hand_data
            # Direct hand control overrides keyboard
            paddle.x = int(hand_x * WIDTH / cam_width)
            paddle.x = max(0, min(WIDTH - paddle.width, paddle.x))
            hand_detected = True
        else:
            # Keyboard control - continuous movement while key is pressed
            if key_left_pressed:
                paddle.x = max(0, paddle.x - paddle_speed)
            if key_right_pressed:
                paddle.x = min(WIDTH - paddle.width, paddle.x + paddle_speed)

        # Update ball speeds based on base speed and multiplier
        hand_speed_multiplier = (
            HAND_DETECTED_SPEED_MULTIPLIER
            if hand_detected
            else HAND_NOT_DETECTED_SPEED_MULTIPLIER
        )
        for ball in balls:
            # Keep speed magnitude consistent
            current_speed = math.sqrt(ball['speed'][0]**2 + ball['speed'][1]**2)
            target_speed = base_ball_speed * ball_speed_multiplier * hand_speed_multiplier
            
            if current_speed != target_speed and current_speed > 0:
                # Normalize and scale to target speed
                ball['speed'][0] = (ball['speed'][0] / current_speed) * target_speed
                ball['speed'][1] = (ball['speed'][1] / current_speed) * target_speed

        # Update balls
        for ball in balls[:]:
            ball['rect'].x += ball['speed'][0]
            ball['rect'].y += ball['speed'][1]

            # Wall bounce
            if ball['rect'].left <= 0 or ball['rect'].right >= WIDTH:
                ball['speed'][0] *= -1
                create_particles(ball['rect'].centerx, ball['rect'].centery, CYAN, 5)

            if ball['rect'].top <= 0:
                ball['speed'][1] *= -1
                create_particles(ball['rect'].centerx, ball['rect'].centery, CYAN, 5)

            # Paddle collision
            if ball['rect'].colliderect(paddle):
                if hit_sound is not None:
                    hit_sound.play()
                ball['speed'][1] *= -1
                # Add angle based on hit position, but maintain speed
                relative_intersect = (ball['rect'].centerx - paddle.centerx) / (paddle.width / 2)
                angle_change = relative_intersect * 2
                
                # Rotate velocity vector while maintaining speed
                current_speed = math.sqrt(ball['speed'][0]**2 + ball['speed'][1]**2)
                ball['speed'][0] += angle_change
                
                # Renormalize to maintain speed
                new_speed = math.sqrt(ball['speed'][0]**2 + ball['speed'][1]**2)
                if new_speed > 0:
                    ball['speed'][0] = (ball['speed'][0] / new_speed) * current_speed
                    ball['speed'][1] = (ball['speed'][1] / new_speed) * current_speed
                
                create_particles(ball['rect'].centerx, ball['rect'].centery, WHITE, 8)

            # Lose condition
            if ball['rect'].bottom >= HEIGHT:
                if len(balls) > 1:
                    balls.remove(ball)
                    create_particles(ball['rect'].centerx, ball['rect'].centery, RED, 15)
                else:
                    game_state = "gameover"
                    if score > high_score:
                        high_score = score

        # Update power-ups
        for powerup in powerups[:]:
            powerup.update()

            # Trigger power-up if EITHER the ball or paddle touches it,
            # so hitting it with the ball "does something" like classic brick breakers.
            activated = False

            # Check collision with any ball
            for ball in balls:
                if ball['rect'].colliderect(powerup.rect):
                    activated = True
                    break

            # Also allow paddle to activate (in case it reaches them)
            if not activated and paddle.colliderect(powerup.rect):
                activated = True

            if activated:
                if powerup.type == 'expand':
                    paddle.width = min(200, paddle.width + 40)
                elif powerup.type == 'multiball':
                    if len(balls) < 3:
                        new_ball = {
                            'rect': pygame.Rect(balls[0]['rect'].centerx, balls[0]['rect'].centery, 20, 20),
                            'speed': [-balls[0]['speed'][0], -balls[0]['speed'][1]],
                            'color': YELLOW
                        }
                        balls.append(new_ball)
                elif powerup.type == 'score':
                    score += 50

                powerups.remove(powerup)
                create_particles(powerup.rect.centerx, powerup.rect.centery, powerup.color, 15)

        # Target collision - brick-breaker style:
        # each ball can destroy at most ONE brick per frame.
        for ball in balls:
            for target in targets[:]:
                if ball['rect'].colliderect(target['rect']):
                    # Play hit sound when ball touches a brick
                    if hit_sound is not None:
                        hit_sound.play()

                    target['health'] -= 1
                    create_particles(ball['rect'].centerx, ball['rect'].centery, target['color'], 10)

                    if target['health'] <= 0:
                        targets.remove(target)
                        score += target['points']

                        # Spawn power-up randomly
                        if random.random() < 0.3:  # 30% chance
                            powerups.append(PowerUp(target['rect'].centerx, target['rect'].centery))

                        # Create explosion particles
                        create_particles(target['rect'].centerx, target['rect'].centery, target['color'], 20)

                        # Check if level complete
                        if len(targets) == 0:
                            if current_level < max_level:
                                game_state = "level_complete"
                            else:
                                game_state = "game_complete"

                    # Simple bounce - maintain speed, then stop checking other bricks
                    ball['speed'][1] *= -1
                    break

        # Update particles
        particles = [p for p in particles if p.update()]

        # Draw everything
        # Draw targets with health bars
        for target in targets:
            pygame.draw.rect(screen, target['color'], target['rect'])
            if target['health'] > 1:
                health_width = (target['rect'].width / 3) * target['health']
                health_rect = pygame.Rect(target['rect'].x, target['rect'].y - 8, health_width, 4)
                pygame.draw.rect(screen, GREEN, health_rect)

        # Draw balls
        for ball in balls:
            pygame.draw.ellipse(screen, ball['color'], ball['rect'])

        # Draw paddle
        
        pygame.draw.rect(screen, CYAN, paddle)

        # Draw power-ups
        for powerup in powerups:
            powerup.draw(screen)

        # Draw particles
        for particle in particles:
            particle.draw(screen)

        # UI Elements
        level_text = font_small.render(f"Level: {current_level}", True, WHITE)
        screen.blit(level_text, (20, 20))
        
        score_text = font_small.render(f"Score: {score}", True, WHITE)
        screen.blit(score_text, (20, 50))
        
        balls_text = font_small.render(f"Balls: {len(balls)}", True, WHITE)
        screen.blit(balls_text, (20, 80))

        # Control indicator
        if hand_detected:
            control_text = font_tiny.render("Hand control active", True, GREEN)
        else:
            control_text = font_tiny.render("Keyboard control active (hold arrows)", True, YELLOW)
        screen.blit(control_text, (20, 110))

        # Speed indicator
        if balls:
            speed_text = font_tiny.render(
                f"Speed: {base_ball_speed * ball_speed_multiplier * hand_speed_multiplier:.1f}",
                True,
                WHITE,
            )
            screen.blit(speed_text, (20, 130))

        # MENU BUTTON
        menu_btn = pygame.Rect(WIDTH - 150, 20, 130, 40)
        pygame.draw.rect(screen, (180, 180, 180), menu_btn)
        screen.blit(font_small.render("MENU", True, BLACK), (WIDTH - 120, 28))

    # ----------------------------
    # LEVEL COMPLETE
    # ----------------------------
    elif game_state == "level_complete":
        complete_text = font_big.render(f"LEVEL {current_level} COMPLETE!", True, GREEN)
        screen.blit(complete_text, (WIDTH//2 - 250, 200))
        
        next_level_btn = pygame.Rect(WIDTH//2 - 120, 320, 240, 60)
        menu_over_btn = pygame.Rect(WIDTH//2 - 120, 400, 240, 60)
        
        pygame.draw.rect(screen, GREEN, next_level_btn)
        pygame.draw.rect(screen, (150, 150, 150), menu_over_btn)
        
        screen.blit(font.render("NEXT LEVEL", True, BLACK), (WIDTH//2 - 60, 335))
        screen.blit(font.render("MENU", True, BLACK), (WIDTH//2 - 40, 415))

    # ----------------------------
    # GAME COMPLETE
    # ----------------------------
    elif game_state == "game_complete":
        win_text = font_big.render("CONGRATULATIONS!", True, YELLOW)
        screen.blit(win_text, (WIDTH//2 - 280, 150))
        
        complete_text = font.render("ALL LEVELS COMPLETE!", True, GREEN)
        screen.blit(complete_text, (WIDTH//2 - 180, 230))
        
        final_score = font.render(f"Final Score: {score}", True, WHITE)
        screen.blit(final_score, (WIDTH//2 - 120, 290))
        
        replay_btn = pygame.Rect(WIDTH//2 - 120, 350, 240, 60)
        menu_over_btn = pygame.Rect(WIDTH//2 - 120, 430, 240, 60)
        
        pygame.draw.rect(screen, GREEN, replay_btn)
        pygame.draw.rect(screen, (150, 150, 150), menu_over_btn)
        
        screen.blit(font.render("PLAY AGAIN", True, BLACK), (WIDTH//2 - 70, 365))
        screen.blit(font.render("MENU", True, BLACK), (WIDTH//2 - 40, 445))

    # ----------------------------
    # GAME OVER
    # ----------------------------
    elif game_state == "gameover":
        over_text = font_big.render("GAME OVER", True, RED)
        screen.blit(over_text, (WIDTH//2 - 200, 150))
        
        final_score = font.render(f"Score: {score}", True, WHITE)
        screen.blit(final_score, (WIDTH//2 - 70, 230))
        
        replay_btn = pygame.Rect(WIDTH//2 - 120, 280, 240, 50)
        next_level_btn = pygame.Rect(WIDTH//2 - 120, 340, 240, 50)
        menu_over_btn = pygame.Rect(WIDTH//2 - 120, 400, 240, 50)
        exit_btn = pygame.Rect(WIDTH//2 - 120, 460, 240, 50)

        pygame.draw.rect(screen, GREEN, replay_btn)
        pygame.draw.rect(screen, YELLOW, next_level_btn)
        pygame.draw.rect(screen, (150, 150, 150), menu_over_btn)
        pygame.draw.rect(screen, RED, exit_btn)

        screen.blit(font_small.render("REPLAY LEVEL", True, BLACK), (WIDTH//2 - 65, 295))
        screen.blit(font_small.render("NEXT LEVEL", True, BLACK), (WIDTH//2 - 60, 355))
        screen.blit(font_small.render("MENU", True, BLACK), (WIDTH//2 - 30, 415))
        screen.blit(font_small.render("EXIT", True, BLACK), (WIDTH//2 - 25, 475))

    pygame.display.flip()
    clock.tick(60)