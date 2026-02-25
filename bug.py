import pygame
import cv2
import mediapipe as mp
import random
import time
import sys
import os
import math

# --- Path Fix ---
try:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
except:
    pass

# --- Pygame Setup ---
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Bug Smasher - Music Logic Updated")
clock = pygame.time.Clock()

# --- Assets Loading ---
BUG_SIZE = 100 

try:
    if os.path.exists("bugback.jpg"):
        bg_raw = pygame.image.load("bugback.jpg")
        bg_image = pygame.transform.scale(bg_raw, (WIDTH, HEIGHT))
    else:
        bg_image = None

    if os.path.exists("bug/bug.png"):
        bug_raw = pygame.image.load("bug/bug.png")
        bug_img_base = pygame.transform.scale(bug_raw, (BUG_SIZE, BUG_SIZE))
    else:
        bug_img_base = None

    # နောက်ခံသီချင်း Loading (Home မှာတင် ချက်ချင်းဖွင့်ရန်)
    if os.path.exists("background_music.mp3"):
        pygame.mixer.music.load("background_music.mp3")
        pygame.mixer.music.set_volume(0.3)
        pygame.mixer.music.play(-1) # ဂိမ်းထဲဝင်ကတည်းက စဖွင့်ခြင်း

    # အသံဖိုင်များ Loading
    smash_sound = pygame.mixer.Sound("slice.wav") if os.path.exists("slice.wav") else None
    
    rank_sounds = {
        "normal": pygame.mixer.Sound("normal.mp3") if os.path.exists("normal.mp3") else None,
        "good": pygame.mixer.Sound("good.mp3") if os.path.exists("good.mp3") else None,
        "excellent": pygame.mixer.Sound("excellent.mp3") if os.path.exists("excellent.mp3") else None
    }

except Exception as e:
    print(f"Asset Error: {e}")
    bg_image, bug_img_base = None, None

# --- Mediapipe Hand Tracking ---
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)
cap = cv2.VideoCapture(0)

# --- Bug Class ---
class Bug:
    def __init__(self, can_be_smashed=True):
        self.can_be_smashed = can_be_smashed
        self.reset()

    def reset(self):
        self.x = random.randint(100, WIDTH - 100)
        self.y = random.randint(100, HEIGHT - 100)
        self.vel_x = random.choice([-7, -5, 5, 7])
        self.vel_y = random.choice([-7, -5, 5, 7])

    def update(self):
        self.x += self.vel_x
        self.y += self.vel_y
        if self.x <= 50 or self.x >= WIDTH - 50: self.vel_x *= -1
        if self.y <= 50 or self.y >= HEIGHT - 50: self.vel_y *= -1

    def draw(self, surface):
        if bug_img_base:
            angle = math.degrees(math.atan2(-self.vel_y, self.vel_x)) - 90
            rotated_bug = pygame.transform.rotate(bug_img_base, angle)
            new_rect = rotated_bug.get_rect(center=(self.x, self.y))
            surface.blit(rotated_bug, new_rect.topleft)
        else:
            pygame.draw.circle(surface, (139, 69, 19), (int(self.x), int(self.y)), 40)

# --- Variables ---
home_bugs = [Bug(can_be_smashed=False) for _ in range(8)]
play_bugs = [Bug(can_be_smashed=True) for _ in range(7)]

game_state = "HOME"
score = 0
game_duration = 60
hover_start_time = 0
is_hovering = False
HOVER_LIMIT = 1.5 
sound_played = False 

font_lg = pygame.font.SysFont("Arial", 70, bold=True)
font_md = pygame.font.SysFont("Arial", 35)

def draw_text(text, font, color, x, y, center=False):
    img = font.render(text, True, color)
    if center:
        rect = img.get_rect(center=(x, y))
        screen.blit(img, rect)
    else:
        screen.blit(img, (x, y))

# --- Main Game Loop ---
running = True
while running:
    success, image = cap.read()
    if not success: break
    image = cv2.flip(image, 1)
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_image)

    hand_x, hand_y = -100, -100
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            lm = hand_landmarks.landmark[8]
            hand_x, hand_y = int(lm.x * WIDTH), int(lm.y * HEIGHT)

    if bg_image: screen.blit(bg_image, (0, 0))
    else: screen.fill((240, 240, 240))

    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False

    # --- 1. HOME STATE ---
    if game_state == "HOME":
        for b in home_bugs:
            b.update()
            b.draw(screen)
        draw_text("BUG SMASHER", font_lg, (255, 255, 255), WIDTH//2, 100, center=True)
        
        play_rect, exit_rect = pygame.Rect(325, 250, 150, 70), pygame.Rect(325, 350, 150, 70)
        
        if play_rect.collidepoint(hand_x, hand_y):
            if not is_hovering: is_hovering, hover_start_time = True, time.time()
            dur = time.time() - hover_start_time
            pygame.draw.rect(screen, (0, 255, 0), (325, 320, int(dur * 100), 8))
            if dur >= HOVER_LIMIT:
                game_state, score, is_hovering, sound_played = "PLAY", 0, False, False
                start_ticks = pygame.time.get_ticks()
            btn_play_col = (0, 220, 0)
        elif exit_rect.collidepoint(hand_x, hand_y):
            if not is_hovering: is_hovering, hover_start_time = True, time.time()
            dur = time.time() - hover_start_time
            pygame.draw.rect(screen, (255, 0, 0), (325, 420, int(dur * 100), 8))
            if dur >= HOVER_LIMIT: running = False
            btn_exit_col = (220, 0, 0)
        else:
            is_hovering = False
            btn_play_col, btn_exit_col = (0, 150, 0), (150, 0, 0)

        pygame.draw.rect(screen, btn_play_col, play_rect, border_radius=15)
        draw_text("PLAY", font_md, (255, 255, 255), 365, 265)
        pygame.draw.rect(screen, btn_exit_col, exit_rect, border_radius=15)
        draw_text("EXIT", font_md, (255, 255, 255), 365, 365)

    # --- 2. PLAY STATE ---
    elif game_state == "PLAY":
        rem_time = max(0, game_duration - (pygame.time.get_ticks() - start_ticks) // 1000)
        for b in play_bugs:
            b.update()
            b.draw(screen)
            if ((hand_x - b.x)**2 + (hand_y - b.y)**2)**0.5 < 60:
                score += 1
                if smash_sound: smash_sound.play()
                b.reset()
        draw_text(f"Smashed: {score}", font_md, (0, 0, 0), 600, 20)
        draw_text(f"Time: {rem_time}s", font_md, (255, 0, 0), 20, 20)
        if rem_time <= 0: 
            game_state = "RESULT"
            pygame.mixer.music.stop() # အချိန်ကုန်ရင် သီချင်းရပ်မယ်

    # --- 3. RESULT STATE ---
    elif game_state == "RESULT":
        draw_text("GAME OVER", font_lg, (0, 0, 0), WIDTH//2, 80, center=True)
        
        if score >= 90:
            rank_key, rank_text, rank_color = "excellent", "EXCELLENT!", (0, 200, 0)
        elif 80 <= score < 90:
            rank_key, rank_text, rank_color = "good", "GOOD", (0, 0, 200)
        else:
            rank_key, rank_text, rank_color = "normal", "NORMAL", (100, 100, 100)

        if not sound_played:
            if rank_sounds[rank_key]: rank_sounds[rank_key].play()
            sound_played = True

        draw_text(f"Smashed: {score}", font_md, (0, 0, 0), WIDTH//2, 170, center=True)
        draw_text(f"Your skill is: {rank_text}", font_md, rank_color, WIDTH//2, 220, center=True)
        
        res_retry_rect = pygame.Rect(325, 350, 150, 60)
        res_exit_rect = pygame.Rect(325, 430, 150, 60)

        if res_retry_rect.collidepoint(hand_x, hand_y):
            if not is_hovering: is_hovering, hover_start_time = True, time.time()
            dur = time.time() - hover_start_time
            pygame.draw.rect(screen, (0, 255, 0), (325, 410, int(dur * 100), 8))
            if dur >= HOVER_LIMIT:
                game_state, score, is_hovering, sound_played = "PLAY", 0, False, False
                pygame.mixer.music.play(-1) # Retry နှိပ်ရင် သီချင်းပြန်စဖွင့်မယ်
                start_ticks = pygame.time.get_ticks()
            btn_retry_col, btn_exit_col = (0, 180, 0), (150, 0, 0)
        elif res_exit_rect.collidepoint(hand_x, hand_y):
            if not is_hovering: is_hovering, hover_start_time = True, time.time()
            dur = time.time() - hover_start_time
            pygame.draw.rect(screen, (255, 0, 0), (325, 490, int(dur * 100), 8))
            if dur >= HOVER_LIMIT: running = False
            btn_retry_col, btn_exit_col = (0, 150, 0), (220, 0, 0)
        else:
            is_hovering = False
            btn_retry_col, btn_exit_col = (0, 150, 0), (150, 0, 0)
            
        pygame.draw.rect(screen, btn_retry_col, res_retry_rect, border_radius=10)
        draw_text("RETRY", font_md, (255, 255, 255), 355, 360)
        pygame.draw.rect(screen, btn_exit_col, res_exit_rect, border_radius=10)
        draw_text("EXIT", font_md, (255, 255, 255), 365, 440)

    pygame.draw.circle(screen, (0, 255, 0), (hand_x, hand_y), 10)
    pygame.display.flip()
    clock.tick(30)

cap.release()
pygame.quit()
sys.exit()