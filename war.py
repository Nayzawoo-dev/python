import cv2
import mediapipe as mp
import pygame
import random
import time

# Initialize Pygame
pygame.init()
pygame.mixer.init()

# Fixed window size
WINDOW_WIDTH, WINDOW_HEIGHT = 1280, 720
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("War Plane Shooter - Replay Logic Fix")
clock = pygame.time.Clock()

# Fonts
try:
    font_large = pygame.font.SysFont("comic sans ms", 80)
    font_medium = pygame.font.SysFont("comic sans ms", 60)
    font_small = pygame.font.SysFont("comic sans ms", 50)
except:
    font_large = pygame.font.Font(None, 80)
    font_medium = pygame.font.Font(None, 60)
    font_small = pygame.font.Font(None, 50)

ASSET = "war/"

# ---------------- LOAD ASSETS ----------------
background = pygame.transform.scale(pygame.image.load(ASSET + "background.jpg"), (WINDOW_WIDTH, WINDOW_HEIGHT))
crosshair = pygame.transform.scale(pygame.image.load(ASSET + "crosshair.png").convert_alpha(), (70, 70))
balloon_img = pygame.transform.scale(pygame.image.load(ASSET + "balloon.png").convert_alpha(), (90, 110))

explosion_frames = [
    pygame.transform.scale(pygame.image.load(ASSET + f"explosion_{i}.png").convert_alpha(), (120, 120))
    for i in range(1, 5)
]

gun_sound = pygame.mixer.Sound(ASSET + "gun.wav")
pop_sound = pygame.mixer.Sound(ASSET + "pop.wav")
balloon_spawn_sound = pygame.mixer.Sound(ASSET + "balloon.wav")
balloon_spawn_sound.set_volume(0.2)
game_over_sound = pygame.mixer.Sound(ASSET + "game_over_sound.wav")

pygame.mixer.music.load(ASSET + "bgm.mp3")
pygame.mixer.music.play(-1)

last_click_time = 0
CLICK_DELAY = 0.35

# ---------------- HAND TRACKING ----------------
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1)
cap = cv2.VideoCapture(0)

def get_hand():
    ret, frame = cap.read()
    if not ret: return None, None
    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb)
    if result.multi_hand_landmarks:
        lm = result.multi_hand_landmarks[0]
        x = int(lm.landmark[8].x * WINDOW_WIDTH)
        y = int(lm.landmark[8].y * WINDOW_HEIGHT)
        return x, y
    return None, None

# ---------------- HELPER FUNCTIONS ----------------
def draw_text(text, font, color, x, y, center=True):
    surf = font.render(text, True, color)
    rect = surf.get_rect()
    if center: rect.center = (x, y)
    else: rect.topleft = (x, y)
    screen.blit(surf, rect)
    return rect

def draw_button(text, font, rect_color, text_color, x, y, hover=False):
    width, height = 300, 80
    button_rect = pygame.Rect(0, 0, width, height)
    button_rect.center = (x, y)
    color = (min(rect_color[0] + 40, 255), min(rect_color[1] + 40, 255), min(rect_color[2] + 40, 255)) if hover else rect_color
    pygame.draw.rect(screen, color, button_rect, border_radius=20)
    pygame.draw.rect(screen, (255, 255, 255), button_rect, 4, border_radius=20)
    text_surf = font.render(text, True, text_color)
    text_rect = text_surf.get_rect(center=button_rect.center)
    screen.blit(text_surf, text_rect)
    return button_rect

# ---------------- MENU ----------------
def menu():
    global last_click_time
    if not pygame.mixer.music.get_busy():
        pygame.mixer.music.play(-1)
        
    while True:
        screen.blit(background, (0, 0))
        draw_text("Gunship Battle Air Defense", font_large, (255, 0, 0), WINDOW_WIDTH//2, 150)
        
        options = [("EASY", (100, 255, 100)), ("NORMAL", (255, 255, 100)), ("HARD", (255, 100, 100)), ("EXIT", (200, 200, 200))]
        rects = []
        hx, hy = get_hand()
        
        for i, (opt, color) in enumerate(options):
            test_rect = pygame.Rect(0, 0, 300, 80)
            test_rect.center = (WINDOW_WIDTH//2, 300 + i*100)
            hover = test_rect.collidepoint(hx, hy) if hx else False
            btn_rect = draw_button(opt, font_medium, color, (0, 0, 0), WINDOW_WIDTH//2, 300 + i*100, hover)
            rects.append((opt, btn_rect))
        
        if hx: screen.blit(crosshair, (hx-35, hy-35))
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return "EXIT"
            if event.type == pygame.MOUSEBUTTONDOWN and hx:
                now = time.time()
                if now - last_click_time > CLICK_DELAY:
                    gun_sound.play()
                    last_click_time = now
                    for opt, rect in rects:
                        if rect.collidepoint(hx, hy): return opt
        
        pygame.display.flip()
        clock.tick(60)

# ---------------- GAME ----------------
def play_game(mode):
    settings = {"EASY": {"speed": 3, "spawn": 1.2}, "NORMAL": {"speed": 5, "spawn": 0.8}, "HARD": {"speed": 8, "spawn": 0.4}}[mode]
    balloons, explosions, score = [], [], 0
    last_spawn, start = time.time(), time.time()
    GAME_TIME = 60
    
    while True:
        remain = int(GAME_TIME - (time.time() - start))
        if remain <= 0: return score
        
        hx, hy = get_hand()
        if time.time() - last_spawn > settings["spawn"]:
            balloons.append([random.randint(50, WINDOW_WIDTH-50), WINDOW_HEIGHT + 100])
            balloon_spawn_sound.play()
            last_spawn = time.time()
        
        for b in balloons: b[1] -= settings["speed"]
        screen.blit(background, (0, 0))
        for b in balloons: screen.blit(balloon_img, b)
        
        for exp in explosions[:]:
            f = exp["frame"] // 3
            if f < len(explosion_frames):
                screen.blit(explosion_frames[f], exp["pos"])
                exp["frame"] += 1
            else: explosions.remove(exp)
        
        if hx: screen.blit(crosshair, (hx-35, hy-35))
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return score
            if event.type == pygame.MOUSEBUTTONDOWN and hx:
                gun_sound.play()
                for b in balloons[:]:
                    rect = pygame.Rect(b[0], b[1], 90, 110)
                    if rect.collidepoint(hx, hy):
                        balloons.remove(b)
                        pop_sound.play()
                        explosions.append({"pos": b, "frame": 0})
                        score += 1
        
        pygame.draw.rect(screen, (255, 215, 0), (20, 20, 220, 80), border_radius=15)
        pygame.draw.rect(screen, (255, 255, 255), (20, 20, 220, 80), 3, border_radius=15)
        draw_text(f"Score: {score}", font_small, (0, 0, 0), 130, 60)
        
        pygame.draw.rect(screen, (135, 206, 235), (20, 110, 220, 80), border_radius=15)
        pygame.draw.rect(screen, (255, 255, 255), (20, 110, 220, 80), 3, border_radius=15)
        draw_text(f"Time: {remain}", font_small, (0, 0, 0), 130, 150)
        
        pygame.display.flip()
        clock.tick(60)

# ---------------- GAME OVER ----------------
def game_over(score):
    global last_click_time
    pygame.mixer.music.stop()
    game_over_sound.play()
    
    while True:
        screen.blit(background, (0, 0))
        draw_text(f"YOUR SCORE: {score}", font_large, (255, 0, 0), WINDOW_WIDTH//2, 200)
        
        hx, hy = get_hand()
        replay_rect = pygame.Rect(0, 0, 300, 80); replay_rect.center = (WINDOW_WIDTH//2, 400)
        menu_rect = pygame.Rect(0, 0, 300, 80); menu_rect.center = (WINDOW_WIDTH//2, 520)
        
        replay_hover = replay_rect.collidepoint(hx, hy) if hx else False
        menu_hover = menu_rect.collidepoint(hx, hy) if hx else False
        
        draw_button("REPLAY", font_medium, (100, 255, 100), (0, 0, 0), WINDOW_WIDTH//2, 400, replay_hover)
        draw_button("MENU", font_medium, (255, 255, 100), (0, 0, 0), WINDOW_WIDTH//2, 520, menu_hover)
        
        if hx: screen.blit(crosshair, (hx-35, hy-35))
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return "EXIT"
            if event.type == pygame.MOUSEBUTTONDOWN and hx:
                now = time.time()
                if now - last_click_time > CLICK_DELAY:
                    gun_sound.play()
                    last_click_time = now
                    if replay_hover:
                        pygame.mixer.music.play(-1)
                        return "REPLAY"
                    if menu_hover:
                        return "MENU"
        
        pygame.display.flip()
        clock.tick(60)

# ---------------- MAIN LOOP ----------------
while True:
    # ၁။ အစမှာ Menu ပြပြီး Mode ရွေးခိုင်းမယ်
    current_mode = menu()
    if current_mode == "EXIT":
        break
    
    # ၂။ ရွေးထားတဲ့ Mode အတိုင်း ဂိမ်းစဆော့မယ်
    active_game = True
    while active_game:
        score = play_game(current_mode)
        result = game_over(score)
        
        if result == "REPLAY":
            # REPLAY ဖြစ်ရင် ဒီ inner loop ထဲမှာပဲ current_mode အတိုင်း ဆက်နေမယ်
            continue
        elif result == "MENU":
            # MENU ဖြစ်ရင် inner loop က ထွက်ပြီး Main Loop ထိပ်က menu() ဆီ ပြန်သွားမယ်
            active_game = False
        elif result == "EXIT":
            # EXIT ဖြစ်ရင် loop တွေအကုန်ပိတ်မယ်
            active_game = False
            pygame.quit()
            import sys; sys.exit()

cap.release()
pygame.quit()