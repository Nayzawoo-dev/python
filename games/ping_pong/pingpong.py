import pygame
import sys
import random
import cv2
import mediapipe as mp
import math

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
pygame.mixer.pre_init(48000, -16, 2, 2048)
pygame.mixer.init()
WIDTH, HEIGHT = 900, 650
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Air Pong - Ultimate Edition")
clock = pygame.time.Clock()

tracker = HandTracker()

font_big   = pygame.font.SysFont(None, 72)
font       = pygame.font.SysFont(None, 40)
font_small = pygame.font.SysFont(None, 24)
font_tiny  = pygame.font.SysFont(None, 20)

WHITE      = (255, 255, 255)
BLACK      = (0,   0,   0)
RED        = (255, 50,  50)
GREEN      = (50,  220, 100)
BLUE       = (50,  100, 255)
YELLOW     = (255, 230, 50)
PURPLE     = (200, 50,  255)
CYAN       = (50,  230, 255)
ORANGE     = (255, 140, 50)
DARK_BLUE  = (8,   10,  22)
NEON_PINK  = (255, 20,  147)
NEON_GREEN = (57,  255, 20)


def darken(color, factor=0.45):
    return tuple(max(0, int(c * factor)) for c in color)


def lighten(color, factor=1.5):
    return tuple(min(255, int(c * factor)) for c in color)


def draw_glow(surface, color, center, radius, layers=6):
    glow_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for i in range(layers, 0, -1):
        alpha = int(60 * (i / layers))
        r = int(radius * (i / layers))
        pygame.draw.circle(glow_surf, (*color, alpha), (radius, radius), r)
    surface.blit(glow_surf, (center[0] - radius, center[1] - radius),
                 special_flags=pygame.BLEND_RGBA_ADD)


def draw_glass_button(surface, rect, base_color, border_color, text_surf,
                      border_radius=14, shadow_offset=4):
    shadow_rect = rect.move(shadow_offset, shadow_offset)
    shadow_surf = pygame.Surface((shadow_rect.width, shadow_rect.height), pygame.SRCALPHA)
    pygame.draw.rect(shadow_surf, (0, 0, 0, 80),
                     (0, 0, shadow_rect.width, shadow_rect.height),
                     border_radius=border_radius)
    surface.blit(shadow_surf, shadow_rect.topleft)

    glass_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    r, g, b = base_color
    pygame.draw.rect(glass_surf, (r, g, b, 110),
                     (0, 0, rect.width, rect.height),
                     border_radius=border_radius)
    highlight = pygame.Surface((rect.width - 4, rect.height // 2), pygame.SRCALPHA)
    highlight.fill((255, 255, 255, 20))
    glass_surf.blit(highlight, (2, 2))
    surface.blit(glass_surf, rect.topleft)

    pygame.draw.rect(surface, border_color, rect, 2, border_radius=border_radius)

    tx = rect.centerx - text_surf.get_width() // 2
    ty = rect.centery - text_surf.get_height() // 2
    surface.blit(text_surf, (tx, ty))


BRICK_DEPTH = 7


def draw_3d_brick(surface, color, rect):
    x, y, w, h = rect.x, rect.y, rect.width, rect.height
    d = BRICK_DEPTH

    bottom_color = darken(color, 0.35)
    bottom_pts = [
        (x,         y + h),
        (x + d,     y + h + d),
        (x + w + d, y + h + d),
        (x + w,     y + h),
    ]
    pygame.draw.polygon(surface, bottom_color, bottom_pts)

    right_color = darken(color, 0.50)
    right_pts = [
        (x + w,     y),
        (x + w + d, y + d),
        (x + w + d, y + h + d),
        (x + w,     y + h),
    ]
    pygame.draw.polygon(surface, right_color, right_pts)

    pygame.draw.rect(surface, color, rect)

    highlight_color = lighten(color, 1.6)
    pygame.draw.line(surface, highlight_color, (x, y),     (x + w - 1, y),     2)
    pygame.draw.line(surface, highlight_color, (x, y),     (x, y + h - 1),     2)

    bevel_color = darken(color, 0.75)
    pygame.draw.line(surface, bevel_color, (x + w - 1, y + 1), (x + w - 1, y + h - 1), 1)
    pygame.draw.line(surface, bevel_color, (x + 1, y + h - 1), (x + w - 1, y + h - 1), 1)


def draw_paddle(surface, rect):
    x, y, w, h = rect.x, rect.y, rect.width, rect.height

    # Slim rectangular drop-shadow (no giant circle)
    shadow_surf = pygame.Surface((w + 10, h + 6), pygame.SRCALPHA)
    pygame.draw.rect(shadow_surf, (0, 200, 255, 50),
                     (0, 0, w + 10, h + 6), border_radius=10)
    surface.blit(shadow_surf, (x - 5, y + 3))

    # Subtle rectangular edge glow — stays tight to the paddle shape
    for i in range(4, 0, -1):
        glow_alpha = 18 * i
        expand     = i * 3
        gs = pygame.Surface((w + expand * 2, h + expand * 2), pygame.SRCALPHA)
        pygame.draw.rect(gs, (50, 230, 255, glow_alpha),
                         (0, 0, w + expand * 2, h + expand * 2), border_radius=10)
        surface.blit(gs, (x - expand, y - expand))

    # Paddle body
    top_color   = (80, 240, 255)
    base_color2 = (30, 170, 210)
    pygame.draw.rect(surface, base_color2, rect, border_radius=8)
    top_half = pygame.Rect(x, y, w, h // 2)
    tsurf = pygame.Surface((top_half.width, top_half.height), pygame.SRCALPHA)
    pygame.draw.rect(tsurf, (*top_color, 160), (0, 0, top_half.width, top_half.height),
                     border_radius=8)
    surface.blit(tsurf, top_half.topleft)
    pygame.draw.rect(surface, CYAN, rect, 2, border_radius=8)


def draw_ball(surface, ball):
    cx    = ball['rect'].centerx
    cy    = ball['rect'].centery
    r     = ball['rect'].width // 2
    color = ball['color']
    draw_glow(surface, color, (cx, cy), r + 14, layers=8)
    pygame.draw.circle(surface, color, (cx, cy), r)
    shine_r = max(2, r // 3)
    pygame.draw.circle(surface, lighten(color, 1.8),
                       (cx - r // 3, cy - r // 3), shine_r)


# ----------------------------
# Particle Effect Class (Enhanced)
# ----------------------------
class Particle:
    def __init__(self, x, y, color, is_spark=False):
        self.x  = x
        self.y  = y
        angle   = random.uniform(0, 2 * math.pi)
        speed   = random.uniform(1.5, 5.5) if not is_spark else random.uniform(3, 8)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.color    = color
        self.lifetime = random.randint(25, 45)
        self.max_life = self.lifetime
        self.size     = random.uniform(2, 6) if not is_spark else random.uniform(1, 3)
        self.is_spark = is_spark
        self.gravity  = 0.15 if not is_spark else 0.05

    def update(self):
        self.x  += self.vx
        self.y  += self.vy
        self.vy += self.gravity
        self.vx *= 0.97
        self.lifetime -= 1
        return self.lifetime > 0

    def draw(self, surface):
        alpha = self.lifetime / self.max_life
        size  = max(1, int(self.size * alpha))
        r, g, b = self.color
        if self.is_spark:
            pygame.draw.line(
                surface, self.color,
                (int(self.x), int(self.y)),
                (int(self.x - self.vx * 2), int(self.y - self.vy * 2)), size
            )
        else:
            fade_color = (
                min(255, int(r * alpha + 255 * (1 - alpha) * 0.3)),
                min(255, int(g * alpha)),
                min(255, int(b * alpha)),
            )
            pygame.draw.circle(surface, fade_color, (int(self.x), int(self.y)), size)


# ----------------------------
# Power-up Class
# ----------------------------
POWERUP_TYPES   = ['expand', 'multiball', 'multiball_4', 'multiball_6', 'score']
POWERUP_WEIGHTS = [0.25, 0.20, 0.20, 0.15, 0.20]

POWERUP_CONFIG = {
    'expand':      {'color': GREEN,      'label': '+PAD', 'glow': (50,  220, 100)},
    'multiball':   {'color': YELLOW,     'label': '+1',   'glow': (255, 230,  50)},
    'multiball_4': {'color': NEON_PINK,  'label': '+4',   'glow': (255,  20, 147)},
    'multiball_6': {'color': NEON_GREEN, 'label': '+6',   'glow': ( 57, 255,  20)},
    'score':       {'color': PURPLE,     'label': '+50',  'glow': (200,  50, 255)},
}


def weighted_powerup_type():
    return random.choices(POWERUP_TYPES, weights=POWERUP_WEIGHTS, k=1)[0]


class PowerUp:
    SIZE = 30

    def __init__(self, x, y):
        self.rect   = pygame.Rect(x - self.SIZE // 2, y, self.SIZE, self.SIZE)
        self.type   = weighted_powerup_type()
        cfg         = POWERUP_CONFIG[self.type]
        self.color  = cfg['color']
        self.label  = cfg['label']
        self.glow_c = cfg['glow']
        self.active = True
        self.float_offset = 0.0
        self.float_dir    = 1
        self.pulse        = 0.0

    def update(self):
        self.float_offset += 0.08 * self.float_dir
        if abs(self.float_offset) > 6:
            self.float_dir *= -1
        self.pulse = (self.pulse + 0.12) % (2 * math.pi)

    def draw(self, surface):
        yo        = int(self.float_offset)
        draw_rect = self.rect.move(0, yo)
        cx, cy    = draw_rect.centerx, draw_rect.centery

        pulse_r = int(22 + 8 * math.sin(self.pulse))
        draw_glow(surface, self.glow_c, (cx, cy), pulse_r, layers=6)

        bg_surf = pygame.Surface((self.SIZE, self.SIZE), pygame.SRCALPHA)
        r, g, b = self.color
        pygame.draw.rect(bg_surf, (r, g, b, 160), (0, 0, self.SIZE, self.SIZE),
                         border_radius=8)
        pygame.draw.rect(bg_surf, (255, 255, 255, 60),
                         (1, 1, self.SIZE - 2, self.SIZE // 2), border_radius=7)
        surface.blit(bg_surf, draw_rect.topleft)
        pygame.draw.rect(surface, self.color, draw_rect, 2, border_radius=8)

        txt = font_tiny.render(self.label, True, WHITE)
        surface.blit(txt, (cx - txt.get_width() // 2, cy - txt.get_height() // 2))


# ----------------------------
# Spawn multiball helper
# ----------------------------
def spawn_balls(origin_ball, count):
    cx      = origin_ball['rect'].centerx
    cy      = origin_ball['rect'].centery
    spd_mag = math.sqrt(origin_ball['speed'][0] ** 2 + origin_ball['speed'][1] ** 2)
    base_angle  = math.atan2(origin_ball['speed'][1], origin_ball['speed'][0])
    spread_deg  = 120
    BALL_COLORS = [YELLOW, ORANGE, NEON_PINK, NEON_GREEN, CYAN, PURPLE, RED, GREEN]
    new_balls   = []

    for i in range(count):
        offset_deg = 0 if count == 1 else -spread_deg / 2 + i * (spread_deg / (count - 1))
        angle = base_angle + math.radians(offset_deg)
        nb = {
            'rect':  pygame.Rect(cx - 6, cy - 6, 12, 12),
            'speed': [math.cos(angle) * spd_mag, math.sin(angle) * spd_mag],
            'color': BALL_COLORS[i % len(BALL_COLORS)],
        }
        new_balls.append(nb)
    return new_balls


# ----------------------------
# Background stars / grid
# ----------------------------
STARS = [(random.randint(0, WIDTH), random.randint(0, HEIGHT),
          random.uniform(0.5, 1.5)) for _ in range(120)]


def draw_background(surface, tick):
    surface.fill(DARK_BLUE)
    for (sx, sy, brightness) in STARS:
        twinkle = 0.6 + 0.4 * math.sin(tick * 0.05 + sx)
        alpha   = min(255, int(180 * brightness * twinkle))
        r       = max(1, int(brightness))
        star_s  = pygame.Surface((r * 2 + 1, r * 2 + 1), pygame.SRCALPHA)
        pygame.draw.circle(star_s, (200, 210, 255, alpha), (r, r), r)
        surface.blit(star_s, (sx - r, sy - r))

    grid_color = (20, 25, 50)
    for gx in range(0, WIDTH, 60):
        pygame.draw.line(surface, grid_color, (gx, 0), (gx, HEIGHT))
    for gy in range(0, HEIGHT, 60):
        pygame.draw.line(surface, grid_color, (0, gy), (WIDTH, gy))


# ----------------------------
# Glassmorphism HUD
# ----------------------------
def draw_hud(surface, level, score_val, ball_count, hand_detected, speed_val):
    panel_w, panel_h = 200, 130
    panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    pygame.draw.rect(panel_surf, (30, 40, 80, 130),  (0, 0, panel_w, panel_h),
                     border_radius=14)
    pygame.draw.rect(panel_surf, (80, 120, 200, 80), (0, 0, panel_w, panel_h // 3),
                     border_radius=14)
    surface.blit(panel_surf, (10, 10))
    pygame.draw.rect(surface, (80, 130, 255, 200), (10, 10, panel_w, panel_h), 2,
                     border_radius=14)

    texts = [
        (f"Level:  {level}",        (255, 200, 80)),
        (f"Score:  {score_val}",     WHITE),
        (f"Balls:  {ball_count}",    CYAN),
        (f"Speed:  {speed_val:.1f}", (180, 255, 180)),
    ]
    for i, (txt, col) in enumerate(texts):
        surf = font_small.render(txt, True, col)
        surface.blit(surf, (22, 20 + i * 26))

    if hand_detected:
        pill_color = (50, 220, 100, 180)
        border_col = GREEN
        ctrl_text  = "Hand Tracking"
    else:
        pill_color = (220, 180, 30, 180)
        border_col = YELLOW
        ctrl_text  = "Keyboard Active"

    pill_w, pill_h = 180, 26
    pill_surf = pygame.Surface((pill_w, pill_h), pygame.SRCALPHA)
    pygame.draw.rect(pill_surf, pill_color, (0, 0, pill_w, pill_h), border_radius=13)
    surface.blit(pill_surf, (10, 148))
    pygame.draw.rect(surface, border_col, (10, 148, pill_w, pill_h), 2, border_radius=13)
    ct = font_tiny.render(ctrl_text, True, WHITE)
    surface.blit(ct, (10 + pill_w // 2 - ct.get_width() // 2, 153))


# ----------------------------
# Game state globals
# ----------------------------
game_state     = "menu"
current_level  = 1
max_level      = 5
score          = 0
high_score     = 0

paddle         = None
balls          = []
targets        = []
powerups       = []
particles      = []
tick_counter   = 0

base_ball_speed       = 5
ball_speed_multiplier = 1.0
HAND_DETECTED_SPEED_MULTIPLIER     = 1.35
HAND_NOT_DETECTED_SPEED_MULTIPLIER = 0.75

# Audio — paths relative to this script so they work regardless of CWD
import os as _os
_SCRIPT_DIR = _os.path.dirname(_os.path.abspath(__file__))

hit_sound = None
for _bg in ("bgmusic.mp3", _os.path.join(_SCRIPT_DIR, "bgmusic.mp3")):
    try:
        pygame.mixer.music.load(_bg)
        pygame.mixer.music.set_volume(0.4)
        pygame.mixer.music.play(-1)
        break
    except Exception:
        pass

for _sfx in ("touchsound.mp3", _os.path.join(_SCRIPT_DIR, "touchsound.mp3")):
    try:
        hit_sound = pygame.mixer.Sound(_sfx)
        hit_sound.set_volume(0.7)
        break
    except Exception:
        hit_sound = None


def create_particles(x, y, color, count=10, sparks=False):
    for _ in range(count):
        particles.append(Particle(x, y, color, is_spark=False))
    if sparks:
        for _ in range(count // 2):
            particles.append(Particle(x, y, lighten(color, 1.8), is_spark=True))


def reset_game():
    global paddle, balls, targets, score, particles, powerups, ball_speed_multiplier

    paddle = pygame.Rect(WIDTH // 2 - 60, HEIGHT - 40, 120, 20)
    balls = []
    main_ball = {
        'rect':  pygame.Rect(WIDTH // 2 - 6, HEIGHT // 2 - 6, 12, 12),
        'speed': [base_ball_speed, -base_ball_speed],
        'color': WHITE,
    }
    balls.append(main_ball)

    targets = []
    # More bricks per level; 16 columns for a denser wall
    num_map     = {1: 48, 2: 64, 3: 80, 4: 96, 5: 112}
    num_targets = num_map.get(current_level, 48)
    target_colors = [RED, ORANGE, YELLOW, GREEN, BLUE, PURPLE]

    cols        = 16
    rows        = max(1, (num_targets + cols - 1) // cols)
    side_margin = 10
    avail_w     = WIDTH - 2 * side_margin
    brick_w     = int(avail_w / cols) - 2   # ~52px wide
    brick_h     = 16                         # thinner bricks
    v_gap       = 5
    start_y     = 55

    created = 0
    for row in range(rows):
        y = start_y + row * (brick_h + v_gap + BRICK_DEPTH)
        for col in range(cols):
            if created >= num_targets:
                break
            x = int(side_margin + col * (brick_w + 2))
            targets.append({
                'rect':   pygame.Rect(x, y, brick_w, brick_h),
                'health': 1,
                'color':  target_colors[created % len(target_colors)],
                'points': 10 * current_level,
            })
            created += 1

    powerups  = []
    particles = []
    score     = 0
    ball_speed_multiplier = 1.0


def configure_level(level):
    global base_ball_speed, paddle, current_level, ball_speed_multiplier

    current_level = level
    speed_map = {1: 8, 2: 11, 3: 14, 4: 18, 5: 22}
    base_ball_speed = speed_map.get(level, 8)
    ball_speed_multiplier = 1.0

    if paddle is None:
        paddle = pygame.Rect(WIDTH // 2 - 60, HEIGHT - 40, 120, 20)
    else:
        paddle.width = max(60, 120 - level * 10)

    reset_game()


configure_level(1)

# Keyboard state
key_left_pressed  = False
key_right_pressed = False
paddle_speed      = 22

# Countdown state (3-2-1-GO before play)
countdown_timer  = 0   # frames remaining in countdown
COUNTDOWN_FRAMES = 180  # 3 seconds at 60 FPS

# ----------------------------
# Main Loop
# ----------------------------
while True:
    tick_counter += 1
    draw_background(screen, tick_counter)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            tracker.__del__()
            pygame.quit()
            sys.exit()

        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()

            if game_state == "menu":
                level1_btn = pygame.Rect(WIDTH // 2 - 120, 195, 240, 48)
                level2_btn = pygame.Rect(WIDTH // 2 - 120, 253, 240, 48)
                level3_btn = pygame.Rect(WIDTH // 2 - 120, 311, 240, 48)
                level4_btn = pygame.Rect(WIDTH // 2 - 120, 369, 240, 48)
                level5_btn = pygame.Rect(WIDTH // 2 - 120, 427, 240, 48)
                if level1_btn.collidepoint(mouse_pos):
                    configure_level(1); game_state = "countdown"; countdown_timer = COUNTDOWN_FRAMES
                elif level2_btn.collidepoint(mouse_pos):
                    configure_level(2); game_state = "countdown"; countdown_timer = COUNTDOWN_FRAMES
                elif level3_btn.collidepoint(mouse_pos):
                    configure_level(3); game_state = "countdown"; countdown_timer = COUNTDOWN_FRAMES
                elif level4_btn.collidepoint(mouse_pos):
                    configure_level(4); game_state = "countdown"; countdown_timer = COUNTDOWN_FRAMES
                elif level5_btn.collidepoint(mouse_pos):
                    configure_level(5); game_state = "countdown"; countdown_timer = COUNTDOWN_FRAMES

            elif game_state == "playing":
                menu_btn = pygame.Rect(WIDTH - 160, 15, 145, 44)
                if menu_btn.collidepoint(mouse_pos):
                    game_state = "menu"

            elif game_state == "gameover":
                replay_btn    = pygame.Rect(WIDTH // 2 - 130, 285, 260, 52)
                next_lvl_btn  = pygame.Rect(WIDTH // 2 - 130, 349, 260, 52)
                menu_over_btn = pygame.Rect(WIDTH // 2 - 130, 413, 260, 52)
                exit_btn      = pygame.Rect(WIDTH // 2 - 130, 477, 260, 52)
                if replay_btn.collidepoint(mouse_pos):
                    configure_level(current_level); game_state = "countdown"; countdown_timer = COUNTDOWN_FRAMES
                elif exit_btn.collidepoint(mouse_pos):
                    tracker.__del__(); pygame.quit(); sys.exit()
                elif menu_over_btn.collidepoint(mouse_pos):
                    game_state = "menu"
                elif next_lvl_btn.collidepoint(mouse_pos) and current_level < max_level:
                    configure_level(current_level + 1); game_state = "countdown"; countdown_timer = COUNTDOWN_FRAMES

            elif game_state == "level_complete":
                next_lvl_btn  = pygame.Rect(WIDTH // 2 - 130, 330, 260, 56)
                menu_over_btn = pygame.Rect(WIDTH // 2 - 130, 400, 260, 56)
                if next_lvl_btn.collidepoint(mouse_pos):
                    configure_level(current_level + 1); game_state = "countdown"; countdown_timer = COUNTDOWN_FRAMES
                elif menu_over_btn.collidepoint(mouse_pos):
                    game_state = "menu"

            elif game_state == "game_complete":
                replay_btn    = pygame.Rect(WIDTH // 2 - 130, 360, 260, 56)
                menu_over_btn = pygame.Rect(WIDTH // 2 - 130, 430, 260, 56)
                if replay_btn.collidepoint(mouse_pos):
                    configure_level(1); game_state = "countdown"; countdown_timer = COUNTDOWN_FRAMES
                elif menu_over_btn.collidepoint(mouse_pos):
                    game_state = "menu"

        if event.type == pygame.KEYDOWN:
            if game_state == "playing" and paddle is not None:
                if event.key == pygame.K_LEFT:
                    key_left_pressed = True
                elif event.key == pygame.K_RIGHT:
                    key_right_pressed = True

        if event.type == pygame.KEYUP:
            if game_state == "playing" and paddle is not None:
                if event.key == pygame.K_LEFT:
                    key_left_pressed = False
                elif event.key == pygame.K_RIGHT:
                    key_right_pressed = False

    # ============================
    # MENU
    # ============================
    if game_state == "menu":
        # Subtle text-level glow only — no giant circle
        _tg = pygame.Surface((320, 70), pygame.SRCALPHA)
        pygame.draw.rect(_tg, (50, 230, 255, 30), (0, 0, 320, 70), border_radius=18)
        screen.blit(_tg, (WIDTH // 2 - 160, 42))
        title_surf = font_big.render("AIR PONG", True, CYAN)
        screen.blit(title_surf, (WIDTH // 2 - title_surf.get_width() // 2, 50))

        sub_surf = font_small.render("*  ULTIMATE EDITION  *", True, YELLOW)
        screen.blit(sub_surf, (WIDTH // 2 - sub_surf.get_width() // 2, 125))

        btn_defs = [
            (pygame.Rect(WIDTH // 2 - 120, 195, 240, 48), (30, 180, 80),  GREEN,  "LEVEL 1 -- EASY"),
            (pygame.Rect(WIDTH // 2 - 120, 253, 240, 48), (180, 150, 20), YELLOW, "LEVEL 2 -- MEDIUM"),
            (pygame.Rect(WIDTH // 2 - 120, 311, 240, 48), (180, 80, 10),  ORANGE, "LEVEL 3 -- HARD"),
            (pygame.Rect(WIDTH // 2 - 120, 369, 240, 48), (180, 20, 20),  RED,    "LEVEL 4 -- EXPERT"),
            (pygame.Rect(WIDTH // 2 - 120, 427, 240, 48), (140, 20, 200), PURPLE, "LEVEL 5 -- NIGHTMARE"),
        ]
        for btn_rect, base_col, border_col, label in btn_defs:
            draw_glass_button(screen, btn_rect, base_col, border_col,
                              font_small.render(label, True, WHITE))

        inst = font_small.render("Move finger  OR  Left/Right Arrow Keys", True, (160, 180, 220))
        screen.blit(inst, (WIDTH // 2 - inst.get_width() // 2, 500))

        hs_surf = font_small.render(f"High Score: {high_score}", True, YELLOW)
        screen.blit(hs_surf, (WIDTH // 2 - hs_surf.get_width() // 2, 545))

        legend_y = 580
        legend_items = [
            (GREEN,      "+PAD"),
            (YELLOW,     "+1 Ball"),
            (NEON_PINK,  "+4 Balls"),
            (NEON_GREEN, "+6 Balls"),
            (PURPLE,     "+50 pts"),
        ]
        lx = WIDTH // 2 - 220
        for col, lbl in legend_items:
            pygame.draw.rect(screen, col, (lx, legend_y, 10, 10), border_radius=3)
            ls = font_tiny.render(lbl, True, (180, 190, 220))
            screen.blit(ls, (lx + 14, legend_y - 1))
            lx += 90

    # ============================
    # COUNTDOWN (3-2-1-GO!)
    # ============================
    elif game_state == "countdown" and paddle is not None:
        countdown_timer -= 1

        # Draw static bricks and paddle as background preview
        for target in targets:
            draw_3d_brick(screen, target['color'], target['rect'])
        draw_paddle(screen, paddle)

        # Dim overlay
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 120))
        screen.blit(dim, (0, 0))

        # Determine which number to show
        frames_per_count = COUNTDOWN_FRAMES // 3   # 60 frames per digit
        if countdown_timer > frames_per_count * 2:
            cd_label  = "3"
            cd_color  = (255, 100, 80)
        elif countdown_timer > frames_per_count:
            cd_label  = "2"
            cd_color  = (255, 210, 60)
        elif countdown_timer > 0:
            cd_label  = "1"
            cd_color  = (80, 220, 100)
        else:
            cd_label  = "GO!"
            cd_color  = CYAN
            game_state = "playing"

        # Pulse scale — grows as each number fades out
        phase = (countdown_timer % frames_per_count) / frames_per_count
        scale = 1.0 + 0.4 * (1.0 - phase)
        alpha = int(255 * phase) if cd_label != "GO!" else 220

        # Render with scaled font
        cd_size = int(130 * scale)
        cd_font = pygame.font.SysFont(None, cd_size)
        cd_surf = cd_font.render(cd_label, True, cd_color)
        cd_surf.set_alpha(alpha)

        # Glow ring behind number
        glow_s = pygame.Surface((200, 200), pygame.SRCALPHA)
        gr = min(255, int(60 * phase))
        pygame.draw.circle(glow_s, (*cd_color, gr), (100, 100), int(80 * scale))
        screen.blit(glow_s, (WIDTH // 2 - 100, HEIGHT // 2 - 100))

        screen.blit(cd_surf, (WIDTH // 2 - cd_surf.get_width() // 2,
                               HEIGHT // 2 - cd_surf.get_height() // 2))

        # "LEVEL X" label
        lbl = font_small.render(f"LEVEL {current_level}", True, (180, 190, 230))
        screen.blit(lbl, (WIDTH // 2 - lbl.get_width() // 2, HEIGHT // 2 + 80))

    # ============================
    # PLAYING
    # ============================
    elif game_state == "playing" and paddle is not None:

        hand_data     = tracker.get_hand_x()
        hand_detected = False

        if hand_data is not None:
            hand_x, cam_width = hand_data
            paddle.x = int(hand_x * WIDTH / cam_width)
            paddle.x = max(0, min(WIDTH - paddle.width, paddle.x))
            hand_detected = True
        else:
            if key_left_pressed:
                paddle.x = max(0, paddle.x - paddle_speed)
            if key_right_pressed:
                paddle.x = min(WIDTH - paddle.width, paddle.x + paddle_speed)

        hand_speed_mult = (HAND_DETECTED_SPEED_MULTIPLIER if hand_detected
                           else HAND_NOT_DETECTED_SPEED_MULTIPLIER)

        for ball in balls:
            cur_spd    = math.sqrt(ball['speed'][0] ** 2 + ball['speed'][1] ** 2)
            target_spd = base_ball_speed * ball_speed_multiplier * hand_speed_mult
            if cur_spd > 0 and abs(cur_spd - target_spd) > 0.1:
                ball['speed'][0] = (ball['speed'][0] / cur_spd) * target_spd
                ball['speed'][1] = (ball['speed'][1] / cur_spd) * target_spd

        for ball in balls[:]:
            ball['rect'].x += ball['speed'][0]
            ball['rect'].y += ball['speed'][1]

            if ball['rect'].left <= 0 or ball['rect'].right >= WIDTH:
                ball['speed'][0] *= -1
                create_particles(ball['rect'].centerx, ball['rect'].centery, CYAN, 5)

            if ball['rect'].top <= 0:
                ball['speed'][1] *= -1
                create_particles(ball['rect'].centerx, ball['rect'].centery, CYAN, 5)

            if ball['rect'].colliderect(paddle):
                if hit_sound:
                    hit_sound.play()
                ball['speed'][1] = -abs(ball['speed'][1])
                rel = (ball['rect'].centerx - paddle.centerx) / (paddle.width / 2)
                spd = math.sqrt(ball['speed'][0] ** 2 + ball['speed'][1] ** 2)
                ball['speed'][0] += rel * 2
                ns  = math.sqrt(ball['speed'][0] ** 2 + ball['speed'][1] ** 2)
                if ns > 0:
                    ball['speed'][0] = (ball['speed'][0] / ns) * spd
                    ball['speed'][1] = (ball['speed'][1] / ns) * spd
                create_particles(ball['rect'].centerx, ball['rect'].centery, WHITE, 8, sparks=True)

            if ball['rect'].bottom >= HEIGHT:
                if len(balls) > 1:
                    balls.remove(ball)
                    create_particles(ball['rect'].centerx, ball['rect'].centery, RED, 15, sparks=True)
                else:
                    game_state = "gameover"
                    if score > high_score:
                        high_score = score

        # Power-ups
        for powerup in powerups[:]:
            powerup.update()
            activated = False

            for ball in balls:
                if ball['rect'].colliderect(powerup.rect):
                    activated = True
                    break
            if not activated and paddle.colliderect(powerup.rect):
                activated = True

            if activated:
                ref = balls[0] if balls else None
                if powerup.type == 'expand':
                    paddle.width = min(200, paddle.width + 40)
                elif powerup.type == 'multiball' and ref and len(balls) < 10:
                    balls.extend(spawn_balls(ref, 1))
                elif powerup.type == 'multiball_4' and ref and len(balls) < 10:
                    balls.extend(spawn_balls(ref, min(4, 10 - len(balls))))
                elif powerup.type == 'multiball_6' and ref and len(balls) < 16:
                    balls.extend(spawn_balls(ref, min(6, 16 - len(balls))))
                elif powerup.type == 'score':
                    score += 50

                powerups.remove(powerup)
                create_particles(powerup.rect.centerx, powerup.rect.centery,
                                 powerup.color, 20, sparks=True)

        # Brick collisions
        for ball in balls:
            for target in targets[:]:
                if ball['rect'].colliderect(target['rect']):
                    if hit_sound:
                        hit_sound.play()
                    target['health'] -= 1
                    create_particles(ball['rect'].centerx, ball['rect'].centery,
                                     target['color'], 8)

                    if target['health'] <= 0:
                        targets.remove(target)
                        score += target['points']
                        if random.random() < 0.30:
                            powerups.append(PowerUp(target['rect'].centerx,
                                                    target['rect'].centery))
                        create_particles(target['rect'].centerx, target['rect'].centery,
                                         target['color'], 22, sparks=True)
                        if len(targets) == 0:
                            if current_level < max_level:
                                game_state = "level_complete"
                            else:
                                game_state = "game_complete"

                    ball['speed'][1] *= -1
                    break

        particles[:] = [p for p in particles if p.update()]

        # Draw
        for target in targets:
            draw_3d_brick(screen, target['color'], target['rect'])

        for ball in balls:
            draw_ball(screen, ball)

        draw_paddle(screen, paddle)

        for powerup in powerups:
            powerup.draw(screen)

        for particle in particles:
            particle.draw(screen)

        current_speed = (base_ball_speed * ball_speed_multiplier *
                         (HAND_DETECTED_SPEED_MULTIPLIER if hand_detected
                          else HAND_NOT_DETECTED_SPEED_MULTIPLIER))
        draw_hud(screen, current_level, score, len(balls), hand_detected, current_speed)

        menu_btn = pygame.Rect(WIDTH - 160, 15, 145, 44)
        draw_glass_button(screen, menu_btn, (60, 60, 100), (120, 140, 255),
                          font_small.render("MENU", True, WHITE), border_radius=12)

    # ============================
    # LEVEL COMPLETE
    # ============================
    elif game_state == "level_complete":
        _tg = pygame.Surface((480, 70), pygame.SRCALPHA)
        pygame.draw.rect(_tg, (50, 220, 100, 35), (0, 0, 480, 70), border_radius=18)
        screen.blit(_tg, (WIDTH // 2 - 240, 172))
        txt = font_big.render(f"LEVEL {current_level} COMPLETE!", True, GREEN)
        screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, 180))

        score_surf = font.render(f"Score: {score}", True, WHITE)
        screen.blit(score_surf, (WIDTH // 2 - score_surf.get_width() // 2, 270))

        next_lvl_btn  = pygame.Rect(WIDTH // 2 - 130, 330, 260, 56)
        menu_over_btn = pygame.Rect(WIDTH // 2 - 130, 400, 260, 56)
        draw_glass_button(screen, next_lvl_btn, (20, 120, 50), GREEN,
                          font.render("NEXT LEVEL", True, WHITE))
        draw_glass_button(screen, menu_over_btn, (60, 60, 80), (120, 130, 180),
                          font.render("MENU", True, WHITE))

    # ============================
    # GAME COMPLETE
    # ============================
    elif game_state == "game_complete":
        _tg = pygame.Surface((500, 70), pygame.SRCALPHA)
        pygame.draw.rect(_tg, (255, 220, 50, 35), (0, 0, 500, 70), border_radius=18)
        screen.blit(_tg, (WIDTH // 2 - 250, 132))
        txt = font_big.render("CONGRATULATIONS!", True, YELLOW)
        screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, 140))

        c2 = font.render("ALL LEVELS COMPLETE!", True, GREEN)
        screen.blit(c2, (WIDTH // 2 - c2.get_width() // 2, 225))

        fs = font.render(f"Final Score: {score}", True, WHITE)
        screen.blit(fs, (WIDTH // 2 - fs.get_width() // 2, 295))

        replay_btn    = pygame.Rect(WIDTH // 2 - 130, 360, 260, 56)
        menu_over_btn = pygame.Rect(WIDTH // 2 - 130, 430, 260, 56)
        draw_glass_button(screen, replay_btn, (20, 120, 50), GREEN,
                          font.render("PLAY AGAIN", True, WHITE))
        draw_glass_button(screen, menu_over_btn, (60, 60, 80), (120, 130, 180),
                          font.render("MENU", True, WHITE))

    # ============================
    # GAME OVER
    # ============================
    elif game_state == "gameover":
        _tg = pygame.Surface((360, 70), pygame.SRCALPHA)
        pygame.draw.rect(_tg, (255, 50, 50, 35), (0, 0, 360, 70), border_radius=18)
        screen.blit(_tg, (WIDTH // 2 - 180, 132))
        txt = font_big.render("GAME OVER", True, RED)
        screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, 140))

        fs = font.render(f"Score: {score}", True, WHITE)
        screen.blit(fs, (WIDTH // 2 - fs.get_width() // 2, 230))

        replay_btn    = pygame.Rect(WIDTH // 2 - 130, 285, 260, 52)
        next_lvl_btn  = pygame.Rect(WIDTH // 2 - 130, 349, 260, 52)
        menu_over_btn = pygame.Rect(WIDTH // 2 - 130, 413, 260, 52)
        exit_btn      = pygame.Rect(WIDTH // 2 - 130, 477, 260, 52)
        draw_glass_button(screen, replay_btn, (20, 120, 50), GREEN,
                          font_small.render("REPLAY LEVEL", True, WHITE))
        draw_glass_button(screen, next_lvl_btn, (150, 130, 10), YELLOW,
                          font_small.render("NEXT LEVEL", True, WHITE))
        draw_glass_button(screen, menu_over_btn, (50, 50, 80), (120, 130, 180),
                          font_small.render("MENU", True, WHITE))
        draw_glass_button(screen, exit_btn, (120, 20, 20), RED,
                          font_small.render("EXIT", True, WHITE))

    pygame.display.flip()
    clock.tick(60)
