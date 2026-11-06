import cv2
import mediapipe as mp
import pygame
import random
import time
import math
import sys
import os

try:
    from PIL import Image, ImageSequence
except ImportError:
    print("Error: 'Pillow' library မရှိသေးပါ။ Terminal တွင် 'pip install pillow' ဟု run ပေးပါ။")
    sys.exit()

import ui_theme

# Initialize Pygame & Audio
pygame.init()
pygame.mixer.pre_init(48000, -16, 2, 2048)
pygame.mixer.init()

# Fixed window size & title
WINDOW_WIDTH, WINDOW_HEIGHT = 1280, 720
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Balloon Shooter - Childhood Classic")
clock = pygame.time.Clock()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
def asset_path(filename):
    return os.path.join(BASE_DIR, filename)

# ---------------- GIF HELPER FUNCTION ----------------
def load_gif_frames(filepath, size):
    """ GIF ဖိုင်ကို ဖတ်ပြီး Pygame Frames များအဖြစ် ပြောင်းပေးသော Function """
    pil_img = Image.open(filepath)
    frames = []
    for frame in ImageSequence.Iterator(pil_img):
        frame_rgba = frame.convert("RGBA")
        pygame_surface = pygame.image.fromstring(
            frame_rgba.tobytes(), frame_rgba.size, "RGBA"
        )
        scaled_surface = pygame.transform.scale(pygame_surface, size)
        frames.append(scaled_surface)
    return frames

# ---------------- LOAD ASSETS ----------------
BACKGROUND_PNG_PATHS = [
    asset_path("background1.jpg"),
    asset_path("background2.jpg"),
    asset_path("background3.jpg"),
    asset_path("background4.jpg"),
    asset_path("background5.jpg")
]

MAP_NAMES = [
    "Sunny Meadows",
    "Magic Twilight",
    "Sky Carnival",
    "Sunset Hills",
    "Crystal Lake"
]

PLANE_GIF_PATHS = [
    asset_path("helicopter1.gif"),
    asset_path("helicopter2.gif"),
    asset_path("helicopter3.gif"),
    asset_path("helicopter4.gif"),
    asset_path("helicopter5.gif")
]

BALLOON_NAMES = [
    "Aqua Heart",
    "Ruby Heart",
    "Purple Dream",
    "Golden Sun",
    "Emerald Heart"
]

crosshair = pygame.transform.scale(
    pygame.image.load(asset_path("crosshair.png")).convert_alpha(), 
    (70, 70)
)

explosion_frames = [
    pygame.transform.scale(
        pygame.image.load(asset_path(f"explosion_{i}.png")).convert_alpha(), 
        (120, 120)
    )
    for i in range(1, 5)
]

gun_sound = pygame.mixer.Sound(asset_path("gun.wav"))
pop_sound = pygame.mixer.Sound(asset_path("pop.wav"))

pygame.mixer.music.load(asset_path("bgm.mp3"))
pygame.mixer.music.play(-1)

last_click_time = 0
CLICK_DELAY = 0.35

# Default selected background PNG
selected_background = pygame.transform.scale(
    pygame.image.load(BACKGROUND_PNG_PATHS[0]), 
    (WINDOW_WIDTH, WINDOW_HEIGHT)
)

# ---------------- HAND TRACKING & POINTER ----------------
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

def get_pointer():
    """ Returns crosshair coordinates, prioritizing webcam hand landmarks with mouse fallback """
    hx, hy = get_hand()
    if hx is not None and hy is not None:
        return hx, hy, True
    mx, my = pygame.mouse.get_pos()
    return mx, my, False

# ---------------- NOSTALGIC SKY & DECORATION INSTANCE ----------------
sky_fx = ui_theme.SkyDecorations(WINDOW_WIDTH, WINDOW_HEIGHT)

# ---------------- HOW TO PLAY DIALOG ----------------
def show_how_to_play():
    global last_click_time
    btn_close = ui_theme.TactileButton("GOT IT!", WINDOW_WIDTH // 2, 570, width=220, height=60, color_scheme=ui_theme.BTN_GREEN)
    
    while True:
        sky_fx.update()
        sky_fx.draw_sky(screen)
        
        # Center instruction panel
        panel_rect = pygame.Rect(WINDOW_WIDTH // 2 - 380, 100, 760, 520)
        ui_theme.draw_arcade_panel(screen, panel_rect, title="HOW TO PLAY")
        
        instructions = [
            ("AIM CROSSHAIR", "Move your hand in front of the camera (or move your mouse) to aim.", (52, 152, 219)),
            ("FIRE DART", "Left Click or squeeze to fire a dart and pop balloons.", (235, 75, 75)),
            ("BEAT THE CLOCK", "You have 60 seconds to pop as many balloons as you can!", (240, 160, 20)),
            ("DIFFICULTY", "Normal and Hard make balloons float faster and spawn quicker!", (46, 204, 113))
        ]
        
        font_header = ui_theme.get_arcade_font(24, bold=True)
        font_desc = ui_theme.get_arcade_font(19, bold=False)
        
        y_cursor = 175
        for title, desc, color in instructions:
            bullet_rect = pygame.Rect(panel_rect.x + 40, y_cursor + 2, 16, 16)
            pygame.draw.circle(screen, color, bullet_rect.center, 8)
            pygame.draw.circle(screen, (70, 30, 10), bullet_rect.center, 8, 2)
            
            ui_theme.draw_text_with_outline(
                screen, title, font_header, color, (255, 255, 255),
                panel_rect.x + 65, y_cursor + 8, outline_width=2, shadow_offset=(0, 1), center=False
            )
            y_cursor += 30
            ui_theme.draw_text_with_outline(
                screen, desc, font_desc, (70, 40, 20), (255, 255, 255),
                panel_rect.x + 65, y_cursor + 4, outline_width=1, shadow_offset=(0, 1), center=False
            )
            y_cursor += 48
            
        px, py, _ = get_pointer()
        btn_close.update((px, py))
        btn_close.draw(screen)
        
        screen.blit(crosshair, (px - 35, py - 35))
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.KEYDOWN and (event.key == pygame.K_ESCAPE or event.key == pygame.K_RETURN):
                return
            if event.type == pygame.MOUSEBUTTONDOWN:
                now = time.time()
                if now - last_click_time > CLICK_DELAY:
                    gun_sound.play()
                    last_click_time = now
                    if btn_close.rect.collidepoint(px, py):
                        return
                        
        pygame.display.flip()
        clock.tick(60)

# ---------------- MAIN MENU ----------------
def menu():
    global last_click_time
    if not pygame.mixer.music.get_busy():
        pygame.mixer.music.play(-1)
        
    btn_easy = ui_theme.TactileButton("EASY", WINDOW_WIDTH // 2, 305, width=300, height=66, color_scheme=ui_theme.BTN_GREEN)
    btn_normal = ui_theme.TactileButton("NORMAL", WINDOW_WIDTH // 2, 385, width=300, height=66, color_scheme=ui_theme.BTN_YELLOW)
    btn_hard = ui_theme.TactileButton("HARD", WINDOW_WIDTH // 2, 465, width=300, height=66, color_scheme=ui_theme.BTN_RED)
    btn_how = ui_theme.TactileButton("HOW TO PLAY", WINDOW_WIDTH // 2, 545, width=300, height=62, color_scheme=ui_theme.BTN_BLUE, font_size=28)
    btn_exit = ui_theme.TactileButton("EXIT", WINDOW_WIDTH // 2, 625, width=220, height=52, color_scheme=ui_theme.BTN_PURPLE, font_size=26)
    
    buttons = [
        ("EASY", btn_easy),
        ("NORMAL", btn_normal),
        ("HARD", btn_hard),
        ("HOW", btn_how),
        ("EXIT", btn_exit)
    ]
    
    title_font = ui_theme.get_arcade_font(74, bold=True)
    high_score = ui_theme.load_high_score()
    
    start_time = time.time()
    
    while True:
        sky_fx.update()
        sky_fx.draw_sky(screen)
        
        elapsed = time.time() - start_time
        wobble1 = math.sin(elapsed * 2.2) * 0.4
        wobble2 = math.cos(elapsed * 2.0) * 0.4
        
        # Retro 3D Arcade Title
        ui_theme.draw_3d_title(screen, "BALLOON", title_font, WINDOW_WIDTH // 2, 85, extrude_depth=8)
        ui_theme.draw_3d_title(screen, "SHOOTER", title_font, WINDOW_WIDTH // 2, 168, extrude_depth=8)
        
        # Nostalgic cartoon balloons floating beside title
        ui_theme.draw_cartoon_balloon(screen, 260, 140, radius=36, color=(240, 70, 70), wobble=wobble1)
        ui_theme.draw_cartoon_balloon(screen, 1020, 140, radius=36, color=(52, 152, 219), wobble=wobble2)
        
        # High Score Ribbon at top right
        if high_score > 0:
            hs_box = pygame.Rect(WINDOW_WIDTH - 240, 20, 215, 46)
            pygame.draw.rect(screen, (0, 0, 0, 50), hs_box.move(0, 3), border_radius=14)
            pygame.draw.rect(screen, ui_theme.COLOR_PANEL_BG, hs_box, border_radius=14)
            pygame.draw.rect(screen, (255, 215, 0), hs_box, 3, border_radius=14)
            ui_theme.draw_text_with_outline(
                screen, f"BEST: {high_score:06d}", ui_theme.get_arcade_font(20, bold=True),
                (120, 60, 20), (255, 255, 255), hs_box.centerx, hs_box.centery, outline_width=1, center=True
            )
            
        px, py, _ = get_pointer()
        
        for name, btn in buttons:
            btn.update((px, py))
            btn.draw(screen)
            
        screen.blit(crosshair, (px - 35, py - 35))
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "EXIT"
            if event.type == pygame.MOUSEBUTTONDOWN:
                now = time.time()
                if now - last_click_time > CLICK_DELAY:
                    gun_sound.play()
                    last_click_time = now
                    for name, btn in buttons:
                        if btn.rect.collidepoint(px, py):
                            if name == "HOW":
                                show_how_to_play()
                                break
                            else:
                                return name
                                
        pygame.display.flip()
        clock.tick(60)

# ---------------- VISUAL BACKGROUND SELECTION MENU ----------------
def select_background():
    global last_click_time, selected_background
    
    bg_thumbnails = []
    card_width, card_height = 210, 290
    thumb_w, thumb_h = 180, 140
    
    for path in BACKGROUND_PNG_PATHS:
        img = pygame.image.load(path)
        thumb = pygame.transform.scale(img, (thumb_w, thumb_h))
        bg_thumbnails.append(thumb)
        
    title_font = ui_theme.get_arcade_font(52, bold=True)
    card_lbl_font = ui_theme.get_arcade_font(22, bold=True)
    card_sub_font = ui_theme.get_arcade_font(17, bold=True)
    
    while True:
        sky_fx.update()
        sky_fx.draw_sky(screen)
        
        ui_theme.draw_3d_title(screen, "SELECT YOUR MAP", title_font, WINDOW_WIDTH // 2, 75, extrude_depth=6)
        
        px, py, _ = get_pointer()
        cards = []
        
        start_x = 140
        spacing = 250
        card_y = 390
        
        for i, thumb in enumerate(bg_thumbnails):
            cx = start_x + i * spacing
            card_rect = pygame.Rect(0, 0, card_width, card_height)
            card_rect.center = (cx, card_y)
            
            hover = card_rect.collidepoint(px, py)
            
            # Subtle hover lift
            visual_rect = card_rect.move(0, -6) if hover else card_rect
            
            # Draw Nostalgic Arcade Card Panel
            border_c = (235, 130, 20) if hover else ui_theme.COLOR_PANEL_BORDER
            bg_c = (255, 255, 248) if hover else ui_theme.COLOR_PANEL_BG
            ui_theme.draw_arcade_panel(screen, visual_rect, border_color=border_c, bg_color=bg_c)
            
            # Thumbnail Frame
            thumb_x = visual_rect.centerx - thumb_w // 2
            thumb_y = visual_rect.y + 20
            screen.blit(thumb, (thumb_x, thumb_y))
            pygame.draw.rect(screen, (70, 30, 10), (thumb_x, thumb_y, thumb_w, thumb_h), 2, border_radius=6)
            
            # Map Labels
            ui_theme.draw_text_with_outline(
                screen, f"MAP {i+1}", card_lbl_font, 
                (235, 75, 75) if hover else (70, 30, 10), 
                (255, 255, 255), visual_rect.centerx, visual_rect.y + 190, outline_width=2
            )
            ui_theme.draw_text_with_outline(
                screen, MAP_NAMES[i], card_sub_font, 
                (120, 70, 20), (255, 255, 255), visual_rect.centerx, visual_rect.y + 225, outline_width=1
            )
            
            # Tactile "CLICK TO SELECT" Pill on hover
            if hover:
                pill_rect = pygame.Rect(visual_rect.centerx - 65, visual_rect.y + 252, 130, 26)
                pygame.draw.rect(screen, (46, 204, 113), pill_rect, border_radius=10)
                pygame.draw.rect(screen, (25, 95, 55), pill_rect, 2, border_radius=10)
                ui_theme.draw_text_with_outline(
                    screen, "SELECT", ui_theme.get_arcade_font(15, bold=True),
                    (255, 255, 255), (25, 95, 55), pill_rect.centerx, pill_rect.centery, outline_width=1
                )
                
            cards.append((BACKGROUND_PNG_PATHS[i], card_rect))
            
        screen.blit(crosshair, (px - 35, py - 35))
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.MOUSEBUTTONDOWN:
                now = time.time()
                if now - last_click_time > CLICK_DELAY:
                    gun_sound.play()
                    last_click_time = now
                    for path, rect in cards:
                        if rect.collidepoint(px, py):
                            selected_background = pygame.transform.scale(
                                pygame.image.load(path), 
                                (WINDOW_WIDTH, WINDOW_HEIGHT)
                            )
                            return True
                            
        pygame.display.flip()
        clock.tick(60)

# ---------------- VISUAL BALLOON SELECTION MENU ----------------
def select_plane():
    global last_click_time
    
    preview_planes = []
    card_width, card_height = 210, 290
    
    for path in PLANE_GIF_PATHS:
        frames = load_gif_frames(path, (110, 130))
        preview_planes.append(frames)
        
    frame_index = 0
    last_anim_time = time.time()
    
    title_font = ui_theme.get_arcade_font(52, bold=True)
    card_lbl_font = ui_theme.get_arcade_font(22, bold=True)
    card_sub_font = ui_theme.get_arcade_font(17, bold=True)
    
    while True:
        sky_fx.update()
        sky_fx.draw_sky(screen)
        
        ui_theme.draw_3d_title(screen, "CHOOSE YOUR BALLOON", title_font, WINDOW_WIDTH // 2, 75, extrude_depth=6)
        
        px, py, _ = get_pointer()
        cards = []
        
        current_time = time.time()
        if current_time - last_anim_time > 0.08:
            frame_index += 1
            last_anim_time = current_time
            
        start_x = 140
        spacing = 250
        card_y = 390
        
        for i, frames in enumerate(preview_planes):
            cx = start_x + i * spacing
            card_rect = pygame.Rect(0, 0, card_width, card_height)
            card_rect.center = (cx, card_y)
            
            hover = card_rect.collidepoint(px, py)
            visual_rect = card_rect.move(0, -6) if hover else card_rect
            
            border_c = (235, 130, 20) if hover else ui_theme.COLOR_PANEL_BORDER
            bg_c = (255, 255, 248) if hover else ui_theme.COLOR_PANEL_BG
            ui_theme.draw_arcade_panel(screen, visual_rect, border_color=border_c, bg_color=bg_c)
            
            # Pedestal background for balloon
            pedestal_rect = pygame.Rect(visual_rect.centerx - 70, visual_rect.y + 20, 140, 145)
            pygame.draw.rect(screen, (240, 245, 255), pedestal_rect, border_radius=15)
            pygame.draw.rect(screen, (200, 215, 235), pedestal_rect, 2, border_radius=15)
            
            cur_frame = frames[frame_index % len(frames)]
            frame_rect = cur_frame.get_rect(center=(visual_rect.centerx, visual_rect.y + 92))
            screen.blit(cur_frame, frame_rect)
            
            ui_theme.draw_text_with_outline(
                screen, f"BALLOON {i+1}", card_lbl_font, 
                (52, 152, 219) if hover else (70, 30, 10), 
                (255, 255, 255), visual_rect.centerx, visual_rect.y + 190, outline_width=2
            )
            ui_theme.draw_text_with_outline(
                screen, BALLOON_NAMES[i], card_sub_font, 
                (120, 70, 20), (255, 255, 255), visual_rect.centerx, visual_rect.y + 225, outline_width=1
            )
            
            if hover:
                pill_rect = pygame.Rect(visual_rect.centerx - 65, visual_rect.y + 252, 130, 26)
                pygame.draw.rect(screen, (46, 204, 113), pill_rect, border_radius=10)
                pygame.draw.rect(screen, (25, 95, 55), pill_rect, 2, border_radius=10)
                ui_theme.draw_text_with_outline(
                    screen, "SELECT", ui_theme.get_arcade_font(15, bold=True),
                    (255, 255, 255), (25, 95, 55), pill_rect.centerx, pill_rect.centery, outline_width=1
                )
                
            cards.append((frames, card_rect))
            
        screen.blit(crosshair, (px - 35, py - 35))
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.MOUSEBUTTONDOWN:
                now = time.time()
                if now - last_click_time > CLICK_DELAY:
                    gun_sound.play()
                    last_click_time = now
                    for frames, rect in cards:
                        if rect.collidepoint(px, py):
                            idx = cards.index((frames, rect))
                            return load_gif_frames(PLANE_GIF_PATHS[idx], (300, 300))
                            
        pygame.display.flip()
        clock.tick(60)

# ---------------- PAUSE MODAL ----------------
def show_pause_modal():
    """ Renders the centered nostalgic arcade pause dialogue """
    global last_click_time
    dim_overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    dim_overlay.fill((20, 15, 30, 155))
    screen.blit(dim_overlay, (0, 0))
    
    panel_rect = pygame.Rect(WINDOW_WIDTH // 2 - 220, 160, 440, 390)
    ui_theme.draw_arcade_panel(screen, panel_rect, title="GAME PAUSED")
    
    btn_resume = ui_theme.TactileButton("RESUME", WINDOW_WIDTH // 2, 275, width=280, height=64, color_scheme=ui_theme.BTN_GREEN)
    btn_restart = ui_theme.TactileButton("RESTART", WINDOW_WIDTH // 2, 355, width=280, height=64, color_scheme=ui_theme.BTN_YELLOW)
    btn_menu = ui_theme.TactileButton("MAIN MENU", WINDOW_WIDTH // 2, 435, width=280, height=64, color_scheme=ui_theme.BTN_BLUE)
    
    buttons = [("RESUME", btn_resume), ("RESTART", btn_restart), ("MENU", btn_menu)]
    
    while True:
        screen.blit(dim_overlay, (0, 0))
        ui_theme.draw_arcade_panel(screen, panel_rect, title="GAME PAUSED")
        
        px, py, _ = get_pointer()
        
        for name, btn in buttons:
            btn.update((px, py))
            btn.draw(screen)
            
        screen.blit(crosshair, (px - 35, py - 35))
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "EXIT"
            if event.type == pygame.KEYDOWN and (event.key == pygame.K_p or event.key == pygame.K_ESCAPE):
                return "RESUME"
            if event.type == pygame.MOUSEBUTTONDOWN:
                now = time.time()
                if now - last_click_time > CLICK_DELAY:
                    gun_sound.play()
                    last_click_time = now
                    for name, btn in buttons:
                        if btn.rect.collidepoint(px, py):
                            return name
                            
        pygame.display.flip()
        clock.tick(60)

# ---------------- GAMEPLAY ----------------
def play_game(mode, chosen_plane_frames):
    settings = {
        "EASY": {"speed": 3, "spawn": 1.2}, 
        "NORMAL": {"speed": 5, "spawn": 0.8}, 
        "HARD": {"speed": 8, "spawn": 0.4}
    }[mode]
    
    balloons, explosions, score = [], [], 0
    last_spawn, start = time.time(), time.time()
    GAME_TIME = 60
    num_frames = len(chosen_plane_frames)
    
    high_score = ui_theme.load_high_score()
    fx_manager = ui_theme.VisualEffectManager()
    btn_pause = ui_theme.TactileButton("|| PAUSE", WINDOW_WIDTH - 80, 52, width=130, height=54, color_scheme=ui_theme.BTN_BLUE, font_size=22)
    
    running = True
    while running:
        elapsed_time = time.time() - start
        remain = int(GAME_TIME - elapsed_time)
        
        # Round ended
        if remain <= 0:
            return score
            
        px, py, _ = get_pointer()
        
        # Spawning logic (Preserved)
        if time.time() - last_spawn > settings["spawn"]:
            balloons.append([random.randint(50, WINDOW_WIDTH-150), WINDOW_HEIGHT + 100, 0, time.time()])
            last_spawn = time.time()
            
        current_time = time.time()
        
        # Screen shake offset
        fx_manager.update()
        ox, oy = fx_manager.get_screen_offset()
        
        # 1. Background
        screen.blit(selected_background, (ox, oy))
        
        # 2. Balloon rendering and animation (Preserved logic)
        for b in balloons: 
            b[1] -= settings["speed"]
            
            if current_time - b[3] > 0.08:
                b[2] = (b[2] + 1) % num_frames
                b[3] = current_time
            
            current_frame = chosen_plane_frames[b[2]]
            screen.blit(current_frame, (b[0] + ox, b[1] + oy))
            
        # 3. Explosions
        for exp in explosions[:]:
            f = exp["frame"] // 3
            if f < len(explosion_frames):
                screen.blit(explosion_frames[f], (exp["pos"][0] + ox, exp["pos"][1] + oy))
                exp["frame"] += 1
            else: 
                explosions.remove(exp)
                
        # 4. Pop particles & score popups
        fx_manager.draw(screen)
        
        # 5. Classic Arcade HUD
        ui_theme.draw_arcade_hud(screen, score, max(high_score, score), remain, mode, WINDOW_WIDTH)
        
        # 6. Tactile Pause Button
        btn_pause.update((px, py))
        btn_pause.draw(screen)
        
        # 7. Crosshair
        screen.blit(crosshair, (px - 35, py - 35))
        
        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT: 
                return None
                
            # Pause Hotkeys (P or ESC)
            if event.type == pygame.KEYDOWN and (event.key == pygame.K_p or event.key == pygame.K_ESCAPE):
                pause_start = time.time()
                action = show_pause_modal()
                if action == "RESUME":
                    start += (time.time() - pause_start)
                elif action == "RESTART":
                    return "RESTART"
                elif action == "MENU" or action == "EXIT":
                    return "MENU"
                continue
                
            if event.type == pygame.MOUSEBUTTONDOWN:
                # Check Pause button click
                if btn_pause.rect.collidepoint(px, py):
                    pause_start = time.time()
                    action = show_pause_modal()
                    if action == "RESUME":
                        start += (time.time() - pause_start)
                    elif action == "RESTART":
                        return "RESTART"
                    elif action == "MENU" or action == "EXIT":
                        return "MENU"
                    continue
                    
                # Gun Fire & Balloon Collision (Preserved gameplay)
                gun_sound.play()
                for b in balloons[:]:
                    rect = pygame.Rect(b[0], b[1], 300, 300)
                    if rect.collidepoint(px, py):
                        balloons.remove(b)
                        pop_sound.play()
                        explosions.append({"pos": (b[0], b[1]), "frame": 0})
                        fx_manager.trigger_pop(b[0], b[1])
                        score += 1
                        
        pygame.display.flip()
        clock.tick(60)

# ---------------- GAME OVER ----------------
def game_over(score):
    global last_click_time
    pygame.mixer.music.stop()
    
    is_new_record, high_score = ui_theme.save_high_score(score)
    
    btn_replay = ui_theme.TactileButton("PLAY AGAIN", WINDOW_WIDTH // 2, 455, width=290, height=66, color_scheme=ui_theme.BTN_GREEN)
    btn_menu = ui_theme.TactileButton("MAIN MENU", WINDOW_WIDTH // 2, 540, width=290, height=66, color_scheme=ui_theme.BTN_YELLOW)
    
    # Celebratory floating confetti
    confetti = []
    palette = [(255, 75, 75), (255, 215, 0), (46, 204, 113), (52, 152, 219), (255, 120, 200)]
    for _ in range(35):
        confetti.append({
            "x": random.randint(0, WINDOW_WIDTH),
            "y": random.randint(-100, WINDOW_HEIGHT),
            "speed": random.uniform(1.2, 3.2),
            "wobble": random.uniform(0, math.tau),
            "size": random.randint(7, 12),
            "color": random.choice(palette)
        })
        
    # Rating stars (1 to 3)
    num_stars = 3 if score >= 25 else (2 if score >= 12 else (1 if score > 0 else 0))
    
    while True:
        # Background
        screen.blit(selected_background, (0, 0))
        
        # Soft Dimming Overlay
        dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((20, 15, 30, 150))
        screen.blit(dim, (0, 0))
        
        # Gentle floating confetti
        for c in confetti:
            c["y"] += c["speed"]
            c["wobble"] += 0.05
            if c["y"] > WINDOW_HEIGHT + 20:
                c["y"] = -20
                c["x"] = random.randint(0, WINDOW_WIDTH)
            cx = c["x"] + math.sin(c["wobble"]) * 14
            pygame.draw.rect(screen, c["color"], (cx, c["y"], c["size"], c["size"]))
            
        # Centered Carnival Game Over Panel
        card_rect = pygame.Rect(WINDOW_WIDTH // 2 - 250, 80, 500, 555)
        ui_theme.draw_arcade_panel(screen, card_rect, title="TIME'S UP!")
        
        # Golden performance stars
        star_y = card_rect.y + 60
        for s_idx in range(3):
            sx = WINDOW_WIDTH // 2 + (s_idx - 1) * 55
            filled = (s_idx < num_stars)
            ui_theme.draw_star(screen, sx, star_y, radius=22, 
                               color=(255, 215, 0) if filled else (210, 200, 190),
                               outline_color=(120, 70, 10) if filled else (150, 140, 130))
                               
        # NEW HIGH SCORE Ribbon if broken
        if is_new_record and score > 0:
            rec_rect = pygame.Rect(card_rect.centerx - 130, card_rect.y + 98, 260, 32)
            pygame.draw.rect(screen, (255, 215, 0), rec_rect, border_radius=10)
            pygame.draw.rect(screen, (160, 100, 10), rec_rect, 2, border_radius=10)
            ui_theme.draw_text_with_outline(
                screen, "★ NEW HIGH SCORE! ★", ui_theme.get_arcade_font(18, bold=True),
                (140, 30, 10), (255, 255, 255), rec_rect.centerx, rec_rect.centery, outline_width=1
            )
            
        # Score presentation
        score_y_offset = 145 if (is_new_record and score > 0) else 135
        ui_theme.draw_text_with_outline(
            screen, "FINAL SCORE", ui_theme.get_arcade_font(26, bold=True),
            (120, 70, 30), (255, 255, 255), WINDOW_WIDTH // 2, card_rect.y + score_y_offset, outline_width=2
        )
        ui_theme.draw_text_with_outline(
            screen, f"{score:06d}", ui_theme.get_arcade_font(56, bold=True),
            (235, 60, 60), (70, 20, 20), WINDOW_WIDTH // 2, card_rect.y + score_y_offset + 55, outline_width=3
        )
        
        # High Score label
        ui_theme.draw_text_with_outline(
            screen, "BEST SCORE", ui_theme.get_arcade_font(20, bold=True),
            (60, 130, 60), (255, 255, 255), WINDOW_WIDTH // 2, card_rect.y + score_y_offset + 115, outline_width=2
        )
        ui_theme.draw_text_with_outline(
            screen, f"{high_score:06d}", ui_theme.get_arcade_font(38, bold=True),
            (46, 180, 90), (20, 70, 30), WINDOW_WIDTH // 2, card_rect.y + score_y_offset + 155, outline_width=3
        )
        
        px, py, _ = get_pointer()
        
        btn_replay.update((px, py))
        btn_menu.update((px, py))
        btn_replay.draw(screen)
        btn_menu.draw(screen)
        
        screen.blit(crosshair, (px - 35, py - 35))
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: 
                return "EXIT"
            if event.type == pygame.MOUSEBUTTONDOWN:
                now = time.time()
                if now - last_click_time > CLICK_DELAY:
                    gun_sound.play()
                    last_click_time = now
                    if btn_replay.rect.collidepoint(px, py):
                        pygame.mixer.music.play(-1)
                        return "REPLAY"
                    if btn_menu.rect.collidepoint(px, py):
                        return "MENU"
                        
        pygame.display.flip()
        clock.tick(60)

def main():
    global selected_background
    while True:
        current_mode = menu()
        if current_mode == "EXIT":
            break
        
        if not select_background():
            break

        chosen_plane_frames = select_plane()
        if chosen_plane_frames is None:
            break

        active_game = True
        while active_game:
            score = play_game(current_mode, chosen_plane_frames)
            
            if score is None:
                active_game = False
                break
                
            if score == "RESTART":
                continue
            elif score == "MENU":
                active_game = False
                break
                
            result = game_over(score)
            
            if result == "REPLAY":
                continue
            elif result == "MENU":
                active_game = False
            elif result == "EXIT":
                active_game = False
                cap.release()
                pygame.quit()
                sys.exit()

    cap.release()
    pygame.quit()

if __name__ == "__main__":
    main()