import pygame
import math
import random
import json
import os
import time

# ==============================================================================
# 90s RETRO MILITARY ARCADE PALETTE
# Authentic Windows 95/98 PC & arcade cabinet helicopter combat palette:
# Olive Drab, Gunmetal Steel, Phosphor Amber, Radar Green, Alert Red, Khaki
# ==============================================================================
COLOR_BLACK = (10, 12, 10)
COLOR_GUNMETAL_DARK = (16, 20, 18)
COLOR_GUNMETAL = (28, 34, 32)
COLOR_STEEL = (50, 60, 58)
COLOR_STEEL_LIGHT = (95, 110, 105)
COLOR_STEEL_BRIGHT = (160, 180, 175)

COLOR_OLIVE_DARK = (24, 32, 20)
COLOR_OLIVE_DRAB = (45, 62, 35)
COLOR_OLIVE_MID = (70, 95, 52)
COLOR_OLIVE_LIGHT = (115, 150, 85)
COLOR_KHAKI = (180, 170, 125)
COLOR_KHAKI_BRIGHT = (230, 220, 175)

COLOR_AMBER = (255, 175, 15)
COLOR_AMBER_BRIGHT = (255, 215, 50)
COLOR_AMBER_DIM = (140, 95, 10)

COLOR_RADAR_GREEN = (35, 235, 85)
COLOR_RADAR_GREEN_DIM = (15, 110, 40)
COLOR_RADAR_BG = (8, 26, 14)

COLOR_ALERT_RED = (235, 40, 40)
COLOR_ALERT_RED_BRIGHT = (255, 90, 90)
COLOR_ALERT_RED_DIM = (120, 20, 20)

COLOR_HAZARD_YELLOW = (250, 210, 25)
COLOR_HAZARD_BLACK = (20, 20, 20)

COLOR_WHITE = (240, 245, 240)
COLOR_TEXT_DIM = (150, 165, 155)

# Button Color Schemes
BTN_OLIVE = {
    "face": COLOR_OLIVE_DRAB,
    "top_edge": COLOR_OLIVE_LIGHT,
    "bottom_edge": COLOR_OLIVE_DARK,
    "text": COLOR_KHAKI_BRIGHT,
    "hover_face": COLOR_OLIVE_MID,
    "hover_edge": COLOR_AMBER_BRIGHT,
    "hover_text": COLOR_WHITE,
    "accent": COLOR_AMBER
}

BTN_AMBER = {
    "face": (85, 60, 15),
    "top_edge": COLOR_AMBER,
    "bottom_edge": (45, 30, 8),
    "text": COLOR_AMBER_BRIGHT,
    "hover_face": (120, 85, 20),
    "hover_edge": COLOR_AMBER_BRIGHT,
    "hover_text": COLOR_WHITE,
    "accent": COLOR_AMBER_BRIGHT
}

BTN_RED = {
    "face": (75, 22, 22),
    "top_edge": COLOR_ALERT_RED,
    "bottom_edge": (38, 10, 10),
    "text": (255, 170, 170),
    "hover_face": (110, 30, 30),
    "hover_edge": COLOR_ALERT_RED_BRIGHT,
    "hover_text": COLOR_WHITE,
    "accent": COLOR_ALERT_RED_BRIGHT
}

BTN_STEEL = {
    "face": COLOR_STEEL,
    "top_edge": COLOR_STEEL_LIGHT,
    "bottom_edge": COLOR_GUNMETAL_DARK,
    "text": COLOR_STEEL_BRIGHT,
    "hover_face": (65, 78, 75),
    "hover_edge": COLOR_AMBER,
    "hover_text": COLOR_WHITE,
    "accent": COLOR_AMBER
}

BTN_RADAR = {
    "face": (15, 60, 25),
    "top_edge": COLOR_RADAR_GREEN,
    "bottom_edge": (8, 30, 12),
    "text": COLOR_RADAR_GREEN,
    "hover_face": (25, 90, 40),
    "hover_edge": (120, 255, 160),
    "hover_text": COLOR_WHITE,
    "accent": COLOR_RADAR_GREEN
}

# ==============================================================================
# SECTOR & TARGET HELICOPTER RETRO CLASSIFIED DATA
# ==============================================================================
SECTORS = [
    {
        "code": "SECTOR ALPHA",
        "name": "COASTAL DEFENSE",
        "grid": "GRID 45-N / 12-E",
        "threat": "MODERATE",
        "desc": "Maritime surveillance border. Intercept low-flying hostile rotorcraft."
    },
    {
        "code": "SECTOR BRAVO",
        "name": "HIGHLAND VALLEY",
        "grid": "GRID 38-N / 24-E",
        "threat": "HIGH THREAT",
        "desc": "Narrow canyon corridor with severe mountain radar interference."
    },
    {
        "code": "SECTOR CHARLIE",
        "name": "DESERT FORTRESS",
        "grid": "GRID 29-N / 47-E",
        "threat": "CRITICAL",
        "desc": "High-temperature combat zone. Extreme concentration of attack choppers."
    }
]

HELICOPTER_PROFILES = [
    {
        "design": "DESIGN 01",
        "name": "KA-50 BLACK HOKUM",
        "role": "HEAVY ATTACK GUNSHIP",
        "threat": "CLASS IV",
        "stats": "SPEED: HIGH // ARMOR: HEAVY"
    },
    {
        "design": "DESIGN 02",
        "name": "MI-24 COMBAT HIND",
        "role": "ASSAULT TANK CHOPPER",
        "threat": "CLASS V",
        "stats": "SPEED: MODERATE // ARMOR: MAXIMUM"
    },
    {
        "design": "DESIGN 03",
        "name": "AH-64 APACHE LONGBOW",
        "role": "PRECISION RADAR HUNTER",
        "threat": "CLASS IV",
        "stats": "SPEED: HIGH // ARMOR: REINFORCED"
    },
    {
        "design": "DESIGN 04",
        "name": "RAH-66 STEALTH COMANCHE",
        "role": "RADAR-EVADING SCOUT",
        "threat": "CLASS III",
        "stats": "SPEED: EXTREME // ARMOR: COMPOSITE"
    },
    {
        "design": "DESIGN 05",
        "name": "EUROCOPTER TIGER",
        "role": "HIGH-AGILITY INTERCEPTOR",
        "threat": "CLASS IV",
        "stats": "SPEED: RAPID // ARMOR: BALANCED"
    }
]

# ==============================================================================
# HIGH SCORE STORAGE
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HIGH_SCORE_FILE = os.path.join(BASE_DIR, "highscore.json")

def load_high_score():
    try:
        if os.path.exists(HIGH_SCORE_FILE):
            with open(HIGH_SCORE_FILE, "r") as f:
                data = json.load(f)
                return int(data.get("high_score", 0))
    except Exception:
        pass
    return 0

def save_high_score(score):
    try:
        current = load_high_score()
        if score > current:
            with open(HIGH_SCORE_FILE, "w") as f:
                json.dump({"high_score": int(score)}, f)
            return True, score
        return False, current
    except Exception:
        return False, score

# ==============================================================================
# FONT CACHE & GENERATOR
# ==============================================================================
_FONT_CACHE = {}

def get_retro_font(category="stencil", size=32, bold=True):
    """
    Returns authentic 90s system fonts with guaranteed fallbacks.
    category options: 'stencil', 'arcade', 'digital', 'body'
    """
    key = (category, size, bold)
    if key not in _FONT_CACHE:
        chosen = None
        if category == "stencil":
            font_candidates = ["stencil", "impact", "arialblack", "consolas"]
        elif category == "arcade":
            font_candidates = ["impact", "arialblack", "lucidaconsole", "consolas"]
        elif category == "digital":
            font_candidates = ["ocraextended", "lucidaconsole", "consolas", "couriernew"]
        else: # body
            font_candidates = ["lucidaconsole", "consolas", "verdana", "arial"]

        for name in font_candidates:
            try:
                chosen = pygame.font.SysFont(name, size, bold=bold)
                if chosen:
                    break
            except Exception:
                continue

        if chosen is None:
            chosen = pygame.font.Font(None, size)
        _FONT_CACHE[key] = chosen
    return _FONT_CACHE[key]

# ==============================================================================
# RETRO TEXT DRAWING WITH SHADOW & OUTLINE
# ==============================================================================
def draw_retro_text(surface, text, font, color, x, y, 
                    shadow_color=(0, 0, 0), shadow_offset=(2, 2), 
                    outline_color=None, outline_width=0, center=True):
    """
    Renders punchy retro text with arcade drop-shadow and optional outline.
    """
    # 1. Shadow
    if shadow_offset and shadow_color:
        s_surf = font.render(text, True, shadow_color)
        s_rect = s_surf.get_rect()
        if center:
            s_rect.center = (x + shadow_offset[0], y + shadow_offset[1])
        else:
            s_rect.topleft = (x + shadow_offset[0], y + shadow_offset[1])
        surface.blit(s_surf, s_rect)

    # 2. Outline if requested
    if outline_width > 0 and outline_color:
        o_surf = font.render(text, True, outline_color)
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx == 0 and dy == 0:
                    continue
                o_rect = o_surf.get_rect()
                if center:
                    o_rect.center = (x + dx, y + dy)
                else:
                    o_rect.topleft = (x + dx, y + dy)
                surface.blit(o_surf, o_rect)

    # 3. Main Text
    surf = font.render(text, True, color)
    rect = surf.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(surf, rect)
    return rect

# ==============================================================================
# MILITARY BEVELED PANELS & HARDWARE DETAILS
# ==============================================================================
def draw_rivet(surface, x, y, radius=4):
    """ Draws a small 3D metallic rivet screw on military hardware panels """
    pygame.draw.circle(surface, (15, 18, 16), (x, y), radius)
    pygame.draw.circle(surface, (120, 135, 130), (x - 1, y - 1), radius - 1)
    pygame.draw.circle(surface, (60, 72, 70), (x, y), radius - 1)
    pygame.draw.circle(surface, (25, 30, 28), (x, y), 1)

def draw_hazard_stripes(surface, rect, stripe_w=12, angle_tilt=True):
    """ Draws classic yellow/black military warning hazard stripes """
    clip = surface.get_clip()
    surface.set_clip(rect)
    w, h = rect.width, rect.height
    surface.fill(COLOR_HAZARD_YELLOW, rect)
    
    # Draw diagonal black slashes
    for x in range(rect.left - h, rect.right + h, stripe_w * 2):
        points = [
            (x, rect.bottom),
            (x + stripe_w, rect.bottom),
            (x + stripe_w + h, rect.top),
            (x + h, rect.top)
        ]
        pygame.draw.polygon(surface, COLOR_HAZARD_BLACK, points)
    surface.set_clip(clip)

def draw_military_panel(surface, rect, title="", subtitle="",
                        bg_color=COLOR_GUNMETAL_DARK, 
                        border_color=COLOR_OLIVE_MID,
                        hazard_header=False,
                        rivets=True,
                        chamfer=8):
    """
    Renders a 1990s military console panel with beveled edges, chamfered corners,
    corner rivets, and authentic tactical stencil header styling.
    """
    x, y, w, h = rect.x, rect.y, rect.width, rect.height

    # Chamfered Polygon Corners for authentic military terminal look
    pts = [
        (x + chamfer, y),
        (x + w - chamfer, y),
        (x + w, y + chamfer),
        (x + w, y + h - chamfer),
        (x + w - chamfer, y + h),
        (x + chamfer, y + h),
        (x, y + h - chamfer),
        (x, y + chamfer)
    ]

    # Panel Body
    pygame.draw.polygon(surface, bg_color, pts)
    # Outer Border
    pygame.draw.polygon(surface, border_color, pts, 2)
    # Inner Bevel Highlight
    inner_pts = [
        (x + chamfer + 2, y + 2),
        (x + w - chamfer - 2, y + 2),
        (x + w - 2, y + chamfer + 2),
        (x + w - 2, y + h - chamfer - 2),
        (x + w - chamfer - 2, y + h - 2),
        (x + chamfer + 2, y + h - 2),
        (x + 2, y + h - chamfer - 2),
        (x + 2, y + chamfer + 2)
    ]
    pygame.draw.polygon(surface, (border_color[0] // 2, border_color[1] // 2, border_color[2] // 2), inner_pts, 1)

    # Rivets at corners
    if rivets and w > 40 and h > 40:
        offset = 12
        draw_rivet(surface, x + offset, y + offset)
        draw_rivet(surface, x + w - offset, y + offset)
        draw_rivet(surface, x + offset, y + h - offset)
        draw_rivet(surface, x + w - offset, y + h - offset)

    # Optional Hazard Stripe Accent Header
    if hazard_header:
        h_rect = pygame.Rect(x + 4, y + 4, w - 8, 8)
        draw_hazard_stripes(surface, h_rect, stripe_w=8)

    # Title Bar
    if title:
        title_y = y + 24
        font_title = get_retro_font("stencil", 22, bold=True)
        draw_retro_text(surface, title, font_title, COLOR_AMBER_BRIGHT, x + w // 2, title_y,
                        shadow_color=COLOR_BLACK, shadow_offset=(2, 2))
        # Divider Line
        div_y = y + 42
        pygame.draw.line(surface, border_color, (x + 16, div_y), (x + w - 16, div_y), 2)
        pygame.draw.line(surface, (15, 20, 18), (x + 16, div_y + 1), (x + w - 16, div_y + 1), 1)

    if subtitle:
        sub_font = get_retro_font("digital", 14, bold=False)
        draw_retro_text(surface, subtitle, sub_font, COLOR_TEXT_DIM, x + w // 2, y + 54,
                        shadow_color=COLOR_BLACK, shadow_offset=(1, 1))

# ==============================================================================
# RETRO MILITARY BUTTON COMPONENT
# ==============================================================================
class MilitaryButton:
    """
    Authentic 90s heavy arcade military button with 3D bevel, rivet corners,
    hover glow, indicator arrows (▶ ... ◀), and sound feedback.
    """
    def __init__(self, text, x, y, width=280, height=64, theme=BTN_OLIVE, subtext=""):
        self.text = text
        self.subtext = subtext
        self.x = x
        self.y = y
        self.w = width
        self.h = height
        self.theme = theme
        self.rect = pygame.Rect(0, 0, width, height)
        self.rect.center = (x, y)
        self.hover = False
        self.pressed = False

    def update(self, pointer_pos):
        self.hover = self.rect.collidepoint(pointer_pos)
        return self.hover

    def draw(self, surface):
        x, y, w, h = self.rect.x, self.rect.y, self.rect.width, self.rect.height
        t = self.theme

        # Active colors based on hover
        face_col = t["hover_face"] if self.hover else t["face"]
        top_edge = t["hover_edge"] if self.hover else t["top_edge"]
        bottom_edge = t["bottom_edge"]
        text_col = t["hover_text"] if self.hover else t["text"]
        accent_col = t["accent"]

        # Drop shadow behind button
        shadow_rect = pygame.Rect(x + 4, y + 5, w, h)
        pygame.draw.rect(surface, (10, 12, 10), shadow_rect, border_radius=4)

        # 3D Button Face
        btn_rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(surface, face_col, btn_rect, border_radius=4)

        # 3D Bevel Edges
        # Top and Left Highlight
        pygame.draw.line(surface, top_edge, (x + 1, y + 1), (x + w - 2, y + 1), 2)
        pygame.draw.line(surface, top_edge, (x + 1, y + 1), (x + 1, y + h - 2), 2)
        # Bottom and Right Shadow
        pygame.draw.line(surface, bottom_edge, (x + 1, y + h - 2), (x + w - 2, y + h - 2), 2)
        pygame.draw.line(surface, bottom_edge, (x + w - 2, y + 1), (x + w - 2, y + h - 2), 2)

        # Outer Border
        pygame.draw.rect(surface, top_edge if self.hover else (30, 40, 35), btn_rect, 1, border_radius=4)

        # Corner Rivets
        draw_rivet(surface, x + 7, y + 7, 3)
        draw_rivet(surface, x + w - 7, y + 7, 3)
        draw_rivet(surface, x + 7, y + h - 7, 3)
        draw_rivet(surface, x + w - 7, y + h - 7, 3)

        # Text and Indicators
        font_main = get_retro_font("stencil", 24, bold=True)
        display_text = f"▶ {self.text} ◀" if self.hover else self.text
        
        # Text y-pos adjustments if there is subtext
        text_y = y + (h // 2 - 8 if self.subtext else h // 2)
        draw_retro_text(surface, display_text, font_main, text_col, x + w // 2, text_y,
                        shadow_color=COLOR_BLACK, shadow_offset=(2, 2))

        if self.subtext:
            font_sub = get_retro_font("digital", 13, bold=False)
            sub_col = accent_col if self.hover else COLOR_TEXT_DIM
            draw_retro_text(surface, self.subtext, font_sub, sub_col, x + w // 2, y + h - 14,
                            shadow_color=COLOR_BLACK, shadow_offset=(1, 1))

        # Amber corner brackets on hover for tactical target lock look
        if self.hover:
            bracket_len = 8
            # Top-left
            pygame.draw.line(surface, COLOR_AMBER_BRIGHT, (x - 4, y - 4), (x - 4 + bracket_len, y - 4), 2)
            pygame.draw.line(surface, COLOR_AMBER_BRIGHT, (x - 4, y - 4), (x - 4, y - 4 + bracket_len), 2)
            # Top-right
            pygame.draw.line(surface, COLOR_AMBER_BRIGHT, (x + w + 4, y - 4), (x + w + 4 - bracket_len, y - 4), 2)
            pygame.draw.line(surface, COLOR_AMBER_BRIGHT, (x + w + 4, y - 4), (x + w + 4, y - 4 + bracket_len), 2)
            # Bottom-left
            pygame.draw.line(surface, COLOR_AMBER_BRIGHT, (x - 4, y + h + 4), (x - 4 + bracket_len, y + h + 4), 2)
            pygame.draw.line(surface, COLOR_AMBER_BRIGHT, (x - 4, y + h + 4), (x - 4, y + h + 4 - bracket_len), 2)
            # Bottom-right
            pygame.draw.line(surface, COLOR_AMBER_BRIGHT, (x + w + 4, y + h + 4), (x + w + 4 - bracket_len, y + h + 4), 2)
            pygame.draw.line(surface, COLOR_AMBER_BRIGHT, (x + w + 4, y + h + 4), (x + w + 4, y + h + 4 - bracket_len), 2)

# ==============================================================================
# ROTATING TACTICAL RADAR
# ==============================================================================
class TacticalRadar:
    """
    Authentic 90s cathode-ray radar sweep display:
    Concentric rings, sweep beam, phosphor persistence, and blips.
    """
    def __init__(self, cx=1190, cy=640, radius=56):
        self.cx = cx
        self.cy = cy
        self.radius = radius
        self.angle = 0.0
        self.sweep_speed = 2.4 # radians per second
        self.blips = [
            {"angle": 0.5, "dist": 0.65, "alpha": 200},
            {"angle": 2.2, "dist": 0.40, "alpha": 150},
            {"angle": 4.1, "dist": 0.80, "alpha": 180},
            {"angle": 5.4, "dist": 0.55, "alpha": 120}
        ]
        self.radar_surf = pygame.Surface((radius * 2 + 10, radius * 2 + 10), pygame.SRCALPHA)

    def update(self, dt):
        self.angle = (self.angle + self.sweep_speed * dt) % (math.pi * 2)
        for b in self.blips:
            diff = abs(self.angle - b["angle"])
            if diff < 0.15 or abs(diff - math.pi * 2) < 0.15:
                b["alpha"] = 255
            else:
                b["alpha"] = max(40, b["alpha"] - int(120 * dt))

    def draw(self, surface):
        r = self.radius
        rcx, rcy = r + 5, r + 5
        self.radar_surf.fill((0, 0, 0, 0))

        # Base CRT green disc
        pygame.draw.circle(self.radar_surf, (10, 28, 14, 210), (rcx, rcy), r)
        # Outer Brass/Steel Rim
        pygame.draw.circle(self.radar_surf, COLOR_STEEL, (rcx, rcy), r, 3)
        pygame.draw.circle(self.radar_surf, COLOR_OLIVE_MID, (rcx, rcy), r - 2, 1)

        # Concentric Radar Range Rings
        pygame.draw.circle(self.radar_surf, (20, 80, 35, 180), (rcx, rcy), int(r * 0.33), 1)
        pygame.draw.circle(self.radar_surf, (20, 80, 35, 180), (rcx, rcy), int(r * 0.66), 1)
        pygame.draw.circle(self.radar_surf, (30, 110, 45, 200), (rcx, rcy), r, 1)

        # Cardinal Axes
        pygame.draw.line(self.radar_surf, (20, 70, 30), (rcx - r + 3, rcy), (rcx + r - 3, rcy), 1)
        pygame.draw.line(self.radar_surf, (20, 70, 30), (rcx, rcy - r + 3), (rcx, rcy + r - 3), 1)

        # Blips
        for b in self.blips:
            bx = int(rcx + math.cos(b["angle"]) * (b["dist"] * (r - 6)))
            by = int(rcy + math.sin(b["angle"]) * (b["dist"] * (r - 6)))
            pygame.draw.circle(self.radar_surf, (40, 240, 80, b["alpha"]), (bx, by), 3)

        # Sweep Line
        sx = int(rcx + math.cos(self.angle) * (r - 2))
        sy = int(rcy + math.sin(self.angle) * (r - 2))
        pygame.draw.line(self.radar_surf, COLOR_RADAR_GREEN, (rcx, rcy), (sx, sy), 2)

        # Blit to target screen
        surface.blit(self.radar_surf, (self.cx - rcx, self.cy - rcy))

        # Little Radar Badge Label
        font_lbl = get_retro_font("digital", 11, bold=True)
        draw_retro_text(surface, "AIR-SCAN 360°", font_lbl, COLOR_RADAR_GREEN, self.cx, self.cy + r + 10,
                        shadow_color=COLOR_BLACK, shadow_offset=(1, 1))

# ==============================================================================
# FLOATING COMBAT TEXT (Score pops, hit marks)
# ==============================================================================
class CombatTextManager:
    def __init__(self):
        self.texts = []

    def add(self, text, x, y, color=COLOR_AMBER_BRIGHT, size=22):
        self.texts.append({
            "text": text,
            "x": float(x),
            "y": float(y),
            "color": color,
            "size": size,
            "life": 1.0,
            "max_life": 1.0
        })

    def update(self, dt):
        for item in self.texts[:]:
            item["life"] -= dt * 1.5
            item["y"] -= 35 * dt
            if item["life"] <= 0:
                self.texts.remove(item)

    def draw(self, surface):
        for item in self.texts:
            alpha = max(0, min(255, int(255 * (item["life"] / item["max_life"]))))
            font = get_retro_font("arcade", item["size"], bold=True)
            surf = font.render(item["text"], True, item["color"])
            shadow = font.render(item["text"], True, COLOR_BLACK)
            surf.set_alpha(alpha)
            shadow.set_alpha(alpha)
            surface.blit(shadow, (int(item["x"]) - surf.get_width()//2 + 2, int(item["y"]) + 2))
            surface.blit(surf, (int(item["x"]) - surf.get_width()//2, int(item["y"])))

# ==============================================================================
# RETRO ARCADE HUD OVERLAY
# ==============================================================================
class RetroArcadeHUD:
    """
    Military Arcade Instrument HUD:
    - Top Steel & Olive Instrument Console with hazard warning tape
    - Blocky Arcade Score (e.g. 0012500) & High Score Display
    - Segmented Mission Timer gauge with flashing amber/red alerts
    - Targets Destroyed Tally with military icons
    - Defense Sector & Threat Status Readout
    - Corner Tactical Radar
    - Screen Bezel Framing with Tactical Crosshair Ticks
    """
    def __init__(self, width=1280, height=720):
        self.w = width
        self.h = height
        self.radar = TacticalRadar(cx=1195, cy=635, radius=54)
        self.high_score = load_high_score()
        self.flash_timer = 0.0

        # Precompute static CRT scanline and vignette overlay for maximum performance
        self.overlay_surf = pygame.Surface((width, height), pygame.SRCALPHA)
        self._build_static_overlay()

    def _build_static_overlay(self):
        """ Pre-renders subtle vintage CRT scanlines and cockpit screen vignette """
        for y in range(0, self.h, 3):
            pygame.draw.line(self.overlay_surf, (8, 12, 10, 22), (0, y), (self.w, y))

        border_w = 4
        pygame.draw.rect(self.overlay_surf, (15, 20, 18, 180), (0, 0, self.w, border_w))
        pygame.draw.rect(self.overlay_surf, (15, 20, 18, 180), (0, self.h - border_w, self.w, border_w))
        pygame.draw.rect(self.overlay_surf, (15, 20, 18, 180), (0, 0, border_w, self.h))
        pygame.draw.rect(self.overlay_surf, (15, 20, 18, 180), (self.w - border_w, 0, border_w, self.h))

        tick_len = 28
        ticks = [
            ((15, 15), (15 + tick_len, 15), (15, 15 + tick_len)),
            ((self.w - 15, 15), (self.w - 15 - tick_len, 15), (self.w - 15, 15 + tick_len)),
            ((15, self.h - 15), (15 + tick_len, self.h - 15), (15, self.h - 15 - tick_len)),
            ((self.w - 15, self.h - 15), (self.w - 15 - tick_len, self.h - 15), (self.w - 15, self.h - 15 - tick_len))
        ]
        for corner, h_end, v_end in ticks:
            pygame.draw.line(self.overlay_surf, COLOR_OLIVE_MID, corner, h_end, 2)
            pygame.draw.line(self.overlay_surf, COLOR_OLIVE_MID, corner, v_end, 2)

    def update(self, dt):
        self.radar.update(dt)
        self.flash_timer += dt

    def draw(self, surface, score, remain_time, mode="NORMAL", total_time=60):
        if score > self.high_score:
            self.high_score = score

        # ======================================================================
        # TOP CONSOLE INSTRUMENT BAR (Arcade Military Bezel)
        # ======================================================================
        bar_h = 74
        bar_rect = pygame.Rect(0, 0, self.w, bar_h)

        pygame.draw.rect(surface, COLOR_GUNMETAL_DARK, bar_rect)
        pygame.draw.line(surface, COLOR_STEEL, (0, 1), (self.w, 1), 2)
        pygame.draw.line(surface, COLOR_OLIVE_MID, (0, bar_h - 2), (self.w, bar_h - 2), 2)
        pygame.draw.line(surface, COLOR_BLACK, (0, bar_h), (self.w, bar_h), 2)

        # Hazard stripes on upper left and right
        draw_hazard_stripes(surface, pygame.Rect(4, 4, 80, 8), stripe_w=6)
        draw_hazard_stripes(surface, pygame.Rect(self.w - 84, 4, 80, 8), stripe_w=6)

        # ---------------- 1. SCORE DISPLAY (Arcade Monospace readout) ----------------
        sc_rect = pygame.Rect(110, 12, 230, 50)
        pygame.draw.rect(surface, (12, 16, 14), sc_rect, border_radius=3)
        pygame.draw.rect(surface, COLOR_STEEL, sc_rect, 1, border_radius=3)
        draw_rivet(surface, sc_rect.left + 5, sc_rect.top + 5, 2)
        draw_rivet(surface, sc_rect.right - 5, sc_rect.top + 5, 2)
        draw_rivet(surface, sc_rect.left + 5, sc_rect.bottom - 5, 2)
        draw_rivet(surface, sc_rect.right - 5, sc_rect.bottom - 5, 2)

        font_label = get_retro_font("digital", 12, bold=True)
        draw_retro_text(surface, "PLAYER SCORE", font_label, COLOR_AMBER, sc_rect.left + 14, sc_rect.top + 10,
                        shadow_color=COLOR_BLACK, center=False)

        font_digits = get_retro_font("digital", 28, bold=True)
        score_formatted = f"{score * 100:07d}"
        score_surf = font_digits.render(score_formatted, True, COLOR_AMBER_BRIGHT)
        surface.blit(score_surf, (sc_rect.right - score_surf.get_width() - 12, sc_rect.top + 18))

        # ---------------- 2. HIGH SCORE DISPLAY ----------------
        hi_rect = pygame.Rect(355, 12, 210, 50)
        pygame.draw.rect(surface, (12, 16, 14), hi_rect, border_radius=3)
        pygame.draw.rect(surface, COLOR_STEEL, hi_rect, 1, border_radius=3)
        draw_rivet(surface, hi_rect.left + 5, hi_rect.top + 5, 2)
        draw_rivet(surface, hi_rect.right - 5, hi_rect.top + 5, 2)
        draw_rivet(surface, hi_rect.left + 5, hi_rect.bottom - 5, 2)
        draw_rivet(surface, hi_rect.right - 5, hi_rect.bottom - 5, 2)

        draw_retro_text(surface, "HIGH RECORD", font_label, COLOR_RADAR_GREEN, hi_rect.left + 14, hi_rect.top + 10,
                        shadow_color=COLOR_BLACK, center=False)
        hi_formatted = f"{self.high_score * 100:07d}"
        hi_surf = font_digits.render(hi_formatted, True, COLOR_RADAR_GREEN)
        surface.blit(hi_surf, (hi_rect.right - hi_surf.get_width() - 12, hi_rect.top + 18))

        # ---------------- 3. CENTER MISSION & STATUS BANNER ----------------
        cx = self.w // 2
        font_mission = get_retro_font("stencil", 18, bold=True)
        draw_retro_text(surface, f"★ MISSION // SECTOR COMBAT [{mode}] ★", font_mission, COLOR_KHAKI_BRIGHT, cx, 24,
                        shadow_color=COLOR_BLACK, shadow_offset=(2, 2))

        # Defense Status LED Indicator
        status_color = COLOR_RADAR_GREEN
        status_text = "SYSTEMS NOMINAL // RADAR ACTIVE"
        if remain_time <= 10:
            blink = int(self.flash_timer * 6) % 2 == 0
            status_color = COLOR_ALERT_RED_BRIGHT if blink else COLOR_ALERT_RED_DIM
            status_text = "WARNING: TIME CRITICAL // EVACUATION IMMINENT"
        elif remain_time <= 20:
            status_color = COLOR_AMBER_BRIGHT
            status_text = "CAUTION: COMBAT WINDOW CLOSING"

        font_status = get_retro_font("digital", 13, bold=False)
        pygame.draw.circle(surface, status_color, (cx - 160, 48), 5)
        draw_retro_text(surface, status_text, font_status, status_color, cx + 10, 48,
                        shadow_color=COLOR_BLACK, shadow_offset=(1, 1))

        # ---------------- 4. TARGETS DESTROYED (Kills) ----------------
        tgt_rect = pygame.Rect(self.w - 565, 12, 190, 50)
        pygame.draw.rect(surface, (12, 16, 14), tgt_rect, border_radius=3)
        pygame.draw.rect(surface, COLOR_STEEL, tgt_rect, 1, border_radius=3)
        draw_rivet(surface, tgt_rect.left + 5, tgt_rect.top + 5, 2)
        draw_rivet(surface, tgt_rect.right - 5, tgt_rect.top + 5, 2)
        draw_rivet(surface, tgt_rect.left + 5, tgt_rect.bottom - 5, 2)
        draw_rivet(surface, tgt_rect.right - 5, tgt_rect.bottom - 5, 2)

        draw_retro_text(surface, "TARGETS DOWN", font_label, COLOR_AMBER, tgt_rect.left + 14, tgt_rect.top + 10,
                        shadow_color=COLOR_BLACK, center=False)
        kills_formatted = f"x {score:03d}"
        kills_surf = font_digits.render(kills_formatted, True, COLOR_AMBER_BRIGHT)
        surface.blit(kills_surf, (tgt_rect.right - kills_surf.get_width() - 14, tgt_rect.top + 18))

        # ---------------- 5. MISSION TIMER (Arcade Clock & Gauge) ----------------
        tm_rect = pygame.Rect(self.w - 360, 12, 250, 50)
        pygame.draw.rect(surface, (12, 16, 14), tm_rect, border_radius=3)
        
        t_border = COLOR_ALERT_RED_BRIGHT if (remain_time <= 10 and int(self.flash_timer * 6) % 2 == 0) else COLOR_STEEL
        pygame.draw.rect(surface, t_border, tm_rect, 1, border_radius=3)
        draw_rivet(surface, tm_rect.left + 5, tm_rect.top + 5, 2)
        draw_rivet(surface, tm_rect.right - 5, tm_rect.top + 5, 2)
        draw_rivet(surface, tm_rect.left + 5, tm_rect.bottom - 5, 2)
        draw_rivet(surface, tm_rect.right - 5, tm_rect.bottom - 5, 2)

        draw_retro_text(surface, "MISSION TIME", font_label, COLOR_KHAKI, tm_rect.left + 14, tm_rect.top + 10,
                        shadow_color=COLOR_BLACK, center=False)

        mins = remain_time // 60
        secs = remain_time % 60
        time_str = f"{mins:02d}:{secs:02d}"
        t_col = COLOR_ALERT_RED_BRIGHT if remain_time <= 10 else (COLOR_AMBER_BRIGHT if remain_time <= 20 else COLOR_WHITE)
        time_surf = font_digits.render(time_str, True, t_col)
        surface.blit(time_surf, (tm_rect.right - time_surf.get_width() - 14, tm_rect.top + 8))

        gauge_w = 220
        gauge_x = tm_rect.left + 15
        gauge_y = tm_rect.bottom - 12
        pygame.draw.rect(surface, (20, 25, 22), (gauge_x, gauge_y, gauge_w, 6))
        
        ratio = max(0.0, min(1.0, remain_time / float(total_time)))
        fill_w = int(gauge_w * ratio)
        fill_col = COLOR_ALERT_RED if ratio < 0.25 else (COLOR_AMBER if ratio < 0.5 else COLOR_RADAR_GREEN)
        
        for sx in range(0, fill_w, 6):
            seg_w = min(4, fill_w - sx)
            pygame.draw.rect(surface, fill_col, (gauge_x + sx, gauge_y, seg_w, 6))

        # ---------------- 6. BOTTOM MILITARY HARDWARE BAR ----------------
        bottom_h = 32
        bottom_rect = pygame.Rect(0, self.h - bottom_h, self.w, bottom_h)
        pygame.draw.rect(surface, COLOR_GUNMETAL_DARK, bottom_rect)
        pygame.draw.line(surface, COLOR_STEEL, (0, self.h - bottom_h), (self.w, self.h - bottom_h), 1)
        pygame.draw.line(surface, COLOR_OLIVE_MID, (0, self.h - bottom_h + 1), (self.w, self.h - bottom_h + 1), 1)

        font_btm = get_retro_font("digital", 12, bold=False)
        draw_retro_text(surface, "SYSTEM: 1999 FLIGHT TACTICAL // GUNSHIP AIR COMBAT", font_btm, COLOR_TEXT_DIM, 25, self.h - 16,
                        shadow_color=COLOR_BLACK, center=False)
        draw_retro_text(surface, "[ESC / P] TACTICAL PAUSE", font_btm, COLOR_AMBER, self.w // 2, self.h - 16,
                        shadow_color=COLOR_BLACK, center=True)
        draw_retro_text(surface, "RADAR FREQ: 9.4 GHz // WEAPONS READY", font_btm, COLOR_RADAR_GREEN, self.w - 180, self.h - 16,
                        shadow_color=COLOR_BLACK, center=True)

        # Draw Corner Radar
        self.radar.draw(surface)

        # Blit CRT Scanline & Screen Framing Overlay
        surface.blit(self.overlay_surf, (0, 0))

# ==============================================================================
# ENHANCED RETRO CROSSHAIR RETICLE
# ==============================================================================
class RetroCrosshair:
    """
    Classic 90s military gunship targeting reticle with center pip,
    outer circular brackets, 4-axis lead marks, and muzzle flash burst.
    """
    def __init__(self, raw_img=None):
        self.raw_img = raw_img
        self.shot_flash_timer = 0.0
        self.lock_target = False

    def trigger_shot(self):
        self.shot_flash_timer = 0.12

    def update(self, dt, is_locked=False):
        self.lock_target = is_locked
        if self.shot_flash_timer > 0:
            self.shot_flash_timer = max(0.0, self.shot_flash_timer - dt)

    def draw(self, surface, x, y):
        reticle_color = COLOR_ALERT_RED_BRIGHT if self.lock_target else (
            COLOR_AMBER_BRIGHT if self.shot_flash_timer > 0 else COLOR_RADAR_GREEN
        )

        r = 26
        for angle_deg in [45, 135, 225, 315]:
            rad = math.radians(angle_deg)
            ax = int(x + math.cos(rad) * r)
            ay = int(y + math.sin(rad) * r)
            pygame.draw.circle(surface, reticle_color, (ax, ay), 2)

        line_len = 12
        gap = 10
        pygame.draw.line(surface, reticle_color, (x - gap - line_len, y), (x - gap, y), 2)
        pygame.draw.line(surface, reticle_color, (x + gap, y), (x + gap + line_len, y), 2)
        pygame.draw.line(surface, reticle_color, (x, y - gap - line_len), (x, y - gap), 2)
        pygame.draw.line(surface, reticle_color, (x, y + gap), (x, y + gap + line_len), 2)

        pygame.draw.circle(surface, reticle_color, (x, y), 3)
        pygame.draw.circle(surface, (255, 255, 255), (x, y), 1)

        if self.shot_flash_timer > 0:
            flash_r = int(38 * (self.shot_flash_timer / 0.12))
            pygame.draw.circle(surface, (255, 240, 180, 180), (x, y), flash_r, 2)
            pygame.draw.line(surface, (255, 220, 100), (x - flash_r, y), (x + flash_r, y), 2)
            pygame.draw.line(surface, (255, 220, 100), (x, y - flash_r), (x, y + flash_r), 2)

        if self.raw_img:
            img_rect = self.raw_img.get_rect(center=(x, y))
            surface.blit(self.raw_img, img_rect)

        font_lead = get_retro_font("digital", 11, bold=True)
        txt = "LOCK [TGT]" if self.lock_target else "RNG: 420m"
        draw_retro_text(surface, txt, font_lead, reticle_color, x, y + 36,
                        shadow_color=COLOR_BLACK, shadow_offset=(1, 1))

# ==============================================================================
# RETRO TARGET LOCK BRACKETS FOR HELICOPTERS
# ==============================================================================
def draw_target_lock_brackets(surface, rect, color=COLOR_AMBER, corner_len=16):
    """ Draws tactical HUD target-tracking corner brackets around helicopter targets """
    x, y, w, h = rect.x, rect.y, rect.width, rect.height
    pygame.draw.line(surface, color, (x, y), (x + corner_len, y), 2)
    pygame.draw.line(surface, color, (x, y), (x, y + corner_len), 2)
    pygame.draw.line(surface, color, (x + w, y), (x + w - corner_len, y), 2)
    pygame.draw.line(surface, color, (x + w, y), (x + w, y + corner_len), 2)
    pygame.draw.line(surface, color, (x, y + h), (x + corner_len, y + h), 2)
    pygame.draw.line(surface, color, (x, y + h), (x, y + h - corner_len), 2)
    pygame.draw.line(surface, color, (x + w, y + h), (x + w - corner_len, y + h), 2)
    pygame.draw.line(surface, color, (x + w, y + h), (x + w, y + h - corner_len), 2)

# ==============================================================================
# RETRO TITLE BANNER DRAWING (For Main Menu)
# ==============================================================================
def draw_arcade_title(surface, x, y):
    """
    Renders the iconic 90s military arcade gunship title screen branding.
    """
    font_main = get_retro_font("stencil", 56, bold=True)
    font_sub = get_retro_font("stencil", 26, bold=True)
    font_badge = get_retro_font("digital", 13, bold=True)

    # 1. Background tactical stencil box
    box_w, box_h = 760, 140
    box_rect = pygame.Rect(x - box_w // 2, y - box_h // 2, box_w, box_h)
    draw_military_panel(surface, box_rect, bg_color=(18, 24, 20), border_color=COLOR_OLIVE_LIGHT, hazard_header=True)

    # 2. Main Title Line: "GUNSHIP BATTLE"
    # Triple-layer retro extrusion: shadow, border, metallic face
    draw_retro_text(surface, "GUNSHIP BATTLE", font_main, COLOR_AMBER_BRIGHT, x, y - 10,
                    shadow_color=COLOR_BLACK, shadow_offset=(4, 4),
                    outline_color=COLOR_OLIVE_DARK, outline_width=2)

    # 3. Subtitle Line: "AIR DEFENSE 1999 // ARCADE COMBAT"
    draw_retro_text(surface, "★ AIR DEFENSE 1999 // TACTICAL INTERCEPT ★", font_sub, COLOR_KHAKI_BRIGHT, x, y + 36,
                    shadow_color=COLOR_BLACK, shadow_offset=(2, 2))

    # 4. Small corner serial badge
    draw_retro_text(surface, "MODEL: GB-99 // REV-2.4", font_badge, COLOR_RADAR_GREEN, box_rect.left + 24, box_rect.bottom - 16,
                    shadow_color=COLOR_BLACK, center=False)
    draw_retro_text(surface, "MIL-SPEC CRT DISPLAY", font_badge, COLOR_TEXT_DIM, box_rect.right - 180, box_rect.bottom - 16,
                    shadow_color=COLOR_BLACK, center=False)

# ==============================================================================
# MODALS: HOW TO PLAY (BRIEFING) & TACTICAL PAUSE
# ==============================================================================
def show_briefing_screen(screen, clock, get_pointer, crosshair_fx, gun_sound, bg_system):
    """
    Tactical Mission Briefing / How to Play Screen
    """
    btn_close = MilitaryButton("ACKNOWLEDGE & RETURN", 1280 // 2, 595, width=340, height=60, theme=BTN_OLIVE)
    last_click = 0
    
    while True:
        dt = clock.tick(60) / 1000.0
        dt = min(dt, 0.05)
        px, py, is_hand = get_pointer()

        bg_system.update(dt * 0.3, px, py)
        bg_system.draw(screen)

        # Center Classified Briefing Dossier
        panel_rect = pygame.Rect(1280 // 2 - 440, 60, 880, 570)
        draw_military_panel(screen, panel_rect, title="CLASSIFIED MISSION BRIEFING // AIR DEFENSE", 
                            subtitle="HIGH COMMAND DIRECTIVE // OPERATION ROARING ROTOR",
                            bg_color=(16, 22, 19), border_color=COLOR_OLIVE_LIGHT, hazard_header=True)

        # Briefing Sections
        instructions = [
            ("TARGET ACQUISITION", "AIM WITH WEBCAM HAND TRACKING OR MOUSE POINTER.", COLOR_RADAR_GREEN),
            ("FIRE 30mm CANNON", "LEFT CLICK OR TRIGGER TO DESTROY HOSTILE ROTORCRAFT.", COLOR_AMBER_BRIGHT),
            ("MISSION TIMEFRAME", "YOU HAVE 60 SECONDS TO CLEAR THE AIRSPACE OF HOSTILES.", COLOR_KHAKI_BRIGHT),
            ("DIFFICULTY THREAT", "RECRUIT (SPEED 3) / VETERAN (SPEED 5) / ACE PILOT (SPEED 8).", COLOR_ALERT_RED_BRIGHT),
            ("TACTICAL PAUSE", "PRESS [ESC] OR [P] TO ENGAGE TACTICAL CEASE-FIRE AT ANY TIME.", COLOR_STEEL_BRIGHT)
        ]

        font_h = get_retro_font("stencil", 20, bold=True)
        font_b = get_retro_font("digital", 15, bold=False)

        cur_y = 150
        for title, desc, col in instructions:
            # Bullet marker
            pygame.draw.rect(screen, col, (panel_rect.left + 45, cur_y + 2, 12, 12))
            draw_rivet(screen, panel_rect.left + 51, cur_y + 8, 2)
            draw_retro_text(screen, title, font_h, col, panel_rect.left + 72, cur_y + 8,
                            shadow_color=COLOR_BLACK, center=False)
            cur_y += 28
            draw_retro_text(screen, desc, font_b, COLOR_WHITE, panel_rect.left + 72, cur_y + 6,
                            shadow_color=COLOR_BLACK, center=False)
            cur_y += 44

        # Close Button
        btn_close.update((px, py))
        btn_close.draw(screen)

        crosshair_fx.update(dt, False)
        crosshair_fx.draw(screen, px, py)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.KEYDOWN and (event.key == pygame.K_ESCAPE or event.key == pygame.K_RETURN):
                return
            if event.type == pygame.MOUSEBUTTONDOWN:
                now = time.time()
                if now - last_click > 0.3:
                    gun_sound.play()
                    crosshair_fx.trigger_shot()
                    last_click = now
                    if btn_close.rect.collidepoint(px, py):
                        return

        pygame.display.flip()

def pause_screen(screen, clock, get_pointer, crosshair_fx, gun_sound, bg_system):
    """
    Tactical Pause Screen with Resume, Restart, Menu options
    """
    btn_resume = MilitaryButton("RESUME ENGAGEMENT", 1280 // 2, 300, width=320, height=62, theme=BTN_OLIVE)
    btn_restart = MilitaryButton("RESTART MISSION", 1280 // 2, 385, width=320, height=62, theme=BTN_AMBER)
    btn_menu = MilitaryButton("ABORT TO BASE", 1280 // 2, 470, width=320, height=62, theme=BTN_RED)

    overlay = pygame.Surface((1280, 720), pygame.SRCALPHA)
    overlay.fill((10, 15, 12, 190))
    screen.blit(overlay, (0, 0))

    last_click = 0

    while True:
        dt = clock.tick(60) / 1000.0
        dt = min(dt, 0.05)
        px, py, is_hand = get_pointer()

        # Center Pause Box
        p_rect = pygame.Rect(1280 // 2 - 250, 140, 500, 420)
        draw_military_panel(screen, p_rect, title="TACTICAL PAUSE // CEASE FIRE",
                            subtitle="COMBAT SUSPENDED // AIRSPACE ON HOLD",
                            bg_color=(18, 24, 20), border_color=COLOR_AMBER, hazard_header=True)

        btn_resume.update((px, py))
        btn_restart.update((px, py))
        btn_menu.update((px, py))

        btn_resume.draw(screen)
        btn_restart.draw(screen)
        btn_menu.draw(screen)

        crosshair_fx.update(dt, False)
        crosshair_fx.draw(screen, px, py)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "EXIT"
            if event.type == pygame.KEYDOWN and (event.key == pygame.K_p or event.key == pygame.K_ESCAPE):
                return "RESUME"
            if event.type == pygame.MOUSEBUTTONDOWN:
                now = time.time()
                if now - last_click > 0.3:
                    gun_sound.play()
                    crosshair_fx.trigger_shot()
                    last_click = now
                    if btn_resume.rect.collidepoint(px, py):
                        return "RESUME"
                    if btn_restart.rect.collidepoint(px, py):
                        return "RESTART"
                    if btn_menu.rect.collidepoint(px, py):
                        return "MENU"

        pygame.display.flip()
