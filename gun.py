import cv2
import mediapipe as mp
import pygame
import random
import time

# Initialize Pygame
pygame.init()
pygame.mixer.init()

# Fixed window size (fits most screens, windowed mode)
WINDOW_WIDTH, WINDOW_HEIGHT = 1280, 720
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Balloon Shooter")
clock = pygame.time.Clock()

# Try to use a child-friendly font (fallback to default if unavailable)
try:
    font_large = pygame.font.SysFont("comic sans ms", 80)
    font_medium = pygame.font.SysFont("comic sans ms", 60)
    font_small = pygame.font.SysFont("comic sans ms", 50)
except:
    font_large = pygame.font.Font(None, 80)
    font_medium = pygame.font.Font(None, 60)
    font_small = pygame.font.Font(None, 50)

ASSET = "gunfolder/"

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
pygame.mixer.music.load(ASSET + "bgm.mp3")
pygame.mixer.music.play(-1)

# Cooldown for finger gun clicks
last_click_time = 0
CLICK_DELAY = 0.35

# ---------------- HAND TRACKING ----------------
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1)
cap = cv2.VideoCapture(0)

def get_hand():
    """Returns (x, y) of index fingertip in window coordinates, or (None, None)."""
    ret, frame = cap.read()
    if not ret:
        return None, None

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
    """Helper to draw text, optionally centered at (x,y)."""
    surf = font.render(text, True, color)
    rect = surf.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    screen.blit(surf, rect)
    return rect

def draw_button(text, font, rect_color, text_color, x, y, hover=False):
    """Draws a rounded button with text. Returns its rect."""
    width, height = 300, 80
    button_rect = pygame.Rect(0, 0, width, height)
    button_rect.center = (x, y)
    
    # Choose color based on hover
    if hover:
        color = (min(rect_color[0] + 40, 255), min(rect_color[1] + 40, 255), min(rect_color[2] + 40, 255))
    else:
        color = rect_color
    
    pygame.draw.rect(screen, color, button_rect, border_radius=20)
    pygame.draw.rect(screen, (255, 255, 255), button_rect, 4, border_radius=20)  # white border
    
    text_surf = font.render(text, True, text_color)
    text_rect = text_surf.get_rect(center=button_rect.center)
    screen.blit(text_surf, text_rect)
    return button_rect

# ---------------- MENU ----------------
def menu():
    global last_click_time
    while True:
        screen.blit(background, (0, 0))
        
        # Title
        draw_text("🎈 Balloon Shooter 🎈", font_large, (255, 255, 100), WINDOW_WIDTH//2, 150)
        
        # Menu options with colorful buttons
        options = [("EASY", (100, 255, 100)), ("NORMAL", (255, 255, 100)), ("HARD", (255, 100, 100)), ("EXIT", (200, 200, 200))]
        rects = []
        y_start = 300
        for i, (opt, color) in enumerate(options):
            hover = False
            hx, hy = get_hand()
            if hx is not None:
                # Check if hand is over this button (will be used for visual feedback)
                test_rect = pygame.Rect(0, 0, 300, 80)
                test_rect.center = (WINDOW_WIDTH//2, y_start + i*100)
                if test_rect.collidepoint(hx, hy):
                    hover = True
            btn_rect = draw_button(opt, font_medium, color, (0, 0, 0), WINDOW_WIDTH//2, y_start + i*100, hover)
            rects.append((opt, btn_rect))
        
        # Draw crosshair if hand detected
        hx, hy = get_hand()
        if hx:
            screen.blit(crosshair, (hx-35, hy-35))
        
        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "EXIT"
            if event.type == pygame.MOUSEBUTTONDOWN and hx:
                now = time.time()
                if now - last_click_time > CLICK_DELAY:
                    gun_sound.play()
                    last_click_time = now
                    for opt, rect in rects:
                        if rect.collidepoint(hx, hy):
                            return opt
        
        pygame.display.flip()
        clock.tick(60)

# ---------------- GAME ----------------
def play_game(mode):
    settings = {
        "EASY": {"speed": 3, "spawn": 1.2},
        "NORMAL": {"speed": 5, "spawn": 0.8},
        "HARD": {"speed": 8, "spawn": 0.4}
    }[mode]
    
    balloons = []
    explosions = []
    score = 0
    last_spawn = time.time()
    start = time.time()
    GAME_TIME = 60
    
    while True:
        # Timer
        remain = int(GAME_TIME - (time.time() - start))
        if remain <= 0:
            return score
        
        # Hand tracking
        hx, hy = get_hand()
        
        # Spawn balloons
        if time.time() - last_spawn > settings["spawn"]:
            balloons.append([random.randint(50, WINDOW_WIDTH-50), WINDOW_HEIGHT + 100])
            last_spawn = time.time()
        
        # Move balloons upward
        for b in balloons:
            b[1] -= settings["speed"]
        
        # Draw background
        screen.blit(background, (0, 0))
        
        # Draw balloons
        for b in balloons:
            screen.blit(balloon_img, b)
        
        # Draw explosions
        for exp in explosions[:]:
            f = exp["frame"] // 3
            if f < len(explosion_frames):
                screen.blit(explosion_frames[f], exp["pos"])
                exp["frame"] += 1
            else:
                explosions.remove(exp)
        
        # Draw crosshair
        if hx:
            screen.blit(crosshair, (hx-35, hy-35))
        
        # Event handling for shooting
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return score  # or handle quit
            if event.type == pygame.MOUSEBUTTONDOWN and hx:
                gun_sound.play()
                for b in balloons[:]:
                    rect = pygame.Rect(b[0], b[1], 90, 110)
                    if rect.collidepoint(hx, hy):
                        balloons.remove(b)
                        pop_sound.play()
                        explosions.append({"pos": b, "frame": 0})
                        score += 1
        
        # Draw UI (score and time) with colorful panels
        # Score panel
        pygame.draw.rect(screen, (255, 215, 0), (20, 20, 220, 80), border_radius=15)
        pygame.draw.rect(screen, (255, 255, 255), (20, 20, 220, 80), 3, border_radius=15)
        draw_text(f"Score: {score}", font_small, (0, 0, 0), 130, 60)
        
        # Time panel
        pygame.draw.rect(screen, (135, 206, 235), (20, 110, 220, 80), border_radius=15)
        pygame.draw.rect(screen, (255, 255, 255), (20, 110, 220, 80), 3, border_radius=15)
        draw_text(f"Time: {remain}", font_small, (0, 0, 0), 130, 150)
        
        pygame.display.flip()
        clock.tick(60)

# ---------------- GAME OVER ----------------
def game_over(score):
    global last_click_time
    while True:
        screen.blit(background, (0, 0))
        
        # Show score
        draw_text(f"YOUR SCORE: {score}", font_large, (255, 255, 100), WINDOW_WIDTH//2, 200)
        
        # Buttons
        hx, hy = get_hand()
        
        # Replay button
        replay_hover = False
        menu_hover = False
        if hx:
            replay_rect = pygame.Rect(0, 0, 300, 80)
            replay_rect.center = (WINDOW_WIDTH//2, 400)
            if replay_rect.collidepoint(hx, hy):
                replay_hover = True
            menu_rect = pygame.Rect(0, 0, 300, 80)
            menu_rect.center = (WINDOW_WIDTH//2, 520)
            if menu_rect.collidepoint(hx, hy):
                menu_hover = True
        
        draw_button("REPLAY", font_medium, (100, 255, 100), (0, 0, 0), WINDOW_WIDTH//2, 400, replay_hover)
        draw_button("MENU", font_medium, (255, 255, 100), (0, 0, 0), WINDOW_WIDTH//2, 520, menu_hover)
        
        # Crosshair
        if hx:
            screen.blit(crosshair, (hx-35, hy-35))
        
        # Events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "EXIT"
            if event.type == pygame.MOUSEBUTTONDOWN and hx:
                now = time.time()
                if now - last_click_time > CLICK_DELAY:
                    gun_sound.play()
                    last_click_time = now
                    if replay_hover:
                        return "REPLAY"
                    if menu_hover:
                        return "MENU"
        
        pygame.display.flip()
        clock.tick(60)

# ---------------- MAIN LOOP ----------------
while True:
    choice = menu()
    if choice == "EXIT":
        break
    score = play_game(choice)
    result = game_over(score)
    if result == "MENU":
        continue
    elif result == "EXIT":
        break

cap.release()
pygame.quit()