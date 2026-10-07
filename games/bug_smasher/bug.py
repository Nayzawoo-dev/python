import pygame
import cv2
import mediapipe as mp
import random
import time
import sys
import os
import math
from PIL import Image

# ─────────────────────────────────────────────
#  Path Fix — run from game folder
# ─────────────────────────────────────────────
try:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
except Exception:
    pass

# ─────────────────────────────────────────────
#  Helper: Extract frames from an animated GIF
# ─────────────────────────────────────────────
def load_gif_frames(path, size=None):
    """Return a list of pygame Surfaces, one per GIF frame."""
    frames = []
    if not os.path.exists(path):
        print(f"[WARN] GIF not found: {path}")
        return frames
    try:
        gif = Image.open(path)
        for i in range(gif.n_frames):
            gif.seek(i)
            frame = gif.convert("RGBA")
            if size:
                frame = frame.resize(size, Image.LANCZOS)
            surf = pygame.image.fromstring(frame.tobytes(), frame.size, "RGBA")
            frames.append(surf.convert_alpha())
    except Exception as e:
        print(f"[ERR] load_gif_frames({path}): {e}")
    return frames

def load_gif_frames_cropped(path, size=None):
    """Load GIF frames auto-cropped to the tightest bounding box across ALL frames.
    This removes transparent padding so the sprite fills its display area."""
    frames = []
    if not os.path.exists(path):
        print(f"[WARN] GIF not found: {path}")
        return frames
    try:
        gif = Image.open(path)
        n = gif.n_frames
        W, H = gif.size

        # ── Pass 1: find the global content bounding box ──────────────────
        gx0, gy0, gx1, gy1 = W, H, 0, 0
        for i in range(n):
            gif.seek(i)
            bb = gif.convert("RGBA").getbbox()
            if bb:
                gx0 = min(gx0, bb[0])
                gy0 = min(gy0, bb[1])
                gx1 = max(gx1, bb[2])
                gy1 = max(gy1, bb[3])
        crop_box = (gx0, gy0, gx1, gy1)
        cw, ch = gx1 - gx0, gy1 - gy0
        print(f"[INFO] {os.path.basename(path)} content: {cw}x{ch} (cropped from {W}x{H})")

        # ── Pass 2: crop each frame to the box, then scale ────────────────
        for i in range(n):
            gif.seek(i)
            frame = gif.convert("RGBA").crop(crop_box)
            if size:
                frame = frame.resize(size, Image.LANCZOS)
            surf = pygame.image.fromstring(frame.tobytes(), frame.size, "RGBA")
            frames.append(surf.convert_alpha())
    except Exception as e:
        print(f"[ERR] load_gif_frames_cropped({path}): {e}")
    return frames

# ─────────────────────────────────────────────
#  Pygame Init
# ─────────────────────────────────────────────
pygame.mixer.pre_init(48000, -16, 2, 2048)
pygame.init()

WIDTH, HEIGHT = 900, 650
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("🪳 Bug Smasher")
clock = pygame.time.Clock()

# ─────────────────────────────────────────────
#  Constants
# ─────────────────────────────────────────────
BUG_SIZE       = 110      # cockroach sprite height
COCKROACH_W    = 90       # display width  (content is ~393x623, ratio ≈0.63)
COCKROACH_H    = 130      # display height — larger so legs are clearly visible
SLAP_SIZE      = 180      # slap animation size
HAND_SIZE      = 90       # hand cursor size
COCKROACH_SPD  = 2        # game-frames per cockroach GIF frame (lower = faster walk)
SLAP_SPD       = 1        # game-frames per slap GIF frame  (lower = faster slap)
MAX_SLAPS      = 1        # max concurrent slap animations on screen
HOVER_LIMIT    = 1.5      # seconds to hold for button activation
HIT_RADIUS     = 65       # pixel radius for hit detection

# ─────────────────────────────────────────────
#  Load Assets
# ─────────────────────────────────────────────

# Background
bg_image = None
try:
    if os.path.exists("bugback.jpg"):
        raw = pygame.image.load("bugback.jpg")
        bg_image = pygame.transform.scale(raw, (WIDTH, HEIGHT))
except Exception as e:
    print(f"[WARN] bg: {e}")

# Cockroach walk GIF → crop to content bbox first, then scale to display size
# (raw GIF is 440x659 but content is only 393x623; cropping removes transparent padding
#  so the cockroach fills the sprite area instead of appearing tiny/sparse)
cockroach_frames = load_gif_frames_cropped(
    "cockroach_walk_transparent.gif", size=(COCKROACH_W, COCKROACH_H)
)
# Pre-build flipped versions so we don't recreate surfaces every draw call
cockroach_frames_flipped = [pygame.transform.flip(f, True, False) for f in cockroach_frames]
print(f"[INFO] cockroach display size: {COCKROACH_W}x{COCKROACH_H}, frames: {len(cockroach_frames)}")

# Hand-slap-bug GIF  → list of frames (shown at hit location)
slap_frames = load_gif_frames("hand_slap_bug.gif", size=(SLAP_SIZE, SLAP_SIZE))
print(f"[INFO] slap frames: {len(slap_frames)}")

# Hand cursor PNG
hand_cursor = None
try:
    if os.path.exists("hand_slap_only.png"):
        raw = pygame.image.load("hand_slap_only.png").convert_alpha()
        hand_cursor = pygame.transform.scale(raw, (HAND_SIZE, HAND_SIZE))
except Exception as e:
    print(f"[WARN] hand cursor: {e}")

# Fallback bug sprite (bug.png) if no GIF
bug_img_base = None
if not cockroach_frames:
    try:
        if os.path.exists("bug.png"):
            raw = pygame.image.load("bug.png")
            bug_img_base = pygame.transform.scale(raw, (BUG_SIZE, BUG_SIZE))
    except Exception:
        pass

# Music & SFX
smash_sound = None
rank_sounds = {"normal": None, "good": None, "excellent": None}
try:
    if os.path.exists("background_music.mp3"):
        pygame.mixer.music.load("background_music.mp3")
        pygame.mixer.music.set_volume(0.3)
        pygame.mixer.music.play(-1)
    if os.path.exists("slice.wav"):
        smash_sound = pygame.mixer.Sound("slice.wav")
    for key in rank_sounds:
        fname = f"{key}.mp3"
        if os.path.exists(fname):
            rank_sounds[key] = pygame.mixer.Sound(fname)
except Exception as e:
    print(f"[WARN] audio: {e}")

# ─────────────────────────────────────────────
#  Fonts
# ─────────────────────────────────────────────
font_xl = pygame.font.SysFont("Arial", 72, bold=True)
font_lg = pygame.font.SysFont("Arial", 48, bold=True)
font_md = pygame.font.SysFont("Arial", 32, bold=True)
font_sm = pygame.font.SysFont("Arial", 22)

# ─────────────────────────────────────────────
#  MediaPipe Hand Tracking
# ─────────────────────────────────────────────
mp_hands = mp.solutions.hands
hand_tracker = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)
cap = cv2.VideoCapture(0)

# ─────────────────────────────────────────────
#  Bug Class (with per-instance GIF frame state)
# ─────────────────────────────────────────────
class Bug:
    def __init__(self, can_be_smashed=True):
        self.can_be_smashed = can_be_smashed
        # stagger start frame so bugs aren't in sync
        self.gif_frame  = random.randint(0, max(0, len(cockroach_frames) - 1))
        self.gif_timer  = 0
        self.reset()

    def reset(self):
        self.x     = random.randint(120, WIDTH  - 120)
        self.y     = random.randint(120, HEIGHT - 120)
        speed      = random.choice([5, 6, 7, 8])
        self.vel_x = random.choice([-1, 1]) * speed
        self.vel_y = random.choice([-1, 1]) * speed

    def update(self):
        self.x += self.vel_x
        self.y += self.vel_y
        if self.x <= 55  or self.x >= WIDTH  - 55:  self.vel_x *= -1
        if self.y <= 55  or self.y >= HEIGHT - 55:  self.vel_y *= -1
        # advance GIF frame
        if cockroach_frames:
            self.gif_timer += 1
            if self.gif_timer >= COCKROACH_SPD:
                self.gif_timer = 0
                self.gif_frame = (self.gif_frame + 1) % len(cockroach_frames)

    def draw(self, surface):
        if cockroach_frames:
            # Use pre-flipped cache: left = flip, right = normal
            if self.vel_x < 0:
                frame = cockroach_frames_flipped[self.gif_frame]
            else:
                frame = cockroach_frames[self.gif_frame]
            rect = frame.get_rect(center=(int(self.x), int(self.y)))
            surface.blit(frame, rect.topleft)
        elif bug_img_base:
            angle   = math.degrees(math.atan2(-self.vel_y, self.vel_x)) - 90
            rotated = pygame.transform.rotate(bug_img_base, angle)
            rect    = rotated.get_rect(center=(int(self.x), int(self.y)))
            surface.blit(rotated, rect.topleft)
        else:
            pygame.draw.circle(surface, (100, 60, 10), (int(self.x), int(self.y)), 40)

# ─────────────────────────────────────────────
#  Active Slap-Effect manager
#  Each entry: {x, y, frame, timer}
# ─────────────────────────────────────────────
slap_effects = []

def spawn_slap(x, y):
    """Show slap animation at (x, y). Caps at MAX_SLAPS — clears old ones first."""
    if slap_frames:
        # Remove oldest effects when at cap so hands don't pile up
        while len(slap_effects) >= MAX_SLAPS:
            slap_effects.pop(0)
        slap_effects.append({"x": x, "y": y, "frame": 0, "timer": 0})

def update_draw_slaps(surface):
    done = []
    for e in slap_effects:
        if e["frame"] < len(slap_frames):
            surf = slap_frames[e["frame"]]
            rect = surf.get_rect(center=(e["x"], e["y"]))
            surface.blit(surf, rect.topleft)
            e["timer"] += 1
            if e["timer"] >= SLAP_SPD:
                e["timer"] = 0
                e["frame"] += 1
        else:
            done.append(e)
    for d in done:
        slap_effects.remove(d)

# ─────────────────────────────────────────────
#  UI Helpers
# ─────────────────────────────────────────────
def draw_text_shadow(text, font, color, x, y, center=False):
    shadow = font.render(text, True, (0, 0, 0))
    main   = font.render(text, True, color)
    if center:
        sr = shadow.get_rect(center=(x + 3, y + 3))
        mr = main.get_rect(center=(x, y))
    else:
        sr = (x + 3, y + 3)
        mr = (x, y)
    screen.blit(shadow, sr)
    screen.blit(main,   mr)

def draw_panel(rect, color=(20, 20, 20), alpha=180, radius=16):
    surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(surf, (*color, alpha), surf.get_rect(), border_radius=radius)
    screen.blit(surf, rect.topleft)
    pygame.draw.rect(screen, (255, 255, 255, 160), rect, 2, border_radius=radius)

def draw_button(rect, label, font, idle_col, hot_col, hovered,
                progress=0.0):
    """Rounded button with drop-shadow, border, and hover-progress bar."""
    col = hot_col if hovered else idle_col
    # drop shadow
    shadow = pygame.Rect(rect.x + 5, rect.y + 5, rect.width, rect.height)
    pygame.draw.rect(screen, (0, 0, 0, 120), shadow, border_radius=14)
    # body
    pygame.draw.rect(screen, col, rect, border_radius=14)
    # white border
    pygame.draw.rect(screen, (255, 255, 255), rect, 2, border_radius=14)
    # label
    draw_text_shadow(label, font, (255, 255, 255), rect.centerx, rect.centery, center=True)
    # fill-bar underneath button when hovering
    if hovered and progress > 0:
        bar_w  = int(rect.width * min(progress / HOVER_LIMIT, 1.0))
        bar_bg = pygame.Rect(rect.x, rect.bottom + 6, rect.width, 7)
        bar_fg = pygame.Rect(rect.x, rect.bottom + 6, bar_w,       7)
        pygame.draw.rect(screen, (80, 80, 80),   bar_bg, border_radius=4)
        pygame.draw.rect(screen, (255, 230, 30), bar_fg, border_radius=4)

def draw_hand(x, y):
    """Draw hand cursor (PNG) centred on fingertip, fall back to circle."""
    if hand_cursor and x > 0:
        rect = hand_cursor.get_rect(center=(x, y))
        screen.blit(hand_cursor, rect.topleft)
    elif x > 0:
        pygame.draw.circle(screen, (0, 255, 100), (x, y), 14)
        pygame.draw.circle(screen, (255, 255, 255), (x, y), 14, 3)

# ─────────────────────────────────────────────
#  Game State
# ─────────────────────────────────────────────
home_bugs = [Bug(can_be_smashed=False) for _ in range(8)]
play_bugs = [Bug(can_be_smashed=True)  for _ in range(7)]

game_state      = "HOME"
score           = 0
game_duration   = 60
hover_start     = 0.0
is_hovering     = False
sound_played    = False
start_ticks     = 0

# ─────────────────────────────────────────────
#  Main Loop
# ─────────────────────────────────────────────
running = True
while running:
    # ── webcam frame ──────────────────────────
    ok, frame = cap.read()
    if not ok:
        break
    frame     = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results   = hand_tracker.process(rgb_frame)

    hand_x, hand_y = -200, -200
    if results.multi_hand_landmarks:
        lm     = results.multi_hand_landmarks[0].landmark[8]   # index fingertip
        hand_x = int(lm.x * WIDTH)
        hand_y = int(lm.y * HEIGHT)

    # ── background ────────────────────────────
    if bg_image:
        screen.blit(bg_image, (0, 0))
    else:
        screen.fill((30, 25, 20))

    # ── events ────────────────────────────────
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # ══════════════════════════════════════════
    #  STATE: HOME
    # ══════════════════════════════════════════
    if game_state == "HOME":
        now = pygame.time.get_ticks()

        # ── dim the wooden background ─────────
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 115))
        screen.blit(dim, (0, 0))

        # ── cockroaches scurrying in background
        for b in home_bugs:
            b.update()
            b.draw(screen)

        # ── central menu card ─────────────────
        CARD_W, CARD_H = 550, 500
        card = pygame.Rect(WIDTH  // 2 - CARD_W // 2,
                           HEIGHT // 2 - CARD_H // 2 - 10,
                           CARD_W, CARD_H)
        draw_panel(card, (8, 6, 4), alpha=228, radius=24)

        # ── animated pulsing title ────────────
        pulse   = 1.0 + 0.035 * math.sin(now * 0.003)
        t_raw   = font_lg.render("🪳  BUG SMASHER  🪳", True, (255, 215, 40))
        ts_raw  = font_lg.render("🪳  BUG SMASHER  🪳", True, (60, 38, 0))
        tw = int(t_raw.get_width()  * pulse)
        th = int(t_raw.get_height() * pulse)
        tw, th = max(tw, 1), max(th, 1)
        t_surf  = pygame.transform.smoothscale(t_raw,  (tw, th))
        ts_surf = pygame.transform.smoothscale(ts_raw, (tw, th))
        tx = WIDTH // 2 - tw // 2
        ty = card.top + 22
        screen.blit(ts_surf, (tx + 3, ty + 3))
        screen.blit(t_surf,  (tx, ty))

        # ── tagline ───────────────────────────
        draw_text_shadow("Use your hand to smash cockroaches!",
                         font_sm, (185, 170, 125),
                         WIDTH // 2, card.top + 94, center=True)

        # ── section divider ───────────────────
        pygame.draw.line(screen, (85, 68, 48),
                         (card.x + 45, card.top + 116),
                         (card.right - 45, card.top + 116), 1)

        # ── HOW TO PLAY ───────────────────────
        draw_text_shadow("HOW TO PLAY", font_sm, (255, 195, 55),
                         WIDTH // 2, card.top + 134, center=True)
        tips = [
            "👆  Point your index finger at the camera",
            "🪳  Move your finger to touch a cockroach",
            "⏱  60 seconds — smash as many as you can!",
        ]
        for i, tip in enumerate(tips):
            draw_text_shadow(tip, font_sm, (195, 188, 172),
                             WIDTH // 2, card.top + 160 + i * 25, center=True)

        # ── rank divider ──────────────────────
        pygame.draw.line(screen, (85, 68, 48),
                         (card.x + 45, card.top + 246),
                         (card.right - 45, card.top + 246), 1)

        # ── RANK GUIDE ────────────────────────
        draw_text_shadow("RANK GUIDE", font_sm, (255, 195, 55),
                         WIDTH // 2, card.top + 263, center=True)

        rank_data = [
            ("✨  EXCELLENT", "50 + bugs", (35, 215, 85)),
            ("👍  GOOD",      "30 + bugs", (85, 155, 255)),
            ("🐛  NORMAL",   "< 30 bugs", (165, 158, 148)),
        ]
        for i, (rank_lbl, req_lbl, col) in enumerate(rank_data):
            ry = card.top + 287 + i * 22
            # left-aligned rank name, right-aligned requirement
            draw_text_shadow(rank_lbl, font_sm, col,
                             WIDTH // 2 - 130, ry)
            draw_text_shadow(req_lbl, font_sm, (155, 148, 135),
                             WIDTH // 2 + 60,  ry)

        # ── button divider ────────────────────
        pygame.draw.line(screen, (85, 68, 48),
                         (card.x + 45, card.top + 355),
                         (card.right - 45, card.top + 355), 1)

        # ── blinking hint ─────────────────────
        if (now // 550) % 2 == 0:
            draw_text_shadow("☝  Hold finger over a button to select",
                             font_sm, (215, 205, 100),
                             WIDTH // 2, card.top + 373, center=True)

        # ── PLAY button (large) ───────────────
        play_rect = pygame.Rect(WIDTH // 2 - 125, card.top + 397, 250, 64)
        # ── EXIT button (smaller, bottom) ─────
        exit_rect = pygame.Rect(WIDTH // 2 - 80,  card.top + 471, 160, 38)

        play_hov = play_rect.collidepoint(hand_x, hand_y)
        exit_hov = exit_rect.collidepoint(hand_x, hand_y)

        if play_hov:
            if not is_hovering:
                is_hovering, hover_start = True, time.time()
            dur = time.time() - hover_start
            if dur >= HOVER_LIMIT:
                game_state, score = "PLAY", 0
                is_hovering, sound_played = False, False
                slap_effects.clear()
                start_ticks = pygame.time.get_ticks()
            draw_button(play_rect, "▶   PLAY", font_md,
                        (0, 145, 0), (0, 210, 55), True, dur)
        elif exit_hov:
            if not is_hovering:
                is_hovering, hover_start = True, time.time()
            dur = time.time() - hover_start
            if dur >= HOVER_LIMIT:
                running = False
            draw_button(exit_rect, "✕  EXIT", font_sm,
                        (130, 0, 0), (200, 35, 35), True, dur)
        else:
            is_hovering = False
            draw_button(play_rect, "▶   PLAY", font_md,
                        (0, 145, 0), (0, 210, 55), False)
            draw_button(exit_rect, "✕  EXIT", font_sm,
                        (130, 0, 0), (200, 35, 35), False)

    # ══════════════════════════════════════════
    #  STATE: PLAY
    # ══════════════════════════════════════════
    elif game_state == "PLAY":
        rem = max(0, game_duration - (pygame.time.get_ticks() - start_ticks) // 1000)

        for b in play_bugs:
            b.update()
            b.draw(screen)
            dist = ((hand_x - b.x) ** 2 + (hand_y - b.y) ** 2) ** 0.5
            if dist < HIT_RADIUS:
                score += 1
                if smash_sound:
                    smash_sound.play()
                spawn_slap(int(b.x), int(b.y))
                b.reset()

        # draw slap animations on top of bugs
        update_draw_slaps(screen)

        # ── HUD ──────────────────────────────
        # timer (top-left)
        t_panel = pygame.Rect(12, 12, 160, 50)
        draw_panel(t_panel, (140, 20, 20), alpha=210)
        draw_text_shadow(f"⏱  {rem}s", font_md,
                         (255, 100, 100), t_panel.centerx, t_panel.centery, center=True)

        # score (top-right)
        s_panel = pygame.Rect(WIDTH - 225, 12, 212, 50)
        draw_panel(s_panel, (10, 70, 150), alpha=210)
        draw_text_shadow(f"🪳  {score}", font_md,
                         (120, 200, 255), s_panel.centerx, s_panel.centery, center=True)

        if rem <= 0:
            game_state = "RESULT"
            pygame.mixer.music.stop()

    # ══════════════════════════════════════════
    #  STATE: RESULT
    # ══════════════════════════════════════════
    elif game_state == "RESULT":
        # dim the whole screen
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 155))
        screen.blit(dim, (0, 0))

        # result card
        card = pygame.Rect(WIDTH // 2 - 280, HEIGHT // 2 - 215, 560, 430)
        draw_panel(card, (15, 15, 15), alpha=230, radius=20)

        # GAME OVER title
        draw_text_shadow("GAME OVER", font_lg, (255, 70, 70),
                         WIDTH // 2, HEIGHT // 2 - 170, center=True)

        # rank
        if score >= 50:
            rank_key, rank_txt, rank_col = "excellent", "✨ EXCELLENT!", (30, 220, 80)
        elif score >= 30:
            rank_key, rank_txt, rank_col = "good",      "👍 GOOD!",      (80, 150, 255)
        else:
            rank_key, rank_txt, rank_col = "normal",    "🐛 NORMAL",     (180, 180, 180)

        if not sound_played:
            if rank_sounds[rank_key]:
                rank_sounds[rank_key].play()
            sound_played = True

        draw_text_shadow(f"Bugs Smashed: {score}", font_md, (255, 255, 255),
                         WIDTH // 2, HEIGHT // 2 - 100, center=True)
        draw_text_shadow(rank_txt, font_lg, rank_col,
                         WIDTH // 2, HEIGHT // 2 - 45, center=True)

        # buttons
        retry_rect = pygame.Rect(WIDTH // 2 - 120, HEIGHT // 2 + 45,  240, 68)
        exit_rect2 = pygame.Rect(WIDTH // 2 - 120, HEIGHT // 2 + 135, 240, 68)

        retry_hov = retry_rect.collidepoint(hand_x, hand_y)
        exit_hov2 = exit_rect2.collidepoint(hand_x, hand_y)

        if retry_hov:
            if not is_hovering:
                is_hovering, hover_start = True, time.time()
            dur = time.time() - hover_start
            if dur >= HOVER_LIMIT:
                game_state, score = "PLAY", 0
                is_hovering, sound_played = False, False
                slap_effects.clear()
                pygame.mixer.music.play(-1)
                start_ticks = pygame.time.get_ticks()
            draw_button(retry_rect, "↺  RETRY", font_md,
                        (0, 140, 0), (0, 205, 55), True, dur)
        elif exit_hov2:
            if not is_hovering:
                is_hovering, hover_start = True, time.time()
            dur = time.time() - hover_start
            if dur >= HOVER_LIMIT:
                running = False
            draw_button(exit_rect2, "✕  EXIT", font_md,
                        (160, 0, 0), (220, 45, 45), True, dur)
        else:
            is_hovering = False
            draw_button(retry_rect, "↺  RETRY", font_md,
                        (0, 140, 0), (0, 205, 55), False)
            draw_button(exit_rect2, "✕  EXIT", font_md,
                        (160, 0, 0), (220, 45, 45), False)

    # ── hand cursor (always on top) ───────────
    draw_hand(hand_x, hand_y)

    pygame.display.flip()
    clock.tick(30)

# ─────────────────────────────────────────────
#  Cleanup
# ─────────────────────────────────────────────
cap.release()
pygame.quit()
sys.exit()
