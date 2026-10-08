import cv2
import mediapipe as mp
import random
import time
import math
import pygame
import os
import sys
import numpy as np

# ----------------- CONFIG & CONSTANTS -----------------
SCREEN_W = 1280
SCREEN_H = 720
SPRITE_SIZE = 90
PAD = 15
CANVAS_SIZE = SPRITE_SIZE + PAD * 2  # 120x120 for rotation without clipping

# ----------------- SOUND SYSTEM -----------------
pygame.mixer.pre_init(48000, -16, 2, 2048)
pygame.mixer.init()
slice_sound = pygame.mixer.Sound("slice.wav") if os.path.exists("slice.wav") else None
bomb_sound = pygame.mixer.Sound("bomb.wav") if os.path.exists("bomb.wav") else None
button_sound = pygame.mixer.Sound("button.wav") if os.path.exists("button.wav") else None
gameover_sound = pygame.mixer.Sound("normal.mp3") if os.path.exists("normal.mp3") else None

if os.path.exists("bgm.mp3"):
    try:
        pygame.mixer.music.load("bgm.mp3")
    except Exception as e:
        print(f"BGM load warning: {e}")

# ----------------- HIGH SCORE -----------------
HIGH_SCORE_FILE = "highscore.txt"

def load_high_score():
    try:
        with open(HIGH_SCORE_FILE, "r") as f:
            return int(f.read().strip())
    except:
        return 0

def save_high_score(score):
    try:
        with open(HIGH_SCORE_FILE, "w") as f:
            f.write(str(score))
    except:
        pass

high_score = load_high_score()

# ----------------- HAND TRACKING -----------------
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=2,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

# ----------------- BACKGROUND SYSTEM -----------------
def create_fallback_gradient(width, height, top_color=(50, 150, 255), bottom_color=(200, 100, 50)):
    gradient = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(height):
        alpha = y / height
        color = [int(top_color[i] * (1.0 - alpha) + bottom_color[i] * alpha) for i in range(3)]
        gradient[y, :] = color
    return gradient

def load_and_fit_background(img_path, target_w=SCREEN_W, target_h=SCREEN_H):
    """
    Cover target_w x target_h preserving aspect ratio and avoiding ugly stretching.
    Scales image so both dimensions >= target, then center-crops to exact dimensions.
    """
    img = cv2.imread(img_path)
    if img is None:
        return None
    ih, iw = img.shape[:2]
    scale = max(target_w / iw, target_h / ih)
    nw, nh = int(round(iw * scale)), int(round(ih * scale))
    resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)
    x_start = max(0, (nw - target_w) // 2)
    y_start = max(0, (nh - target_h) // 2)
    cropped = resized[y_start:y_start + target_h, x_start:x_start + target_w]
    return cropped

def scan_background_files(asset_dir="."):
    valid_exts = (".jpg", ".jpeg", ".png")
    bg_files = []
    for f in sorted(os.listdir(asset_dir)):
        lower = f.lower()
        if lower.startswith("background") and lower.endswith(valid_exts):
            bg_files.append(f)
    return bg_files

bg_files = scan_background_files(".")
background_cache = {}
thumbnail_cache = {}

for bg_file in bg_files:
    fitted = load_and_fit_background(bg_file, SCREEN_W, SCREEN_H)
    if fitted is not None:
        background_cache[bg_file] = fitted
        thumb = cv2.resize(fitted, (200, 120), interpolation=cv2.INTER_AREA)
        thumbnail_cache[bg_file] = thumb

# Set default background: prioritize background1.jpg if exists
default_bg_name = "background1.jpg" if "background1.jpg" in background_cache else (bg_files[0] if bg_files else None)
if default_bg_name and default_bg_name in background_cache:
    selected_bg_name = default_bg_name
    current_bg_img = background_cache[selected_bg_name]
else:
    fallback_bg = create_fallback_gradient(SCREEN_W, SCREEN_H)
    selected_bg_name = "Default Gradient"
    background_cache[selected_bg_name] = fallback_bg
    thumbnail_cache[selected_bg_name] = cv2.resize(fallback_bg, (200, 120))
    current_bg_img = fallback_bg
    bg_files = [selected_bg_name]

# ----------------- ASSET LOADER (FRUITS & BOMBS) -----------------
def prepare_sprite_padded(img, target_size=SPRITE_SIZE, pad=PAD):
    """
    Resizes image to target_size and places it in the center of a padded RGBA canvas.
    This guarantees that arbitrary rotations never clip sprite corners.
    """
    if img is None:
        return None
    if img.shape[2] == 3:
        # Add alpha channel if missing
        alpha = np.full((img.shape[0], img.shape[1], 1), 255, dtype=np.uint8)
        img = np.concatenate([img, alpha], axis=2)
        
    scaled = cv2.resize(img, (target_size, target_size), interpolation=cv2.INTER_AREA)
    total_size = target_size + pad * 2
    padded = np.zeros((total_size, total_size, 4), dtype=np.uint8)
    padded[pad:pad + target_size, pad:pad + target_size] = scaled
    return padded

fruits_data = []
for file in sorted(os.listdir(".")):
    if file.endswith(".png") and file != "bomb.png":
        raw_img = cv2.imread(file, cv2.IMREAD_UNCHANGED)
        if raw_img is not None:
            name = os.path.splitext(file)[0].lower()
            if "apple" in name or "fruit" in name:
                color = (0, 0, 255)
            elif "banana" in name:
                color = (0, 255, 255)
            elif "orange" in name:
                color = (0, 165, 255)
            elif "watermelon" in name:
                color = (0, 255, 0)
            else:
                color = (255, 255, 255)
            sprite = prepare_sprite_padded(raw_img, SPRITE_SIZE, PAD)
            fruits_data.append((sprite, color, name))

# Bomb asset
raw_bomb = cv2.imread("bomb.png", cv2.IMREAD_UNCHANGED)
bomb_sprite = prepare_sprite_padded(raw_bomb, SPRITE_SIZE, PAD)

# ----------------- VECTORIZED RGBA DRAWING WITH ROTATION -----------------
def draw_rgba(dst, rgba, x, y, angle=0.0):
    """
    Renders an RGBA sprite onto dst (BGR) with fast rotation and alpha blending.
    Handles out-of-bounds clipping safely.
    """
    if rgba is None:
        return
        
    if abs(angle) > 0.05:
        h, w = rgba.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rgba = cv2.warpAffine(rgba, M, (w, h), flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
                              
    h, w = rgba.shape[:2]
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(dst.shape[1], x + w), min(dst.shape[0], y + h)
    
    if x1 >= x2 or y1 >= y2:
        return
        
    sx1, sy1 = x1 - x, y1 - y
    sx2, sy2 = sx1 + (x2 - x1), sy1 + (y2 - y1)
    
    src_crop = rgba[sy1:sy2, sx1:sx2]
    dst_crop = dst[y1:y2, x1:x2]
    
    alpha = (src_crop[:, :, 3] / 255.0)[:, :, np.newaxis]
    dst[y1:y2, x1:x2] = (src_crop[:, :, :3] * alpha + dst_crop * (1.0 - alpha)).astype(np.uint8)

def draw_text_shadow(img, text, x, y, font_scale, color=(255, 255, 255), thickness=2, shadow_color=(0, 0, 0), offset=2):
    cv2.putText(img, text, (x + offset, y + offset), cv2.FONT_HERSHEY_DUPLEX, font_scale, shadow_color, thickness + 1)
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_DUPLEX, font_scale, color, thickness)

# ----------------- PARTICLES / SPLASH -----------------
class Splash:
    def __init__(self, x, y, base_color, is_bomb=False):
        self.particles = []
        colors = [(0, 165, 255), (0, 255, 255), (0, 0, 0)] if is_bomb else \
                 [base_color, (min(255, base_color[0] + 50), min(255, base_color[1] + 50), min(255, base_color[2] + 50))]
        num_particles = 35 if is_bomb else 22
        for _ in range(num_particles):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(5, 16 if is_bomb else 11)
            self.particles.append([
                float(x), float(y),
                math.cos(angle) * speed, math.sin(angle) * speed,
                float(random.randint(5, 13)),
                random.choice(colors)
            ])

    def update(self, frame):
        alive = []
        for p in self.particles:
            p[0] += p[2]
            p[1] += p[3]
            p[3] += 0.5  # Gravity on particles
            p[4] -= 0.25  # Shrink size
            if p[4] > 0:
                cv2.circle(frame, (int(p[0]), int(p[1])), int(p[4]), p[5], -1)
                alive.append(p)
        self.particles = alive

    def alive(self):
        return len(self.particles) > 0

# ----------------- SLICING TRAIL -----------------
class Trail:
    def __init__(self, max_length=12):
        self.points = []

    def add_point(self, pt):
        self.points.append(pt)
        if len(self.points) > 12:
            self.points.pop(0)

    def draw(self, img):
        n = len(self.points)
        if n < 2:
            return
        for i in range(1, n):
            pt1 = self.points[i - 1]
            pt2 = self.points[i]
            ratio = i / n
            thickness = int(10 * ratio) + 2
            # Bright cyan-white blade trail
            blade_color = (int(255 * ratio), int(255 * ratio), int(100 + 155 * ratio))
            cv2.line(img, pt1, pt2, blade_color, thickness)
        for i, pt in enumerate(self.points):
            cv2.circle(img, pt, int(6 * (i / n)) + 1, (0, 255, 255), -1)

# ----------------- DIFFICULTY CONFIGURATION -----------------
DIFFICULTIES = {
    "EASY": {
        "name": "EASY",
        "spawn_cooldown": 1.5,
        "max_wave": 1,
        "bomb_prob": 0.08,
        "gravity": 0.44,
        "vy_range": (-23.0, -20.0),
        "vx_mult": 0.85,
        "desc": "Relaxed pace, minimal bombs"
    },
    "MEDIUM": {
        "name": "MEDIUM",
        "spawn_cooldown": 1.1,
        "max_wave": 2,
        "bomb_prob": 0.20,
        "gravity": 0.49,
        "vy_range": (-25.5, -22.0),
        "vx_mult": 1.0,
        "desc": "Standard speed, moderate bombs"
    },
    "HARD": {
        "name": "HARD",
        "spawn_cooldown": 0.72,
        "max_wave": 3,
        "bomb_prob": 0.38,
        "gravity": 0.55,
        "vy_range": (-27.5, -24.0),
        "vx_mult": 1.25,
        "desc": "Intense action, frequent bombs!"
    }
}

difficulty = "EASY"

# ----------------- PROJECTILE OBJECT (FRUIT / BOMB) -----------------
class Object:
    """
    Classic Fruit Ninja upward arc projectile physics:
    - Launches from near bottom of the screen with upward velocity
    - Random horizontal velocity towards screen interior
    - Gravity continuously accelerates downwards
    - Rotates smoothly while airborne
    """
    def __init__(self, screen_w, screen_h, is_bomb=False, diff_cfg=None, spawn_x=None):
        self.canvas_size = CANVAS_SIZE
        self.hit_radius = 42
        self.is_bomb = is_bomb
        self.alive = True
        self.screen_w = screen_w
        self.screen_h = screen_h

        if is_bomb:
            self.img = bomb_sprite
            self.color = (0, 0, 0)
        else:
            sprite, color, _ = random.choice(fruits_data) if fruits_data else (bomb_sprite, (255, 255, 255), "unknown")
            self.img = sprite
            self.color = color

        if diff_cfg is None:
            diff_cfg = DIFFICULTIES["EASY"]

        # Spawn near bottom area below visible frame
        if spawn_x is not None:
            self.x = float(spawn_x)
        else:
            self.x = float(random.randint(120, screen_w - 120 - self.canvas_size))
        self.y = float(screen_h + random.randint(15, 45))

        self.gravity = diff_cfg["gravity"]

        # Upward launch velocity (negative vy)
        vy_min, vy_max = diff_cfg["vy_range"]
        self.vy = random.uniform(vy_min, vy_max)

        # Horizontal launch velocity (vx) - aimed into playable screen area
        vx_mult = diff_cfg.get("vx_mult", 1.0)
        center_x = screen_w / 2.0
        if self.x < center_x - 120:
            # Spawned on left: arc toward center/right
            self.vx = random.uniform(2.0, 5.5) * vx_mult
        elif self.x > center_x + 120:
            # Spawned on right: arc toward center/left
            self.vx = random.uniform(-5.5, -2.0) * vx_mult
        else:
            # Spawned in center: gentle drift left or right
            self.vx = random.choice([-1, 1]) * random.uniform(1.2, 3.8) * vx_mult

        # Smooth rotation
        self.angle = random.uniform(0.0, 360.0)
        self.rot_speed = random.choice([-1, 1]) * random.uniform(2.5, 6.0)

    def move(self):
        # Velocity and gravity integration
        self.vy += self.gravity
        self.x += self.vx
        self.y += self.vy
        self.angle = (self.angle + self.rot_speed) % 360.0

        # Gentle soft bounce if reaching outer screen border
        if self.x < 15 and self.vx < 0:
            self.vx = -self.vx * 0.7
        elif self.x > self.screen_w - self.canvas_size - 15 and self.vx > 0:
            self.vx = -self.vx * 0.7

    def draw(self, canvas):
        draw_rgba(canvas, self.img, int(self.x), int(self.y), self.angle)

    def hit(self, fx, fy):
        cx = self.x + self.canvas_size / 2.0
        cy = self.y + self.canvas_size / 2.0
        return math.hypot(cx - fx, cy - fy) < self.hit_radius

# ----------------- UI BUTTON -----------------
class Button:
    def __init__(self, text, x, y, w=240, h=80, font_scale=1.1, base_color=(90, 80, 160), hover_color=(0, 200, 100)):
        self.text = text
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.font_scale = font_scale
        self.base_color = base_color
        self.hover_color = hover_color
        self.hover = 0

    def draw(self, img, pointers, is_selected=False, mouse_clicked=False):
        active = any(self.x < px < self.x + self.w and self.y < py < self.y + self.h for px, py in pointers)
        clicked = mouse_clicked and active
        self.hover = min(self.hover + 1, 20) if active else max(self.hover - 1, 0)

        # Background color
        if is_selected:
            bg_col = (50, 150, 60)
        elif active:
            bg_col = self.hover_color
        else:
            bg_col = self.base_color

        cv2.rectangle(img, (self.x, self.y), (self.x + self.w, self.y + self.h), bg_col, -1)

        # Border
        if is_selected:
            cv2.rectangle(img, (self.x, self.y), (self.x + self.w, self.y + self.h), (0, 220, 255), 3)
        else:
            cv2.rectangle(img, (self.x, self.y), (self.x + self.w, self.y + self.h), (220, 220, 220), 2)

        # Hover progress bar
        if active and not is_selected:
            prog = self.hover / 20.0
            cv2.rectangle(img, (self.x, self.y + self.h - 6), (self.x + int(self.w * prog), self.y + self.h), (0, 255, 0), -1)

        # Text with centering
        disp_text = ("> " + self.text) if is_selected else self.text
        (tw, th), _ = cv2.getTextSize(disp_text, cv2.FONT_HERSHEY_DUPLEX, self.font_scale, 2)
        tx = self.x + max(10, (self.w - tw) // 2)
        ty = self.y + (self.h + th) // 2
        cv2.putText(img, disp_text, (tx, ty), cv2.FONT_HERSHEY_DUPLEX, self.font_scale, (255, 255, 255), 2)

        if (self.hover >= 20 or clicked):
            self.hover = 0
            if button_sound:
                button_sound.play()
            return True
        return False

# ----------------- BACKGROUND SELECTION CARD -----------------
class BackgroundCard:
    def __init__(self, bg_file, thumb_img, x, y, w=200, h=120, label=""):
        self.bg_file = bg_file
        self.thumb = thumb_img
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.label = label
        self.hover = 0

    def draw(self, canvas, pointers, is_selected=False, mouse_clicked=False):
        active = any(self.x < px < self.x + self.w and self.y < py < self.y + self.h for px, py in pointers)
        clicked = mouse_clicked and active
        self.hover = min(self.hover + 1, 20) if active else max(self.hover - 1, 0)

        # Draw thumbnail image
        canvas[self.y:self.y + self.h, self.x:self.x + self.w] = self.thumb

        # Border and Selection status
        if is_selected:
            cv2.rectangle(canvas, (self.x, self.y), (self.x + self.w, self.y + self.h), (0, 220, 255), 4)
            # SELECTED badge
            badge_h = 24
            cv2.rectangle(canvas, (self.x, self.y + self.h - badge_h), (self.x + self.w, self.y + self.h), (0, 180, 0), -1)
            cv2.putText(canvas, "SELECTED", (self.x + 42, self.y + self.h - 7), cv2.FONT_HERSHEY_DUPLEX, 0.55, (255, 255, 255), 1)
        elif active:
            cv2.rectangle(canvas, (self.x, self.y), (self.x + self.w, self.y + self.h), (0, 255, 120), 3)
            # Hover progress bar
            prog = self.hover / 20.0
            cv2.rectangle(canvas, (self.x, self.y + self.h - 6), (self.x + int(self.w * prog), self.y + self.h), (0, 255, 120), -1)
        else:
            cv2.rectangle(canvas, (self.x, self.y), (self.x + self.w, self.y + self.h), (140, 140, 140), 2)

        # Label under thumbnail
        (tw, _), _ = cv2.getTextSize(self.label, cv2.FONT_HERSHEY_DUPLEX, 0.6, 1)
        lx = self.x + max(5, (self.w - tw) // 2)
        draw_text_shadow(canvas, self.label, lx, self.y + self.h + 24, 0.6, (255, 255, 255), 1)

        if (self.hover >= 20 or clicked) and not is_selected:
            self.hover = 0
            if button_sound:
                button_sound.play()
            return True
        return False

# ----------------- GAME STATE DEFINITIONS -----------------
STATE_MENU = 0
STATE_PLAYING = 1
STATE_GAME_OVER = 2
STATE_SELECT_DIFFICULTY = 3
STATE_SELECT_BG = 4

game_state = STATE_MENU

# ----------------- UI CONTROLS INITIALIZATION -----------------
# Main Menu buttons
menu_play_btn = Button("PLAY", 500, 290, 280, 75, font_scale=1.2)
menu_diff_btn = Button("DIFFICULTY", 450, 390, 380, 75, font_scale=1.1)
menu_bg_btn = Button("BACKGROUND", 450, 490, 380, 75, font_scale=1.1)
menu_quit_btn = Button("QUIT", 500, 590, 280, 75, font_scale=1.2)

# Difficulty buttons
diff_easy_btn = Button("EASY", 200, 290, 250, 90, font_scale=1.3)
diff_medium_btn = Button("MEDIUM", 515, 290, 250, 90, font_scale=1.3)
diff_hard_btn = Button("HARD", 830, 290, 250, 90, font_scale=1.3)
diff_back_btn = Button("BACK", 370, 550, 240, 75, font_scale=1.1)
diff_start_btn = Button("PLAY", 670, 550, 240, 75, font_scale=1.1)

# Background selection screen buttons
bg_back_btn = Button("BACK", 370, 560, 240, 75, font_scale=1.1)
bg_start_btn = Button("PLAY", 670, 560, 240, 75, font_scale=1.1)

# Game Over buttons
go_replay_btn = Button("REPLAY", 370, 490, 240, 75, font_scale=1.2)
go_menu_btn = Button("MAIN MENU", 670, 490, 240, 75, font_scale=1.2)

# Build Background Cards
bg_cards = []
card_w, card_h = 200, 120
num_bgs = len(bg_files)
if num_bgs > 0:
    gap = 25
    total_cards_w = num_bgs * card_w + (num_bgs - 1) * gap
    start_card_x = max(20, (SCREEN_W - total_cards_w) // 2)
    start_card_y = 270
    for idx, b_name in enumerate(bg_files):
        cx = start_card_x + idx * (card_w + gap)
        clean_label = os.path.splitext(b_name)[0].capitalize()
        card = BackgroundCard(b_name, thumbnail_cache[b_name], cx, start_card_y, card_w, card_h, clean_label)
        bg_cards.append(card)

# ----------------- MOUSE INTERACTION SUPPORT -----------------
mouse_pos = (0, 0)
mouse_clicked = False

def on_mouse_event(event, x, y, flags, param):
    global mouse_pos, mouse_clicked
    mouse_pos = (x, y)
    if event == cv2.EVENT_LBUTTONDOWN:
        mouse_clicked = True

def main():
    global current_bg_img, selected_bg_name, difficulty, game_state, score, combo, high_score
    global last_slice_time, last_spawn, objects, splashes, trail, mouse_pos, mouse_clicked

    cv2.namedWindow("Fruit Ninja Python")
    cv2.setMouseCallback("Fruit Ninja Python", on_mouse_event)

    # ----------------- CAMERA INITIALIZATION -----------------
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, SCREEN_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, SCREEN_H)

    objects = []
    splashes = []
    score = 0
    combo = 0
    last_slice_time = 0
    last_spawn = 0
    trail = Trail()

    # Start background music
    if os.path.exists("bgm.mp3"):
        try:
            pygame.mixer.music.play(-1)
        except:
            pass

    def start_new_game():
        global score, combo, objects, splashes, last_spawn, last_slice_time, game_state
        score = 0
        combo = 0
        objects = []
        splashes = []
        last_slice_time = 0
        last_spawn = time.time()
        game_state = STATE_PLAYING
        if os.path.exists("bgm.mp3"):
            try:
                pygame.mixer.music.play(-1)
            except:
                pass

    # ----------------- MAIN GAME LOOP -----------------
    while True:
        ret, cam_raw = cap.read()
        if not ret:
            # Fallback empty camera frame if webcam is momentarily unavailable
            cam_raw = np.zeros((SCREEN_H, SCREEN_W, 3), dtype=np.uint8)

        # 1. CAMERA INPUT PIPELINE (Used exclusively for hand tracking)
        cam_frame = cv2.flip(cam_raw, 1)
        ch, cw, _ = cam_frame.shape

        # Hand detection processed on camera feed
        rgb_frame = cv2.cvtColor(cam_frame, cv2.COLOR_BGR2RGB)
        result = hands.process(rgb_frame)

        fingers = []
        if result.multi_hand_landmarks:
            for hand in result.multi_hand_landmarks:
                fx = int(hand.landmark[8].x * SCREEN_W)
                fy = int(hand.landmark[8].y * SCREEN_H)
                fingers.append((fx, fy))
                trail.add_point((fx, fy))

        # Combine hand tracking with mouse fallback for flexible input
        pointers = list(fingers)
        if mouse_pos != (0, 0):
            pointers.append(mouse_pos)

        # 2. VISUAL RENDERING PIPELINE (Rendered on selected static background)
        if game_state == STATE_PLAYING:
            display = current_bg_img.copy()

            cfg = DIFFICULTIES[difficulty]

            # Wave Spawning Logic
            if time.time() - last_spawn > cfg["spawn_cooldown"]:
                wave_count = random.randint(1, cfg["max_wave"])
                possible_x = list(range(120, SCREEN_W - 120 - CANVAS_SIZE, 140))
                random.shuffle(possible_x)

                for i in range(wave_count):
                    spawn_x = possible_x[i] if i < len(possible_x) else random.randint(120, SCREEN_W - 120 - CANVAS_SIZE)
                    is_bomb = (random.random() < cfg["bomb_prob"])
                    # If multiple in wave, ensure not all are bombs
                    if is_bomb and wave_count > 1 and all(o.is_bomb for o in objects[-wave_count + 1:] if len(objects) >= wave_count):
                        is_bomb = False
                    objects.append(Object(SCREEN_W, SCREEN_H, is_bomb=is_bomb, diff_cfg=cfg, spawn_x=spawn_x))

                last_spawn = time.time()

            # Update and Draw Objects
            for obj in objects:
                obj.move()
                obj.draw(display)

                # Slicing Collision Check against tracked fingertips / pointers
                for px, py in pointers:
                    if obj.alive and obj.hit(px, py):
                        if obj.is_bomb:
                            # Bomb hit -> Game Over
                            if bomb_sound:
                                bomb_sound.play()
                            pygame.mixer.music.stop()
                            if gameover_sound:
                                gameover_sound.play()
                            game_state = STATE_GAME_OVER
                            splashes.append(Splash(px, py, (0, 0, 0), is_bomb=True))
                            if score > high_score:
                                high_score = score
                                save_high_score(high_score)
                            break
                        else:
                            # Fruit hit -> Slice and Splash
                            if slice_sound:
                                slice_sound.play()
                            combo = combo + 1 if time.time() - last_slice_time < 0.9 else 1
                            last_slice_time = time.time()
                            score += (1 + combo // 2)
                            obj.alive = False
                            splashes.append(Splash(px, py, obj.color, is_bomb=False))

            # Splashes update
            for s in splashes:
                s.update(display)
            splashes = [s for s in splashes if s.alive()]

            # Filter out sliced objects or objects that finished their upward arc and fell below screen
            objects = [o for o in objects if o.alive and not (o.y > SCREEN_H + 50 and o.vy > 0)]

            # Slicing Trail & Fingertip Cursor
            trail.draw(display)
            for fx, fy in fingers:
                cv2.circle(display, (fx, fy), 7, (0, 255, 255), -1)
                cv2.circle(display, (fx, fy), 13, (255, 255, 255), 2)

            # HUD Overlay
            draw_text_shadow(display, f"Score: {score}", 30, 60, 1.2, (255, 255, 255), 2)
            draw_text_shadow(display, f"Best: {high_score}", 30, 100, 0.8, (200, 200, 200), 2)
            draw_text_shadow(display, f"Diff: {difficulty}", SCREEN_W - 220, 60, 0.9, (0, 230, 255), 2)

            # Combo Announcement
            if combo > 1 and time.time() - last_slice_time < 0.8:
                combo_text = f"COMBO x{combo}!"
                draw_text_shadow(display, combo_text, SCREEN_W // 2 - 130, 120, 1.4, (0, 215, 255), 3)

        elif game_state == STATE_MENU:
            # Sleek dark dimmed backdrop on selected background
            display = current_bg_img.copy()
            dim = np.zeros_like(display)
            cv2.addWeighted(display, 0.40, dim, 0.60, 0, display)

            # Title
            draw_text_shadow(display, "FRUIT NINJA", 410, 160, 2.8, (0, 220, 255), 4)
            draw_text_shadow(display, "HAND DETECTION EDITION", 475, 215, 0.9, (255, 255, 255), 2)
            
            # Info bar
            clean_bg_name = os.path.splitext(selected_bg_name)[0].capitalize()
            info_str = f"Difficulty: {difficulty}  |  Background: {clean_bg_name}  |  High Score: {high_score}"
            draw_text_shadow(display, info_str, 340, 255, 0.7, (200, 230, 255), 1)

            # Buttons
            if menu_play_btn.draw(display, pointers, mouse_clicked=mouse_clicked):
                start_new_game()
            elif menu_diff_btn.draw(display, pointers, mouse_clicked=mouse_clicked):
                game_state = STATE_SELECT_DIFFICULTY
            elif menu_bg_btn.draw(display, pointers, mouse_clicked=mouse_clicked):
                game_state = STATE_SELECT_BG
            elif menu_quit_btn.draw(display, pointers, mouse_clicked=mouse_clicked):
                break

            # Slicing Trail & Cursor
            trail.draw(display)
            for fx, fy in fingers:
                cv2.circle(display, (fx, fy), 8, (0, 255, 255), -1)

        elif game_state == STATE_SELECT_DIFFICULTY:
            display = current_bg_img.copy()
            dim = np.zeros_like(display)
            cv2.addWeighted(display, 0.38, dim, 0.62, 0, display)

            draw_text_shadow(display, "SELECT DIFFICULTY", 380, 140, 2.0, (0, 220, 255), 3)
            draw_text_shadow(display, "Choose your challenge level", 480, 190, 0.85, (220, 220, 220), 2)

            # Difficulty Cards
            if diff_easy_btn.draw(display, pointers, is_selected=(difficulty == "EASY"), mouse_clicked=mouse_clicked):
                difficulty = "EASY"
            draw_text_shadow(display, DIFFICULTIES["EASY"]["desc"], 210, 420, 0.6, (200, 255, 200), 1)

            if diff_medium_btn.draw(display, pointers, is_selected=(difficulty == "MEDIUM"), mouse_clicked=mouse_clicked):
                difficulty = "MEDIUM"
            draw_text_shadow(display, DIFFICULTIES["MEDIUM"]["desc"], 505, 420, 0.6, (255, 255, 200), 1)

            if diff_hard_btn.draw(display, pointers, is_selected=(difficulty == "HARD"), mouse_clicked=mouse_clicked):
                difficulty = "HARD"
            draw_text_shadow(display, DIFFICULTIES["HARD"]["desc"], 810, 420, 0.6, (255, 200, 200), 1)

            # Navigation buttons
            if diff_back_btn.draw(display, pointers, mouse_clicked=mouse_clicked):
                game_state = STATE_MENU
            elif diff_start_btn.draw(display, pointers, mouse_clicked=mouse_clicked):
                start_new_game()

            trail.draw(display)
            for fx, fy in fingers:
                cv2.circle(display, (fx, fy), 8, (0, 255, 255), -1)

        elif game_state == STATE_SELECT_BG:
            display = current_bg_img.copy()
            dim = np.zeros_like(display)
            cv2.addWeighted(display, 0.38, dim, 0.62, 0, display)

            draw_text_shadow(display, "SELECT BACKGROUND", 370, 130, 2.0, (0, 220, 255), 3)
            draw_text_shadow(display, "Hover hand over a card or click to choose background", 360, 180, 0.8, (220, 220, 220), 2)

            # Background cards
            for card in bg_cards:
                is_active_bg = (card.bg_file == selected_bg_name)
                if card.draw(display, pointers, is_selected=is_active_bg, mouse_clicked=mouse_clicked):
                    selected_bg_name = card.bg_file
                    current_bg_img = background_cache[selected_bg_name]

            # Navigation buttons
            if bg_back_btn.draw(display, pointers, mouse_clicked=mouse_clicked):
                game_state = STATE_MENU
            elif bg_start_btn.draw(display, pointers, mouse_clicked=mouse_clicked):
                start_new_game()

            trail.draw(display)
            for fx, fy in fingers:
                cv2.circle(display, (fx, fy), 8, (0, 255, 255), -1)

        elif game_state == STATE_GAME_OVER:
            display = current_bg_img.copy()
            red_dim = np.full_like(display, (15, 15, 75))
            cv2.addWeighted(display, 0.35, red_dim, 0.65, 0, display)

            draw_text_shadow(display, "GAME OVER", 430, 220, 2.8, (0, 0, 255), 4)
            draw_text_shadow(display, f"Final Score: {score}", 490, 310, 1.4, (255, 255, 255), 2)
            draw_text_shadow(display, f"High Score: {high_score}", 510, 370, 1.1, (200, 200, 200), 2)

            if score == high_score and score > 0:
                draw_text_shadow(display, "★ NEW HIGH SCORE! ★", 470, 425, 1.0, (0, 215, 255), 2)

            if go_replay_btn.draw(display, pointers, mouse_clicked=mouse_clicked):
                start_new_game()
            elif go_menu_btn.draw(display, pointers, mouse_clicked=mouse_clicked):
                game_state = STATE_MENU

            trail.draw(display)
            for fx, fy in fingers:
                cv2.circle(display, (fx, fy), 8, (0, 255, 255), -1)

        # Reset frame-level mouse click flag
        mouse_clicked = False

        cv2.imshow("Fruit Ninja Python", display)
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC to exit
            break

    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    pygame.mixer.quit()
    sys.exit()

if __name__ == "__main__":
    main()