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
# Bomb ထိရင် မြည်မယ့်အသံ
gameover_sound = pygame.mixer.Sound("normal.mp3") if os.path.exists("normal.mp3") else None
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
fruits_data = []
for file in os.listdir("."):
    if file.endswith(".png") and file != "bomb.png":
        img = cv2.imread(file, cv2.IMREAD_UNCHANGED)
        if img is not None:
            name = os.path.splitext(file)[0].lower()
            if name == "apple" or name == "fruit": color = (0, 0, 255)
            elif name == "banana": color = (0, 255, 255)
            elif name == "orange": color = (0, 165, 255)
            elif name == "watermelon": color = (0, 255, 0)
            else: color = (255, 255, 255)
            fruits_data.append((img, color))

bomb_img = cv2.imread("bomb.png", cv2.IMREAD_UNCHANGED)

# ----------------- BACKGROUNDS -----------------
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

def draw_png(img, png, x, y, size):
    png = cv2.resize(png, (size, size))
    h, w, _ = img.shape
    for i in range(size):
        for j in range(size):
            if 0 <= y + i < h and 0 <= x + j < w and png[i, j, 3] > 0:
                img[y + i, x + j] = png[i, j, :3]

class Splash:
    def __init__(self, x, y, base_color, is_bomb=False):
        self.particles = []
        colors = [(0, 165, 255), (0, 255, 255), (0, 0, 0)] if is_bomb else \
                 [base_color, (min(255, base_color[0]+50), min(255, base_color[1]+50), min(255, base_color[2]+50))]
        for _ in range(30 if is_bomb else 20):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(5, 15 if is_bomb else 10)
            self.particles.append([x, y, math.cos(angle)*speed, math.sin(angle)*speed, random.randint(5, 12), random.choice(colors)])

    def update(self, frame):
        alive = []
        for p in self.particles:
            p[0], p[1] = p[0]+p[2], p[1]+p[3]
            p[3] += 0.5; p[4] -= 0.2
            if p[4] > 0:
                cv2.circle(frame, (int(p[0]), int(p[1])), int(p[4]), p[5], -1)
                alive.append(p)
        self.particles = alive
    def alive(self): return len(self.particles) > 0

class Button:
    def __init__(self, text, x, y, w=240, h=90, font_scale=1.3):
        self.text, self.x, self.y, self.w, self.h, self.font_scale = text, x, y, w, h, font_scale
        self.hover = 0
    def draw(self, img, fingers):
        active = any(self.x < fx < self.x + self.w and self.y < fy < self.y + self.h for fx, fy in fingers)
        self.hover = min(self.hover + 1, 20) if active else max(self.hover - 1, 0)
        color = (0, 255, 0) if active else (100, 100, 200)
        cv2.rectangle(img, (self.x, self.y), (self.x+self.w, self.y+self.h), color, -1)
        cv2.putText(img, self.text, (self.x+25, self.y+60), cv2.FONT_HERSHEY_DUPLEX, self.font_scale, (255,255,255), 3)
        if self.hover >= 20:
            self.hover = 0
            if button_sound: button_sound.play()
            return True
        return False

class Object:
    def __init__(self, w, is_bomb=False):
        self.size, self.is_bomb, self.alive = 80, is_bomb, True
        self.x, self.y = random.randint(0, w - self.size), -100
        self.speed = random.randint(5, 9)
        if is_bomb: self.img, self.color = bomb_img, (0,0,0)
        else: self.img, self.color = random.choice(fruits_data)
    def move(self): self.y += self.speed
    def draw(self, img): draw_png(img, self.img, self.x, self.y, self.size)
    def hit(self, fx, fy): return math.hypot(self.x+40-fx, self.y+40-fy) < 40

class Trail:
    def __init__(self, max_length=10): self.points = []
    def add_point(self, pt):
        self.points.append(pt)
        if len(self.points) > 10: self.points.pop(0)
    def draw(self, img):
        for i, pt in enumerate(self.points):
            cv2.circle(img, pt, int(15 * (i/len(self.points))), (0, 255, 255), -1)

# ----------------- GAME START -----------------
cap = cv2.VideoCapture(0)
cap.set(3, 1280); cap.set(4, 720)
objects, splashes, score, last_spawn = [], [], 0, 0
difficulty = "NORMAL"
combo, last_slice_time = 0, 0
trail = Trail()
MENU, PLAYING, GAME_OVER = 0, 1, 2
game_state = MENU

easy_btn = Button("EASY", 200, 420); normal_btn = Button("NORMAL", 520, 420); 
hard_btn = Button("HARD", 840, 420); exit_btn = Button("EXIT", 540, 560); replay_btn = Button("REPLAY", 540, 420)

settings = {"EASY": {"spawn": 1.2, "bomb": 0.10}, "NORMAL": {"spawn": 1.0, "bomb": 0.20}, "HARD": {"spawn": 0.6, "bomb": 0.35}}
pygame.mixer.music.play(-1)

while True:
    ret, img = cap.read()
    if not ret: break
    img = cv2.flip(img, 1)
    h, w, _ = img.shape
    bg = menu_bg.copy() if game_state == MENU else (playing_bg.copy() if game_state == PLAYING else gameover_bg.copy())
    img = cv2.addWeighted(img, 0.7, cv2.resize(bg, (w, h)), 0.3, 0)
    
    result = hands.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    fingers = []
    if result.multi_hand_landmarks:
        for hand in result.multi_hand_landmarks:
            fx, fy = int(hand.landmark[8].x * w), int(hand.landmark[8].y * h)
            fingers.append((fx, fy)); trail.add_point((fx, fy))
    trail.draw(img)

    if game_state == MENU:
        cv2.putText(img, "FRUIT NINJA", (400, 200), cv2.FONT_HERSHEY_DUPLEX, 3, (255, 255, 0), 4)
        if easy_btn.draw(img, fingers) or normal_btn.draw(img, fingers) or hard_btn.draw(img, fingers):
            score, combo, objects, splashes = 0, 0, [], []
            game_state = PLAYING
            pygame.mixer.music.play(-1)
        if exit_btn.draw(img, fingers): break

    elif game_state == PLAYING:
        if time.time() - last_spawn > settings[difficulty]["spawn"]:
            objects.append(Object(w, random.random() < settings[difficulty]["bomb"]))
            last_spawn = time.time()

        for obj in objects:
            obj.move(); obj.draw(img)
            for fx, fy in fingers:
                if obj.alive and obj.hit(fx, fy):
                    if obj.is_bomb:
                        # --- BOMB ထိတဲ့ အပိုင်း ---
                        bomb_sound.play()
                        pygame.mixer.music.stop() # သီချင်းရပ်မယ်
                        if gameover_sound: gameover_sound.play() # Game Over အသံမြည်မယ်
                        game_state = GAME_OVER
                        if score > high_score: high_score = score; save_high_score(high_score)
                    else:
                        slice_sound.play()
                        combo = combo + 1 if time.time() - last_slice_time < 1.0 else 1
                        last_slice_time = time.time()
                        score += (1 + combo // 2); obj.alive = False
                        splashes.append(Splash(fx, fy, obj.color))

        for s in splashes: s.update(img)
        splashes = [s for s in splashes if s.alive()]
        objects = [o for o in objects if o.y < h and o.alive]
        cv2.putText(img, f"Score: {score}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    elif game_state == GAME_OVER:
        cv2.putText(img, "GAME OVER", (400, 250), cv2.FONT_HERSHEY_DUPLEX, 3, (0, 0, 255), 5)
        cv2.putText(img, f"Score: {score}", (520, 350), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
        if replay_btn.draw(img, fingers) or exit_btn.draw(img, fingers):
            game_state = MENU # Menu ပြန်သွားရင် သီချင်းပြန်စမယ်

    cv2.imshow("Fruit Ninja Python", img)
    if cv2.waitKey(1) & 0xFF == 27: break

cap.release(); cv2.destroyAllWindows(); sys.exit()