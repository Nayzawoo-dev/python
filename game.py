import cv2
import mediapipe as mp
import random
import time
import math
import pygame
import os
import sys
import numpy as np

# ----------------- SOUND -----------------
pygame.mixer.init(frequency=44100, buffer=512)
slice_sound = pygame.mixer.Sound("slice.wav")
bomb_sound = pygame.mixer.Sound("bomb.wav")
button_sound = pygame.mixer.Sound("button.wav") if os.path.exists("button.wav") else None
gameover_sound = pygame.mixer.Sound("gameover.wav") if os.path.exists("gameover.wav") else None
pygame.mixer.music.load("bgm.mp3")

# ----------------- HIGH SCORE -----------------
HIGH_SCORE_FILE = "highscore.txt"
def load_high_score():
    try:
        with open(HIGH_SCORE_FILE, "r") as f:
            return int(f.read())
    except:
        return 0

def save_high_score(score):
    with open(HIGH_SCORE_FILE, "w") as f:
        f.write(str(score))

high_score = load_high_score()

# ----------------- HAND TRACKING -----------------
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7, min_tracking_confidence=0.7)

# ----------------- LOAD FRUITS -----------------
fruits_data = []  # [(img, color)]
for file in os.listdir("."):
    if file.endswith(".png") and file != "bomb.png":
        img = cv2.imread(file, cv2.IMREAD_UNCHANGED)
        if img is not None:
            name = os.path.splitext(file)[0].lower()
            if name == "apple" or name == "fruit":
                color = (0, 0, 255)          # red
            elif name == "banana":
                color = (0, 255, 255)        # yellow
            elif name == "orange":
                color = (0, 165, 255)        # orange
            elif name == "watermelon":
                color = (0, 255, 0)          # green
            else:
                color = (255, 255, 255)      # default white
            fruits_data.append((img, color))

bomb_img = cv2.imread("bomb.png", cv2.IMREAD_UNCHANGED)

# ----------------- BACKGROUND IMAGES (created programmatically) -----------------
def create_gradient_background(width, height, top_color, bottom_color):
    gradient = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(height):
        alpha = y / height
        color = [int(top_color[i] * (1 - alpha) + bottom_color[i] * alpha) for i in range(3)]
        gradient[y, :] = color
    return gradient

menu_bg = create_gradient_background(1280, 720, (50, 150, 255), (200, 100, 50))
playing_bg = create_gradient_background(1280, 720, (20, 20, 50), (100, 50, 150))
gameover_bg = create_gradient_background(1280, 720, (100, 0, 0), (50, 0, 0))

# ----------------- DRAW PNG (with alpha) -----------------
def draw_png(img, png, x, y, size):
    png = cv2.resize(png, (size, size))
    h, w, _ = img.shape
    for i in range(size):
        for j in range(size):
            if 0 <= y + i < h and 0 <= x + j < w and png[i, j, 3] > 0:
                img[y + i, x + j] = png[i, j, :3]

# ----------------- SPLASH EFFECT (improved) -----------------
class Splash:
    def __init__(self, x, y, base_color, is_bomb=False):
        self.particles = []
        if is_bomb:
            # explosion: orange/yellow sparks
            colors = [(0, 165, 255), (0, 255, 255), (0, 0, 0)]
        else:
            # fruit splash: varying shades of base color
            colors = [base_color,
                      (min(255, base_color[0] + 50), min(255, base_color[1] + 50), min(255, base_color[2] + 50)),
                      (max(0, base_color[0] - 50), max(0, base_color[1] - 50), max(0, base_color[2] - 50))]
        for _ in range(30 if is_bomb else 20):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(5, 15 if is_bomb else 10)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            color = random.choice(colors)
            size = random.randint(5, 12 if is_bomb else 8)
            self.particles.append([x, y, vx, vy, size, color])

    def update(self, frame):
        alive = []
        for p in self.particles:
            p[0] += p[2]
            p[1] += p[3]
            p[3] += 0.5  # gravity
            p[4] -= 0.2   # shrink
            if p[4] > 0:
                cv2.circle(frame, (int(p[0]), int(p[1])), int(p[4]), p[5], -1)
                alive.append(p)
        self.particles = alive

    def alive(self):
        return len(self.particles) > 0

# ----------------- BUTTON (with rounded corners, shadow, hover) -----------------
class Button:
    def __init__(self, text, x, y, w=240, h=90, font_scale=1.3):
        self.text = text
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.font_scale = font_scale
        self.hover = 0
        self.clicked = False
        self.shadow_offset = 5

    def draw(self, img, fingers):
        active = False
        for fx, fy in fingers:
            if self.x < fx < self.x + self.w and self.y < fy < self.y + self.h:
                self.hover = min(self.hover + 1, 20)
                active = True
        if not active:
            self.hover = max(self.hover - 1, 0)

        # Button background
        if active:
            color = (0, 255, 0)  # bright green when finger near
        else:
            color = (100, 100, 200)  # default blue
        # Rounded rectangle effect (draw circle at corners)
        radius = 20
        cv2.rectangle(img, (self.x + radius, self.y), (self.x + self.w - radius, self.y + self.h), color, -1)
        cv2.rectangle(img, (self.x, self.y + radius), (self.x + self.w, self.y + self.h - radius), color, -1)
        cv2.circle(img, (self.x + radius, self.y + radius), radius, color, -1)
        cv2.circle(img, (self.x + self.w - radius, self.y + radius), radius, color, -1)
        cv2.circle(img, (self.x + radius, self.y + self.h - radius), radius, color, -1)
        cv2.circle(img, (self.x + self.w - radius, self.y + self.h - radius), radius, color, -1)

        # Text
        cv2.putText(img, self.text,
                    (self.x + 25, self.y + 60),
                    cv2.FONT_HERSHEY_DUPLEX, self.font_scale, (255, 255, 255), 3)

        # Hover progress bar (shows when it will be clicked)
        if self.hover > 0:
            bar_width = int((self.hover / 20) * self.w)
            cv2.rectangle(img, (self.x, self.y + self.h + 5),
                          (self.x + bar_width, self.y + self.h + 10),
                          (0, 255, 0), -1)

        # Click detection (hover sustained for ~0.3 sec)
        if self.hover >= 20:
            self.hover = 0
            if button_sound:
                button_sound.play()
            return True
        return False

# ----------------- FALLING OBJECT -----------------
class Object:
    def __init__(self, w, is_bomb=False):
        self.size = 80
        self.x = random.randint(0, w - self.size)
        self.y = -100
        self.is_bomb = is_bomb
        self.speed = random.randint(5, 9)
        self.alive = True
        if is_bomb:
            self.img = bomb_img
            self.color = (0, 0, 0)
        else:
            self.img, self.color = random.choice(fruits_data)
        # rotation animation
        self.angle = random.uniform(0, 360)
        self.rot_speed = random.uniform(-3, 3)

    def move(self):
        self.y += self.speed
        self.angle += self.rot_speed

    def draw(self, img):
        # Simple rotation (optional - can be slow)
        # For simplicity, we draw without rotation; but you can implement rotate if you want.
        draw_png(img, self.img, self.x, self.y, self.size)

    def hit(self, fx, fy):
        cx = self.x + self.size // 2
        cy = self.y + self.size // 2
        return math.hypot(cx - fx, cy - fy) < self.size // 2

# ----------------- TRAIL EFFECT FOR FINGER (blade) -----------------
class Trail:
    def __init__(self, max_length=10):
        self.points = []
        self.max_length = max_length

    def add_point(self, pt):
        self.points.append(pt)
        if len(self.points) > self.max_length:
            self.points.pop(0)

    def draw(self, img):
        for i, pt in enumerate(self.points):
            alpha = i / len(self.points) if self.points else 1
            radius = int(15 * alpha)
            color = (0, 255, 255)  # yellow
            cv2.circle(img, pt, radius, color, -1)

# ----------------- CAMERA -----------------
cap = cv2.VideoCapture(0)
cap.set(3, 1280)
cap.set(4, 720)

objects = []
splashes = []
score = 0
last_spawn = 0
difficulty = "NORMAL"
combo = 0
last_slice_time = 0
trail = Trail()

easy_btn = Button("EASY", 200, 420, 240, 90)
normal_btn = Button("NORMAL", 520, 420, 240, 90)
hard_btn = Button("HARD", 840, 420, 240, 90)
exit_btn = Button("EXIT", 540, 560, 240, 90)
replay_btn = Button("REPLAY", 540, 420, 240, 90)

MENU, PLAYING, GAME_OVER = 0, 1, 2
game_state = MENU

settings = {
    "EASY": {"spawn": 1.2, "bomb": 0.10},
    "NORMAL": {"spawn": 1.0, "bomb": 0.20},
    "HARD": {"spawn": 0.6, "bomb": 0.35}
}

pygame.mixer.music.play(-1)

# ----------------- MAIN LOOP -----------------
while True:
    ret, img = cap.read()
    if not ret:
        break
    img = cv2.flip(img, 1)
    h, w, _ = img.shape

    # Apply background based on state
    if game_state == MENU:
        bg = menu_bg.copy()
    elif game_state == PLAYING:
        bg = playing_bg.copy()
    else:
        bg = gameover_bg.copy()

    # Resize background to match frame (if needed)
    bg = cv2.resize(bg, (w, h))

    # Blend camera feed with background (semi-transparent)
    # This gives a cool effect: camera feed overlaid on gradient
    alpha = 0.7
    img = cv2.addWeighted(img, alpha, bg, 1 - alpha, 0)

    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb)

    fingers = []
    if result.multi_hand_landmarks:
        for hand in result.multi_hand_landmarks:
            lm = hand.landmark[8]
            fx, fy = int(lm.x * w), int(lm.y * h)
            fingers.append((fx, fy))
            # Add to trail
            trail.add_point((fx, fy))
    # Draw trail (blade)
    trail.draw(img)

    # -------- MENU --------
    if game_state == MENU:
        # Title with shadow
        cv2.putText(img, "FRUIT NINJA", (400, 200), cv2.FONT_HERSHEY_DUPLEX, 3, (0, 0, 0), 8)
        cv2.putText(img, "FRUIT NINJA", (400, 200), cv2.FONT_HERSHEY_DUPLEX, 3, (255, 255, 0), 4)
        cv2.putText(img, f"High Score: {high_score}", (500, 300), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)

        if easy_btn.draw(img, fingers):
            difficulty = "EASY"
            score = 0
            combo = 0
            objects = []
            splashes = []
            game_state = PLAYING
            pygame.mixer.music.play(-1)
        if normal_btn.draw(img, fingers):
            difficulty = "NORMAL"
            score = 0
            combo = 0
            objects = []
            splashes = []
            game_state = PLAYING
            pygame.mixer.music.play(-1)
        if hard_btn.draw(img, fingers):
            difficulty = "HARD"
            score = 0
            combo = 0
            objects = []
            splashes = []
            game_state = PLAYING
            pygame.mixer.music.play(-1)
        if exit_btn.draw(img, fingers):
            break

    # -------- PLAYING --------
    elif game_state == PLAYING:
        # Spawn objects
        if time.time() - last_spawn > settings[difficulty]["spawn"]:
            is_bomb = random.random() < settings[difficulty]["bomb"]
            objects.append(Object(w, is_bomb))
            last_spawn = time.time()

        # Update objects
        for obj in objects:
            obj.move()
            obj.draw(img)

            # Check collision with any finger
            for fx, fy in fingers:
                if obj.alive and obj.hit(fx, fy):
                    now = time.time()
                    if now - last_slice_time < 1.0:
                        combo += 1
                    else:
                        combo = 1
                    last_slice_time = now

                    if obj.is_bomb:
                        bomb_sound.play()
                        splashes.append(Splash(fx, fy, (0, 0, 0), is_bomb=True))
                        pygame.mixer.music.stop()
                        if gameover_sound:
                            gameover_sound.play()
                        game_state = GAME_OVER
                        # Update high score
                        if score > high_score:
                            high_score = score
                            save_high_score(high_score)
                    else:
                        slice_sound.play()
                        points = 1 + combo // 2  # combo bonus
                        score += points
                        obj.alive = False
                        splashes.append(Splash(fx, fy, obj.color))

        # Update splashes
        for splash in splashes:
            splash.update(img)
        splashes = [s for s in splashes if s.alive()]

        # Remove off-screen or dead objects
        objects = [o for o in objects if o.y < h and o.alive]

        # Display score, combo, difficulty
        # Score panel
        overlay = img.copy()
        cv2.rectangle(overlay, (10, 10), (300, 100), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, img, 0.5, 0, img)
        cv2.putText(img, f"{difficulty}", (20, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
        cv2.putText(img, f"Score: {score}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        if combo > 1:
            cv2.putText(img, f"Combo x{combo}!", (150, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

    # -------- GAME OVER --------
    elif game_state == GAME_OVER:
        # Dark overlay
        overlay = img.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, img, 0.3, 0, img)

        cv2.putText(img, "GAME OVER", (400, 250), cv2.FONT_HERSHEY_DUPLEX, 3, (0, 0, 255), 5)
        cv2.putText(img, f"Score: {score}", (520, 350), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
        cv2.putText(img, f"High Score: {high_score}", (480, 399), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 0), 2)

        if replay_btn.draw(img, fingers):
            objects = []
            splashes = []
            score = 0
            combo = 0
            game_state = MENU
        if exit_btn.draw(img, fingers):
            objects = []
            splashes = []
            score = 0
            combo = 0
            game_state = MENU

    cv2.imshow("Fruit Ninja Python", img)
    if cv2.waitKey(1) & 0xFF == 27:  # ESC
        break

cap.release()
cv2.destroyAllWindows()
sys.exit()