import os
import cv2
import mediapipe as mp
import pygame
import random
import time
import sys
import math
import numpy as np

# Pillow Library Check
try:
    from PIL import Image, ImageSequence, ImageDraw, ImageFilter
except ImportError:
    print("Error: 'Pillow' library missing. Please run 'pip install pillow'.")
    sys.exit()

# Import 90s Retro Military Arcade Theme System
import ui_theme

# Base directory for absolute asset paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
def asset_path(filename):
    return os.path.join(BASE_DIR, filename)

# Initialize Pygame & Audio
pygame.init()
pygame.mixer.pre_init(48000, -16, 2, 2048)
pygame.mixer.init()

# Window Setup
WINDOW_WIDTH, WINDOW_HEIGHT = 1280, 720
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("GUNSHIP BATTLE // AIR DEFENSE 1999 [ARCADE]")
clock = pygame.time.Clock()

# Fonts (Maintained from ui_theme)
font_large = ui_theme.get_retro_font("stencil", 60, bold=True)
font_medium = ui_theme.get_retro_font("stencil", 36, bold=True)
font_small = ui_theme.get_retro_font("digital", 24, bold=True)

# ---------------- GIF HELPER FUNCTION ----------------
def load_gif_frames(filepath, size):
    """ Loads GIF frames and scales them to Pygame surfaces """
    pil_img = Image.open(filepath)
    frames = []
    for frame in ImageSequence.Iterator(pil_img):
        frame_rgba = frame.convert("RGBA")
        pygame_surface = pygame.image.fromstring(
            frame_rgba.tobytes(), frame_rgba.size, "RGBA"
        )
        scaled_surface = pygame.transform.scale(pygame_surface, size).convert_alpha()
        frames.append(scaled_surface)
    return frames

# ---------------- LOAD ASSETS ----------------
BACKGROUND_PNG_PATHS = [
    asset_path("background1.jpg"),
    asset_path("background2.png"),
    asset_path("background3.png")
]

PLANE_GIF_PATHS = [
    asset_path("helicopter1.gif"),
    asset_path("helicopter2.gif"),
    asset_path("helicopter3.gif"),
    asset_path("helicopter4.gif"),
    asset_path("helicopter5.gif")
]

raw_crosshair = pygame.transform.scale(pygame.image.load(asset_path("crosshair.png")).convert_alpha(), (70, 70))
crosshair_fx = ui_theme.RetroCrosshair(raw_crosshair)

explosion_frames = [
    pygame.transform.scale(pygame.image.load(asset_path(f"explosion_{i}.png")).convert_alpha(), (120, 120))
    for i in range(1, 5)
]

gun_sound = pygame.mixer.Sound(asset_path("gun.wav"))
pop_sound = pygame.mixer.Sound(asset_path("pop.wav"))
balloon_spawn_sound = pygame.mixer.Sound(asset_path("balloon.wav"))
balloon_spawn_sound.set_volume(0.9)
game_over_sound = pygame.mixer.Sound(asset_path("game_over_sound.wav"))

pygame.mixer.music.load(asset_path("bgm.mp3"))
pygame.mixer.music.play(-1)

last_click_time = 0
CLICK_DELAY = 0.30

# ---------------- ENHANCED MULTI-LAYER BACKGROUND SYSTEM ----------------
class BackgroundSystem:
    """
    High-performance multi-layer parallax background with:
    - Mathematically seamless vertical looping (zero seam, zero gaps, zero jumps)
    - Delta-time based scrolling (smooth continuous motion)
    - Multi-layer visual depth:
        * Layer 0: Far scenery/sky (seamless base map)
        * Layer 1: Mid-altitude volumetric soft clouds drifting with parallax
        * Layer 2: High-speed atmospheric air streak particles for flight immersion
        * Layer 3: Atmospheric horizon depth & subtle cinematic lighting
    - Interactive camera parallax damping connected to finger/crosshair tracking
    - Natural aerodynamic turbulence swaying
    - Pre-computed and cached surfaces (zero per-frame image loading or allocations)
    """
    def __init__(self, map_paths, window_width=WINDOW_WIDTH, window_height=WINDOW_HEIGHT):
        self.w = window_width
        self.h = window_height
        self.tile_w = window_width + 100
        self.tile_h = window_height
        self.map_paths = map_paths
        self.current_idx = 0
        
        self.seamless_tiles = []
        self.menu_bgs = []
        self.thumbnails = []
        
        # 1. Precompute seamless looping tiles and converted surfaces for all maps
        overlap = 180
        t = np.linspace(0, 1, overlap)[:, None, None]
        s = t * t * (3.0 - 2.0 * t)
        
        for p in map_paths:
            im = Image.open(p).convert('RGB').resize((self.tile_w, self.tile_h + overlap), Image.Resampling.BILINEAR)
            arr = np.array(im, dtype=np.float32)
            H, W, C = arr.shape
            L = H - overlap
            tile = np.zeros((L, W, C), dtype=np.float32)
            tile[overlap:L] = arr[overlap:L]
            tile[:overlap] = (1.0 - s) * arr[L:H] + s * arr[:overlap]
            surf = pygame.image.frombuffer(tile.astype(np.uint8).tobytes(), (W, L), 'RGB').convert()
            self.seamless_tiles.append(surf)
            
            m_im = Image.open(p).convert('RGB').resize((self.w, self.h), Image.Resampling.BILINEAR)
            m_surf = pygame.image.frombuffer(np.array(m_im, dtype=np.uint8).tobytes(), (self.w, self.h), 'RGB').convert()
            self.menu_bgs.append(m_surf)
            
            th_im = Image.open(p).convert('RGB').resize((200, 140), Image.Resampling.BILINEAR)
            th_surf = pygame.image.frombuffer(np.array(th_im, dtype=np.uint8).tobytes(), (200, 140), 'RGB').convert()
            self.thumbnails.append(th_surf)
            
        # 2. Precompute procedural soft volumetric cloud surfaces
        self.cloud_surfaces = []
        cloud_specs = [(480, 180, 65), (560, 140, 50), (420, 160, 60), (620, 210, 45)]
        for i, (cw, ch, ca) in enumerate(cloud_specs):
            rng = random.Random(i * 31 + 42)
            mask = Image.new('L', (cw, ch), 0)
            draw = ImageDraw.Draw(mask)
            for _ in range(rng.randint(8, 13)):
                cx = rng.randint(int(cw * 0.2), int(cw * 0.8))
                cy = rng.randint(int(ch * 0.3), int(ch * 0.7))
                rx = rng.randint(int(cw * 0.16), int(cw * 0.33))
                ry = rng.randint(int(ch * 0.22), int(ch * 0.40))
                draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=rng.randint(185, 255))
            mask = mask.filter(ImageFilter.GaussianBlur(radius=int(ch * 0.14)))
            m_arr = (np.array(mask, dtype=np.float32) / 255.0) * ca
            rgba = np.zeros((ch, cw, 4), dtype=np.uint8)
            rgba[..., :3] = 248
            rgba[..., 3] = m_arr.astype(np.uint8)
            c_surf = pygame.image.frombuffer(rgba.tobytes(), (cw, ch), 'RGBA').convert_alpha()
            self.cloud_surfaces.append(c_surf)
            
        # 3. Precompute atmospheric horizon lighting
        self.vignette_surf = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        for y_idx in range(120):
            a = int(32 * (1.0 - y_idx / 120.0))
            pygame.draw.line(self.vignette_surf, (210, 235, 255, a), (0, y_idx), (self.w, y_idx))
        for y_idx in range(self.h - 90, self.h):
            a = int(28 * ((y_idx - (self.h - 90)) / 90.0))
            pygame.draw.line(self.vignette_surf, (15, 25, 40, a), (0, y_idx), (self.w, y_idx))
            
        # 4. Atmospheric speed streaks
        self.particles = []
        for _ in range(28):
            self.particles.append([
                random.uniform(0, self.w),
                random.uniform(0, self.h),
                random.uniform(220, 390),
                random.uniform(25, 55),
                random.randint(25, 60)
            ])
        self.streak_surf = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        
        # 5. Cloud instances
        self.cloud_instances = []
        for _ in range(5):
            c_idx = random.randint(0, len(self.cloud_surfaces) - 1)
            self.cloud_instances.append({
                'idx': c_idx,
                'x': random.uniform(-100, self.w - 150),
                'y': random.uniform(-120, self.h),
                'speed_y': random.uniform(115, 150),
                'speed_x': random.uniform(-8, 12),
                'sway_phase': random.uniform(0, math.pi * 2),
                'sway_amp': random.uniform(6, 14)
            })
            
        self.bg_y = 0.0
        self.base_speed = 92.0
        self.cam_x = 0.0
        self.cam_y = 0.0
        self.time_val = 0.0

    def set_map(self, idx):
        if 0 <= idx < len(self.map_paths):
            self.current_idx = idx

    def get_selected_background(self):
        return self.menu_bgs[self.current_idx]

    def update(self, dt, hx=None, hy=None):
        self.time_val += dt
        self.bg_y = (self.bg_y + self.base_speed * dt) % self.tile_h
        
        if hx is not None and hy is not None:
            tx = -(hx - self.w / 2) * 0.032
            ty = -(hy - self.h / 2) * 0.018
        else:
            tx, ty = 0.0, 0.0
            
        self.cam_x += (tx - self.cam_x) * min(1.0, 5.0 * dt)
        self.cam_y += (ty - self.cam_y) * min(1.0, 5.0 * dt)
        
        for c in self.cloud_instances:
            c['y'] += c['speed_y'] * dt
            c['x'] += c['speed_x'] * dt
            c['sway_phase'] += 0.8 * dt
            if c['y'] > self.h + 230:
                c['y'] = -230
                c['x'] = random.uniform(-150, self.w - 150)
                c['idx'] = random.randint(0, len(self.cloud_surfaces) - 1)
                
        for p in self.particles:
            p[1] += p[2] * dt
            if p[1] > self.h + p[3]:
                p[1] = -p[3]
                p[0] = random.uniform(0, self.w)

    def draw(self, surface):
        sway_x = math.sin(self.time_val * 0.75) * 5.0
        sway_y = math.cos(self.time_val * 1.05) * 3.0
        eff_cam_x = self.cam_x + sway_x
        eff_cam_y = self.cam_y + sway_y
        
        tile = self.seamless_tiles[self.current_idx]
        base_x = int((self.w - self.tile_w) // 2 + eff_cam_x * 0.4)
        base_y = self.bg_y + eff_cam_y * 0.4
        
        start_y = (base_y % self.tile_h) - self.tile_h
        while start_y < self.h:
            surface.blit(tile, (base_x, int(start_y)))
            start_y += self.tile_h
            
        for c in self.cloud_instances:
            csurf = self.cloud_surfaces[c['idx']]
            cx = int(c['x'] + math.sin(c['sway_phase']) * c['sway_amp'] + eff_cam_x * 0.75)
            cy = int(c['y'] + eff_cam_y * 0.75)
            surface.blit(csurf, (cx, cy))
            
        self.streak_surf.fill((0, 0, 0, 0))
        for p in self.particles:
            px = int(p[0] + eff_cam_x * 1.2)
            py = int(p[1])
            length = int(p[3])
            alpha = p[4]
            pygame.draw.line(self.streak_surf, (240, 248, 255, alpha), (px, py), (px, py + length), 1)
        surface.blit(self.streak_surf, (0, 0))
        surface.blit(self.vignette_surf, (0, 0))

# Initialize background system
bg_system = BackgroundSystem(BACKGROUND_PNG_PATHS)
selected_background = bg_system.get_selected_background()

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
    """ Returns (x, y, is_hand) with seamless mouse fallback for arcade testing / gameplay """
    hx, hy = get_hand()
    if hx is not None and hy is not None:
        return hx, hy, True
    mx, my = pygame.mouse.get_pos()
    return mx, my, False

# ---------------- LEGACY DRAW HELPER (For Compatibility) ----------------
def draw_text(text, font, color, x, y, center=True):
    return ui_theme.draw_retro_text(screen, text, font, color, x, y, 
                                    shadow_color=ui_theme.COLOR_BLACK, shadow_offset=(2, 2), center=center)

# ---------------- MAIN MENU (90s Military Arcade Title Screen) ----------------
def menu():
    global last_click_time
    if not pygame.mixer.music.get_busy():
        pygame.mixer.music.play(-1)

    # Buttons
    btn_easy = ui_theme.MilitaryButton("RECRUIT // EASY", WINDOW_WIDTH // 2, 255, width=340, height=58, 
                                       theme=ui_theme.BTN_OLIVE, subtext="SLOW TARGETS - TRAINING SECTOR")
    btn_normal = ui_theme.MilitaryButton("VETERAN // NORMAL", WINDOW_WIDTH // 2, 325, width=340, height=58, 
                                         theme=ui_theme.BTN_AMBER, subtext="STANDARD SPEED - COMBAT DEFENSE")
    btn_hard = ui_theme.MilitaryButton("ACE PILOT // HARD", WINDOW_WIDTH // 2, 395, width=340, height=58, 
                                       theme=ui_theme.BTN_RED, subtext="RAPID SWARM - MAXIMUM HOSTILITY")
    btn_brief = ui_theme.MilitaryButton("MISSION BRIEFING", WINDOW_WIDTH // 2, 465, width=340, height=58, 
                                        theme=ui_theme.BTN_STEEL, subtext="RULES & WEAPON CONTROLS")
    btn_exit = ui_theme.MilitaryButton("ABORT TO DESKTOP", WINDOW_WIDTH // 2, 535, width=340, height=58, 
                                       theme=ui_theme.BTN_STEEL, subtext="QUIT SIMULATOR")

    buttons = [
        ("EASY", btn_easy),
        ("NORMAL", btn_normal),
        ("HARD", btn_hard),
        ("BRIEFING", btn_brief),
        ("EXIT", btn_exit)
    ]

    attract_timer = 0.0

    while True:
        dt = clock.tick(60) / 1000.0
        dt = min(dt, 0.05)
        attract_timer += dt
        px, py, is_hand = get_pointer()
        
        # Parallax Background
        bg_system.update(dt * 0.4, px, py)
        bg_system.draw(screen)

        # 1. 90s Military Arcade Title Banner
        ui_theme.draw_arcade_title(screen, WINDOW_WIDTH // 2, 105)

        # 2. Top-Gun High Record Bar
        high_score = ui_theme.load_high_score()
        font_hi = ui_theme.get_retro_font("digital", 16, bold=True)
        hi_box = pygame.Rect(WINDOW_WIDTH // 2 - 200, 185, 400, 32)
        ui_theme.draw_military_panel(screen, hi_box, bg_color=(14, 18, 16), border_color=ui_theme.COLOR_OLIVE_MID, rivets=False)
        ui_theme.draw_retro_text(screen, f"★ TOP GUN RECORD: {high_score * 100:07d} PTS ★", font_hi, 
                                ui_theme.COLOR_RADAR_GREEN, WINDOW_WIDTH // 2, 201)

        # 3. Update & Draw Buttons
        is_hovering_any = False
        for opt, btn in buttons:
            hover = btn.update((px, py))
            if hover:
                is_hovering_any = True
            btn.draw(screen)

        # 4. Attract Mode / Insert Coin Footer Text
        blink = int(attract_timer * 3) % 2 == 0
        blink_col = ui_theme.COLOR_AMBER_BRIGHT if blink else ui_theme.COLOR_AMBER_DIM
        font_attract = ui_theme.get_retro_font("stencil", 16, bold=True)
        ui_theme.draw_retro_text(screen, "★ INSERT COIN // CLICK TARGET TO ENGAGE // READY PLAYER ONE ★", 
                                font_attract, blink_col, WINDOW_WIDTH // 2, 630)

        # Input mode badge
        font_input = ui_theme.get_retro_font("digital", 13, bold=False)
        inp_text = "INPUT: WEBCAM HAND TRACKING ACTIVE" if is_hand else "INPUT: MOUSE POINTER TARGETING [DEFAULT]"
        ui_theme.draw_retro_text(screen, inp_text, font_input, ui_theme.COLOR_TEXT_DIM, WINDOW_WIDTH // 2, 665)

        # 5. Draw Crosshair
        crosshair_fx.update(dt, is_locked=is_hovering_any)
        crosshair_fx.draw(screen, px, py)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "EXIT"
            if event.type == pygame.MOUSEBUTTONDOWN:
                now = time.time()
                if now - last_click_time > CLICK_DELAY:
                    gun_sound.play()
                    crosshair_fx.trigger_shot()
                    last_click_time = now
                    for opt, btn in buttons:
                        if btn.rect.collidepoint(px, py):
                            if opt == "BRIEFING":
                                ui_theme.show_briefing_screen(screen, clock, get_pointer, crosshair_fx, gun_sound, bg_system)
                            else:
                                return opt
        
        pygame.display.flip()

# ---------------- VISUAL BACKGROUND SELECTION (THEATER OF OPERATIONS) ----------------
def select_background():
    global last_click_time, selected_background
    card_width, card_height = 290, 380
    
    btn_deploy = ui_theme.MilitaryButton("CONFIRM THEATER", WINDOW_WIDTH // 2 - 140, 630, width=260, height=58, theme=ui_theme.BTN_OLIVE)
    btn_back = ui_theme.MilitaryButton("BACK TO HQ", WINDOW_WIDTH // 2 + 140, 630, width=220, height=58, theme=ui_theme.BTN_STEEL)

    while True:
        dt = clock.tick(60) / 1000.0
        dt = min(dt, 0.05)
        px, py, is_hand = get_pointer()
        
        # Dark Gunmetal Command Screen
        screen.fill(ui_theme.COLOR_GUNMETAL_DARK)

        # Top Header Dossier
        header_rect = pygame.Rect(WINDOW_WIDTH // 2 - 450, 20, 900, 72)
        ui_theme.draw_military_panel(screen, header_rect, title="THEATER OF OPERATIONS // SECTOR SELECTION",
                                    subtitle="DESIGNATE COMBAT SECTOR FOR AIR DEFENSE ENGAGEMENT",
                                    bg_color=(18, 24, 21), border_color=ui_theme.COLOR_OLIVE_LIGHT, hazard_header=True)
        
        cards = []
        start_x = 220
        spacing = 420
        card_y = 350
        
        for i, thumb in enumerate(bg_system.thumbnails):
            cx = start_x + i * spacing
            card_rect = pygame.Rect(0, 0, card_width, card_height)
            card_rect.center = (cx, card_y)
            
            hover = card_rect.collidepoint(px, py)
            is_selected = (i == bg_system.current_idx)
            sec_info = ui_theme.SECTORS[i]

            # Panel Styling based on selection / hover
            border_col = ui_theme.COLOR_AMBER_BRIGHT if (hover or is_selected) else ui_theme.COLOR_OLIVE_MID
            bg_col = (25, 34, 28) if is_selected else ((30, 42, 34) if hover else (18, 22, 20))
            
            ui_theme.draw_military_panel(screen, card_rect, bg_color=bg_col, border_color=border_col, chamfer=6)

            # Sector Title
            font_sec = ui_theme.get_retro_font("stencil", 20, bold=True)
            ui_theme.draw_retro_text(screen, sec_info["code"], font_sec, 
                                    ui_theme.COLOR_AMBER_BRIGHT if is_selected else ui_theme.COLOR_KHAKI_BRIGHT, 
                                    cx, card_rect.top + 26)
            
            font_sec_name = ui_theme.get_retro_font("digital", 14, bold=True)
            ui_theme.draw_retro_text(screen, sec_info["name"], font_sec_name, ui_theme.COLOR_WHITE, cx, card_rect.top + 48)

            # Map Thumbnail Frame
            thumb_rect = thumb.get_rect(center=(cx, card_rect.top + 135))
            pygame.draw.rect(screen, ui_theme.COLOR_BLACK, thumb_rect.inflate(6, 6))
            screen.blit(thumb, thumb_rect)
            pygame.draw.rect(screen, border_col, thumb_rect.inflate(2, 2), 1)

            # Sector Telemetry
            font_stat = ui_theme.get_retro_font("digital", 12, bold=False)
            ui_theme.draw_retro_text(screen, sec_info["grid"], font_stat, ui_theme.COLOR_RADAR_GREEN, cx, card_rect.top + 225)
            ui_theme.draw_retro_text(screen, f"THREAT: {sec_info['threat']}", font_stat, 
                                    ui_theme.COLOR_ALERT_RED_BRIGHT if i == 2 else ui_theme.COLOR_AMBER_BRIGHT, cx, card_rect.top + 245)

            # Brief Description (2 lines)
            words = sec_info["desc"].split(" ")
            line1 = " ".join(words[:4])
            line2 = " ".join(words[4:])
            ui_theme.draw_retro_text(screen, line1, font_stat, ui_theme.COLOR_TEXT_DIM, cx, card_rect.top + 275)
            ui_theme.draw_retro_text(screen, line2, font_stat, ui_theme.COLOR_TEXT_DIM, cx, card_rect.top + 295)

            # Selection Stamp Badge
            status_txt = "★ DEPLOYED HERE ★" if is_selected else ("▶ SELECT ◀" if hover else "STANDBY")
            status_col = ui_theme.COLOR_RADAR_GREEN if is_selected else (ui_theme.COLOR_AMBER if hover else ui_theme.COLOR_STEEL_LIGHT)
            font_badge = ui_theme.get_retro_font("stencil", 15, bold=True)
            ui_theme.draw_retro_text(screen, status_txt, font_badge, status_col, cx, card_rect.bottom - 24)

            cards.append((i, card_rect))

        # Bottom Buttons
        btn_deploy.update((px, py))
        btn_back.update((px, py))
        btn_deploy.draw(screen)
        btn_back.draw(screen)
            
        crosshair_fx.update(dt, any(r.collidepoint(px, py) for _, r in cards) or btn_deploy.hover or btn_back.hover)
        crosshair_fx.draw(screen, px, py)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return False
            if event.type == pygame.MOUSEBUTTONDOWN:
                now = time.time()
                if now - last_click_time > CLICK_DELAY:
                    gun_sound.play()
                    crosshair_fx.trigger_shot()
                    last_click_time = now
                    for idx, rect in cards:
                        if rect.collidepoint(px, py):
                            bg_system.set_map(idx)
                            selected_background = bg_system.get_selected_background()
                    if btn_deploy.rect.collidepoint(px, py):
                        return True
                    if btn_back.rect.collidepoint(px, py):
                        return False
                            
        pygame.display.flip()

# ---------------- VISUAL PLANE GIF SELECTION (THREAT RECONNAISSANCE) ----------------
cached_plane_previews = None
def select_plane():
    global last_click_time, cached_plane_previews
    
    if cached_plane_previews is None:
        cached_plane_previews = [load_gif_frames(path, (110, 130)) for path in PLANE_GIF_PATHS]
        
    preview_planes = cached_plane_previews
    card_width, card_height = 224, 385
        
    frame_index = 0
    last_anim_time = time.time()
    selected_idx = 0

    btn_launch = ui_theme.MilitaryButton("COMMENCE COMBAT", WINDOW_WIDTH // 2 - 140, 630, width=280, height=58, theme=ui_theme.BTN_OLIVE)
    btn_back = ui_theme.MilitaryButton("BACK", WINDOW_WIDTH // 2 + 150, 630, width=180, height=58, theme=ui_theme.BTN_STEEL)
    
    while True:
        dt = clock.tick(60) / 1000.0
        dt = min(dt, 0.05)
        px, py, is_hand = get_pointer()
        
        # Dark Military Command Screen
        screen.fill(ui_theme.COLOR_GUNMETAL_DARK)

        # Header Banner
        header_rect = pygame.Rect(WINDOW_WIDTH // 2 - 470, 20, 940, 72)
        ui_theme.draw_military_panel(screen, header_rect, title="THREAT RECONNAISSANCE // ENEMY ROTORCRAFT",
                                    subtitle="SELECT HOSTILE GUNSHIP TARGET PROFILE FOR ENGAGEMENT",
                                    bg_color=(18, 24, 21), border_color=ui_theme.COLOR_OLIVE_LIGHT, hazard_header=True)
        
        cards = []
        
        current_time = time.time()
        if current_time - last_anim_time > 0.08:
            frame_index += 1
            last_anim_time = current_time
            
        start_x = 148
        spacing = 246
        card_y = 350
        
        for i, frames in enumerate(preview_planes):
            cx = start_x + i * spacing
            card_rect = pygame.Rect(0, 0, card_width, card_height)
            card_rect.center = (cx, card_y)
            
            hover = card_rect.collidepoint(px, py)
            is_selected = (i == selected_idx)
            info = ui_theme.HELICOPTER_PROFILES[i]

            border_col = ui_theme.COLOR_AMBER_BRIGHT if (hover or is_selected) else ui_theme.COLOR_OLIVE_MID
            bg_col = (25, 34, 28) if is_selected else ((30, 42, 34) if hover else (18, 22, 20))
            
            ui_theme.draw_military_panel(screen, card_rect, bg_color=bg_col, border_color=border_col, chamfer=6)

            # Design & NATO Name
            font_d = ui_theme.get_retro_font("digital", 13, bold=True)
            ui_theme.draw_retro_text(screen, info["design"], font_d, ui_theme.COLOR_KHAKI, cx, card_rect.top + 22)

            font_n = ui_theme.get_retro_font("stencil", 16, bold=True)
            ui_theme.draw_retro_text(screen, info["name"], font_n, 
                                    ui_theme.COLOR_AMBER_BRIGHT if is_selected else ui_theme.COLOR_WHITE, cx, card_rect.top + 42)

            # Animated GIF Preview Box with Target Lock Brackets
            box_rect = pygame.Rect(cx - 65, card_rect.top + 65, 130, 135)
            pygame.draw.rect(screen, (10, 16, 12), box_rect)
            pygame.draw.rect(screen, (30, 48, 35), box_rect, 1)
            ui_theme.draw_target_lock_brackets(screen, box_rect, color=border_col, corner_len=12)

            cur_frame = frames[frame_index % len(frames)]
            frame_rect = cur_frame.get_rect(center=box_rect.center)
            screen.blit(cur_frame, frame_rect)

            # Chopper Role & Threat Rating
            font_r = ui_theme.get_retro_font("digital", 12, bold=False)
            ui_theme.draw_retro_text(screen, info["role"], font_r, ui_theme.COLOR_KHAKI_BRIGHT, cx, card_rect.top + 220)
            ui_theme.draw_retro_text(screen, f"THREAT: {info['threat']}", font_r, ui_theme.COLOR_ALERT_RED_BRIGHT, cx, card_rect.top + 242)

            # Tactical Stats
            ui_theme.draw_retro_text(screen, info["stats"], font_r, ui_theme.COLOR_RADAR_GREEN, cx, card_rect.top + 270)

            # Select Indicator
            status_txt = "★ TARGET LOCKED ★" if is_selected else ("▶ SELECT ◀" if hover else "AVAILABLE")
            status_col = ui_theme.COLOR_RADAR_GREEN if is_selected else (ui_theme.COLOR_AMBER if hover else ui_theme.COLOR_STEEL_LIGHT)
            font_badge = ui_theme.get_retro_font("stencil", 14, bold=True)
            ui_theme.draw_retro_text(screen, status_txt, font_badge, status_col, cx, card_rect.bottom - 24)
            
            cards.append((i, frames, card_rect))

        btn_launch.update((px, py))
        btn_back.update((px, py))
        btn_launch.draw(screen)
        btn_back.draw(screen)
            
        crosshair_fx.update(dt, any(r.collidepoint(px, py) for _, _, r in cards) or btn_launch.hover or btn_back.hover)
        crosshair_fx.draw(screen, px, py)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return None
            if event.type == pygame.MOUSEBUTTONDOWN:
                now = time.time()
                if now - last_click_time > CLICK_DELAY:
                    gun_sound.play()
                    crosshair_fx.trigger_shot()
                    last_click_time = now
                    for idx, frames, rect in cards:
                        if rect.collidepoint(px, py):
                            selected_idx = idx
                    if btn_launch.rect.collidepoint(px, py):
                        return load_gif_frames(PLANE_GIF_PATHS[selected_idx], (250, 250))
                    if btn_back.rect.collidepoint(px, py):
                        return None
                            
        pygame.display.flip()

# ---------------- GAMEPLAY LOOP ----------------
def play_game(mode, chosen_plane_frames):
    settings = {"EASY": {"speed": 3, "spawn": 1.2}, "NORMAL": {"speed": 5, "spawn": 0.8}, "HARD": {"speed": 8, "spawn": 0.4}}[mode]
    balloons, explosions, score = [], [], 0
    last_spawn, start = time.time(), time.time()
    GAME_TIME = 60
    num_frames = len(chosen_plane_frames)
    
    # Retro Arcade Visual Systems
    hud = ui_theme.RetroArcadeHUD(WINDOW_WIDTH, WINDOW_HEIGHT)
    combat_text = ui_theme.CombatTextManager()
    
    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        dt = min(dt, 0.05)
        
        elapsed_time = time.time() - start
        remain = int(GAME_TIME - elapsed_time)
        
        # Time expired -> Mission completed
        if remain <= 0:
            return score
        
        px, py, is_hand = get_pointer()
        
        # Spawning enemies
        if time.time() - last_spawn > settings["spawn"]:
            balloons.append([random.randint(50, WINDOW_WIDTH-150), WINDOW_HEIGHT + 100, 0, time.time()])
            balloon_spawn_sound.play()
            last_spawn = time.time()

        # ---------------- MULTI-LAYER PARALLAX BACKGROUND ----------------
        bg_system.update(dt, px, py)
        bg_system.draw(screen)
        # -----------------------------------------------------------------
        
        current_time = time.time()
        
        # Render Enemy Helicopters
        is_hovering_enemy = False
        for b in balloons: 
            b[1] -= settings["speed"]
            
            if current_time - b[3] > 0.08:
                b[2] = (b[2] + 1) % num_frames
                b[3] = current_time
            
            current_frame = chosen_plane_frames[b[2]]
            screen.blit(current_frame, (b[0], b[1]))

            # Tactical Target Lock Brackets around Helicopter Hitbox
            b_rect = pygame.Rect(b[0], b[1], 250, 250)
            if b_rect.collidepoint(px, py):
                is_hovering_enemy = True
                ui_theme.draw_target_lock_brackets(screen, b_rect, color=ui_theme.COLOR_ALERT_RED_BRIGHT, corner_len=18)
            else:
                ui_theme.draw_target_lock_brackets(screen, b_rect, color=ui_theme.COLOR_OLIVE_MID, corner_len=12)
            
        # Render Explosions
        for exp in explosions[:]:
            f = exp["frame"] // 3
            if f < len(explosion_frames):
                screen.blit(explosion_frames[f], exp["pos"])
                exp["frame"] += 1
            else: 
                explosions.remove(exp)
        
        # Combat Floating Text
        combat_text.update(dt)
        combat_text.draw(screen)

        # Draw Retro Arcade HUD
        hud.update(dt)
        hud.draw(screen, score, remain, mode=mode, total_time=GAME_TIME)

        # Draw Targeting Crosshair
        crosshair_fx.update(dt, is_locked=is_hovering_enemy)
        crosshair_fx.draw(screen, px, py)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: 
                return None
            
            # Tactical Pause via [P] or [ESC]
            if event.type == pygame.KEYDOWN and (event.key == pygame.K_p or event.key == pygame.K_ESCAPE):
                pause_res = ui_theme.pause_screen(screen, clock, get_pointer, crosshair_fx, gun_sound, bg_system)
                if pause_res == "EXIT":
                    return None
                elif pause_res == "RESTART":
                    return "RESTART"
                elif pause_res == "MENU":
                    return "MENU"
                elif pause_res == "RESUME":
                    # Recalculate start timer to prevent losing time while paused
                    start = time.time() - elapsed_time
            
            # Fire Cannon
            if event.type == pygame.MOUSEBUTTONDOWN:
                gun_sound.play()
                crosshair_fx.trigger_shot()
                for b in balloons[:]:
                    rect = pygame.Rect(b[0], b[1], 250, 250)
                    if rect.collidepoint(px, py):
                        balloons.remove(b)
                        pop_sound.play()
                        explosions.append({"pos": (b[0], b[1]), "frame": 0})
                        score += 1
                        combat_text.add("+100 PTS", b[0] + 125, b[1] + 90, color=ui_theme.COLOR_AMBER_BRIGHT, size=24)
        
        pygame.display.flip()

# ---------------- GAME OVER / MISSION DEBRIEF SCREEN ----------------
def game_over(score, mode):
    global last_click_time
    pygame.mixer.music.stop()
    game_over_sound.play()

    # Save high score
    is_new_record, high_score = ui_theme.save_high_score(score)

    btn_replay = ui_theme.MilitaryButton("RETRY MISSION", WINDOW_WIDTH // 2 - 160, 540, width=280, height=64, theme=ui_theme.BTN_OLIVE)
    btn_menu = ui_theme.MilitaryButton("RETURN TO BASE", WINDOW_WIDTH // 2 + 160, 540, width=280, height=64, theme=ui_theme.BTN_AMBER)

    # Determine Pilot Combat Rank
    if score >= 35:
        rank_title = "★ TOP GUN ACE PILOT ★★★"
        rank_badge = "RANK: SUPREME AIR DEFENDER"
        rank_color = ui_theme.COLOR_RADAR_GREEN
    elif score >= 25:
        rank_title = "★ SQUADRON LEADER ★★"
        rank_badge = "RANK: SENIOR FLIGHT COMMANDER"
        rank_color = ui_theme.COLOR_AMBER_BRIGHT
    elif score >= 15:
        rank_title = "★ FLIGHT LIEUTENANT ★"
        rank_badge = "RANK: EXPERIENCED AIR DEFENDER"
        rank_color = ui_theme.COLOR_KHAKI_BRIGHT
    else:
        rank_title = "RECRUIT GUNNER"
        rank_badge = "RANK: AIR CAVALRY ROOKIE"
        rank_color = ui_theme.COLOR_STEEL_BRIGHT

    blink_timer = 0.0

    while True:
        dt = clock.tick(60) / 1000.0
        dt = min(dt, 0.05)
        blink_timer += dt
        px, py, is_hand = get_pointer()
        
        bg_system.update(dt * 0.3, px, py)
        bg_system.draw(screen)

        # Center Debriefing Dossier Box
        debrief_rect = pygame.Rect(WINDOW_WIDTH // 2 - 420, 70, 840, 560)
        ui_theme.draw_military_panel(screen, debrief_rect, title="OPERATION REPORT // MISSION DEBRIEF",
                                    subtitle=f"HEADQUARTERS DEBRIEFING // ENGAGEMENT DIFFICULTY: [{mode}]",
                                    bg_color=(16, 22, 19), border_color=ui_theme.COLOR_OLIVE_LIGHT, hazard_header=True)

        # New High Score Flash Alert
        if is_new_record:
            blink = int(blink_timer * 5) % 2 == 0
            if blink:
                font_rec = ui_theme.get_retro_font("stencil", 22, bold=True)
                ui_theme.draw_retro_text(screen, "★ ALL-TIME HIGH SCORE RECORD BROKEN! ★", 
                                        font_rec, ui_theme.COLOR_RADAR_GREEN, WINDOW_WIDTH // 2, 155)

        # Evaluation Rank Banner
        font_rnk = ui_theme.get_retro_font("stencil", 30, bold=True)
        ui_theme.draw_retro_text(screen, rank_title, font_rnk, rank_color, WINDOW_WIDTH // 2, 195)
        
        font_rnk_sub = ui_theme.get_retro_font("digital", 15, bold=False)
        ui_theme.draw_retro_text(screen, rank_badge, font_rnk_sub, ui_theme.COLOR_TEXT_DIM, WINDOW_WIDTH // 2, 225)

        # Stat Boxes (Kills, Combat Score, Record)
        # 1. Kills Box
        k_rect = pygame.Rect(WINDOW_WIDTH // 2 - 340, 260, 210, 110)
        ui_theme.draw_military_panel(screen, k_rect, bg_color=(12, 16, 14), border_color=ui_theme.COLOR_STEEL, rivets=False)
        font_stat_lbl = ui_theme.get_retro_font("digital", 13, bold=True)
        font_stat_val = ui_theme.get_retro_font("digital", 32, bold=True)
        ui_theme.draw_retro_text(screen, "AIR TARGETS DOWN", font_stat_lbl, ui_theme.COLOR_KHAKI, k_rect.centerx, k_rect.top + 26)
        ui_theme.draw_retro_text(screen, f"{score:03d}", font_stat_val, ui_theme.COLOR_AMBER_BRIGHT, k_rect.centerx, k_rect.top + 68)

        # 2. Total Combat Score Box
        s_rect = pygame.Rect(WINDOW_WIDTH // 2 - 105, 260, 210, 110)
        ui_theme.draw_military_panel(screen, s_rect, bg_color=(12, 16, 14), border_color=ui_theme.COLOR_STEEL, rivets=False)
        ui_theme.draw_retro_text(screen, "COMBAT SCORE", font_stat_lbl, ui_theme.COLOR_KHAKI, s_rect.centerx, s_rect.top + 26)
        ui_theme.draw_retro_text(screen, f"{score * 100:07d}", font_stat_val, ui_theme.COLOR_AMBER_BRIGHT, s_rect.centerx, s_rect.top + 68)

        # 3. High Record Box
        h_rect = pygame.Rect(WINDOW_WIDTH // 2 + 130, 260, 210, 110)
        ui_theme.draw_military_panel(screen, h_rect, bg_color=(12, 16, 14), border_color=ui_theme.COLOR_STEEL, rivets=False)
        ui_theme.draw_retro_text(screen, "ALL-TIME RECORD", font_stat_lbl, ui_theme.COLOR_KHAKI, h_rect.centerx, h_rect.top + 26)
        ui_theme.draw_retro_text(screen, f"{high_score * 100:07d}", font_stat_val, ui_theme.COLOR_RADAR_GREEN, h_rect.centerx, h_rect.top + 68)

        # Debrief Statement
        font_msg = ui_theme.get_retro_font("digital", 15, bold=False)
        ui_theme.draw_retro_text(screen, "MISSION SUMMARY: AIR DEFENSE OPERATIONS COMPLETED FOR DESIGNATED WINDOW.", 
                                font_msg, ui_theme.COLOR_TEXT_DIM, WINDOW_WIDTH // 2, 415)
        ui_theme.draw_retro_text(screen, "BASE COMMAND HAS COMMENDED YOUR CANNON ACCURACY AND DEFENSE PERFORMANCE.", 
                                font_msg, ui_theme.COLOR_TEXT_DIM, WINDOW_WIDTH // 2, 442)

        # Buttons
        btn_replay.update((px, py))
        btn_menu.update((px, py))
        btn_replay.draw(screen)
        btn_menu.draw(screen)
        
        crosshair_fx.update(dt, btn_replay.hover or btn_menu.hover)
        crosshair_fx.draw(screen, px, py)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "EXIT"
            if event.type == pygame.MOUSEBUTTONDOWN:
                now = time.time()
                if now - last_click_time > CLICK_DELAY:
                    gun_sound.play()
                    crosshair_fx.trigger_shot()
                    last_click_time = now
                    if btn_replay.hover:
                        pygame.mixer.music.play(-1)
                        return "REPLAY"
                    if btn_menu.hover:
                        return "MENU"
        
        pygame.display.flip()

# ---------------- MAIN APPLICATION ENTRY POINT ----------------
if __name__ == "__main__":
    while True:
        current_mode = menu()
        if current_mode == "EXIT":
            break
        
        if not select_background():
            continue

        chosen_plane_frames = select_plane()
        if chosen_plane_frames is None:
            continue

        active_game = True
        while active_game:
            score = play_game(current_mode, chosen_plane_frames)
            
            if score is None:
                active_game = False
                break
            elif score == "RESTART":
                continue
            elif score == "MENU":
                active_game = False
                break
                
            result = game_over(score, current_mode)
            
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