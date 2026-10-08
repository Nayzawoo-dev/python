import pygame
import math
import random
import json
import os

# ==============================================================================
# NOSTALGIC COLOR PALETTE
# Cheerful childhood arcade / carnival palette: warm, playful, high-contrast
# ==============================================================================
COLOR_SKY_TOP = (110, 192, 252)       # Soft warm sky blue
COLOR_SKY_BOTTOM = (215, 240, 255)    # Gentle sunny horizon
COLOR_CREAM = (255, 251, 240)         # Soft warm cream
COLOR_PANEL_BG = (255, 248, 230)      # Vintage cardboard/parchment
COLOR_PANEL_BORDER = (85, 45, 20)     # Deep chocolate outline
COLOR_PANEL_INNER = (255, 215, 0)     # Golden accent border
COLOR_GOLD = (255, 215, 0)
COLOR_DARK_TEXT = (70, 30, 10)

# Tactile button color schemes: (face, base_3d, highlight, text, outline)
BTN_GREEN = {
    "face": (46, 204, 113),
    "base": (30, 145, 80),
    "high": (120, 235, 160),
    "text": (255, 255, 255),
    "outline": (25, 95, 55)
}

BTN_YELLOW = {
    "face": (250, 190, 30),
    "base": (200, 135, 10),
    "high": (255, 230, 120),
    "text": (70, 40, 10),
    "outline": (130, 80, 15)
}

BTN_RED = {
    "face": (235, 75, 75),
    "base": (175, 40, 40),
    "high": (255, 140, 140),
    "text": (255, 255, 255),
    "outline": (110, 25, 25)
}

BTN_BLUE = {
    "face": (52, 152, 219),
    "base": (35, 110, 165),
    "high": (140, 205, 250),
    "text": (255, 255, 255),
    "outline": (20, 75, 115)
}

BTN_PURPLE = {
    "face": (155, 89, 182),
    "base": (115, 60, 140),
    "high": (210, 155, 235),
    "text": (255, 255, 255),
    "outline": (80, 35, 100)
}

# ==============================================================================
# HIGH SCORE STORAGE
# ==============================================================================
HIGH_SCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "highscore.json")

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
# FONT CACHE & HELPERS
# ==============================================================================
_FONT_CACHE = {}

def get_arcade_font(size, bold=True):
    key = (size, bold)
    if key not in _FONT_CACHE:
        chosen = None
        # Prioritize quintessential chunky, friendly childhood arcade fonts
        for name in ["arialrounded", "cooperblack", "comicsansms", "impact", "arial"]:
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
# RETRO TEXT WITH OUTLINES & 3D EXTRUSIONS
# ==============================================================================
def draw_text_with_outline(surface, text, font, text_color, outline_color, x, y, 
                            outline_width=3, shadow_offset=(0, 3), shadow_color=(0, 0, 0, 120), center=True):
    """ Renders high-legibility nostalgic text with drop-shadow and comic outline """
    main_surf = font.render(text, True, text_color)
    w, h = main_surf.get_size()
    
    so_x = abs(shadow_offset[0]) if shadow_offset else 0
    so_y = abs(shadow_offset[1]) if shadow_offset else 0
    pad = outline_width + max(so_x, so_y) + 4
    comp_surf = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
    
    cx, cy = pad, pad
    
    # 1. Drop shadow
    if shadow_offset and shadow_color:
        shadow_surf = font.render(text, True, shadow_color[:3])
        if len(shadow_color) > 3 and shadow_color[3] < 255:
            shadow_surf.set_alpha(shadow_color[3])
        comp_surf.blit(shadow_surf, (cx + shadow_offset[0], cy + shadow_offset[1]))
        
    # 2. Comic Outline
    if outline_width > 0 and outline_color:
        out_surf = font.render(text, True, outline_color)
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx * dx + dy * dy <= outline_width * outline_width and (dx != 0 or dy != 0):
                    comp_surf.blit(out_surf, (cx + dx, cy + dy))
                    
    # 3. Foreground text
    comp_surf.blit(main_surf, (cx, cy))
    
    target_x = x - (w // 2 + pad) if center else x - pad
    target_y = y - (h // 2 + pad) if center else y - pad
    surface.blit(comp_surf, (target_x, target_y))
    
    return pygame.Rect(x - w // 2 if center else x, y - h // 2 if center else y, w, h)

def draw_3d_title(surface, text, font, x, y, 
                  fill_color=(255, 225, 45), 
                  border_color=(70, 30, 10), 
                  extrude_color=(190, 70, 20), 
                  extrude_depth=7,
                  center=True):
    """
    Renders bold, chunky, 3D extruded arcade title letters reminiscent of 
    classic childhood carnival/arcade logos.
    """
    for d in range(extrude_depth, 0, -1):
        draw_text_with_outline(
            surface, text, font, 
            text_color=extrude_color, 
            outline_color=border_color, 
            x=x, y=y + d, 
            outline_width=3, 
            shadow_offset=None, 
            center=center
        )
    return draw_text_with_outline(
        surface, text, font, 
        text_color=fill_color, 
        outline_color=border_color, 
        x=x, y=y, 
        outline_width=4, 
        shadow_offset=None, 
        center=center
    )

# ==============================================================================
# RETRO TACTILE BUTTON
# ==============================================================================
class TactileButton:
    """
    Classic childhood toy/arcade tactile button:
    - 3D bottom bevel slab
    - Glossy highlight curve
    - Depresses on press, lifts on hover
    - Chunky rounded rectangle with dark outline
    """
    def __init__(self, text, x, y, width=280, height=68, color_scheme=BTN_GREEN, font_size=34):
        self.text = text
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.scheme = color_scheme
        self.font = get_arcade_font(font_size, bold=True)
        self.rect = pygame.Rect(0, 0, width, height)
        self.rect.center = (x, y)
        self.hover = False
        self.pressed = False

    def update(self, pointer_pos, is_pressed=False):
        if pointer_pos:
            self.hover = self.rect.collidepoint(pointer_pos)
        else:
            self.hover = False
        self.pressed = self.hover and is_pressed
        return self.hover

    def draw(self, surface):
        if self.pressed:
            offset_y = 4
        elif self.hover:
            offset_y = -3
        else:
            offset_y = 0

        bevel_depth = 6
        rx, ry, rw, rh = self.rect.x, self.rect.y, self.rect.width, self.rect.height

        # 1. Soft ground drop-shadow
        shadow_surf = pygame.Surface((rw + 8, rh + 8), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, (0, 0, 0, 65), (4, 6, rw, rh), border_radius=18)
        surface.blit(shadow_surf, (rx - 4, ry - 2))

        # 2. Bottom 3D base/slab
        base_rect = pygame.Rect(rx, ry + bevel_depth, rw, rh)
        pygame.draw.rect(surface, self.scheme["base"], base_rect, border_radius=18)
        pygame.draw.rect(surface, self.scheme["outline"], base_rect, 3, border_radius=18)

        # 3. Top face
        face_y = ry + offset_y
        face_rect = pygame.Rect(rx, face_y, rw, rh)
        face_color = self.scheme["high"] if self.hover and not self.pressed else self.scheme["face"]
        pygame.draw.rect(surface, face_color, face_rect, border_radius=18)
        
        # 4. Gloss shine
        shine_rect = pygame.Rect(rx + 6, face_y + 4, rw - 12, (rh // 2) - 4)
        shine_surf = pygame.Surface((shine_rect.width, shine_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(shine_surf, (255, 255, 255, 75), shine_surf.get_rect(), border_radius=12)
        surface.blit(shine_surf, (shine_rect.x, shine_rect.y))

        # 5. Dark comic outline
        pygame.draw.rect(surface, self.scheme["outline"], face_rect, 3, border_radius=18)

        # 6. Button text with shadow
        draw_text_with_outline(
            surface, self.text, self.font,
            text_color=self.scheme["text"],
            outline_color=self.scheme["outline"],
            x=face_rect.centerx,
            y=face_rect.centery,
            outline_width=2,
            shadow_offset=(0, 2),
            shadow_color=(0, 0, 0, 100),
            center=True
        )

# ==============================================================================
# NOSTALGIC ARCADE PANEL
# ==============================================================================
def draw_arcade_panel(surface, rect, title=None, border_color=COLOR_PANEL_BORDER, bg_color=COLOR_PANEL_BG, corner_radius=22):
    """
    Draws a warm childhood arcade/carnival style board with wooden/parchment fill,
    decorative rounded borders, and golden corner studs.
    """
    x, y, w, h = rect
    
    # Outer soft drop shadow
    shadow = pygame.Surface((w + 14, h + 14), pygame.SRCALPHA)
    pygame.draw.rect(shadow, (0, 0, 0, 85), (7, 9, w, h), border_radius=corner_radius)
    surface.blit(shadow, (x - 7, y - 7))

    # Main panel body
    panel_rect = pygame.Rect(x, y, w, h)
    pygame.draw.rect(surface, bg_color, panel_rect, border_radius=corner_radius)

    # Inner decorative border
    inner_rect = pygame.Rect(x + 7, y + 7, w - 14, h - 14)
    pygame.draw.rect(surface, COLOR_PANEL_INNER, inner_rect, 3, border_radius=corner_radius - 4)

    # Outer dark comic outline
    pygame.draw.rect(surface, border_color, panel_rect, 4, border_radius=corner_radius)

    # Corner gold studs / rivets
    stud_offsets = [
        (x + 15, y + 15),
        (x + w - 15, y + 15),
        (x + 15, y + h - 15),
        (x + w - 15, y + h - 15)
    ]
    for sx, sy in stud_offsets:
        pygame.draw.circle(surface, border_color, (sx, sy), 5)
        pygame.draw.circle(surface, (255, 225, 80), (sx, sy), 3)

    # Optional Title Ribbon
    if title:
        title_font = get_arcade_font(32, bold=True)
        tw = title_font.size(title)[0] + 56
        th = 46
        ribbon_rect = pygame.Rect(x + (w - tw) // 2, y - 20, tw, th)
        
        # Ribbon shadow
        pygame.draw.rect(surface, (0, 0, 0, 60), ribbon_rect.move(0, 3), border_radius=14)
        # Ribbon body
        pygame.draw.rect(surface, (235, 75, 75), ribbon_rect, border_radius=14)
        pygame.draw.rect(surface, (255, 215, 0), ribbon_rect, 3, border_radius=14)
        # Ribbon title text
        draw_text_with_outline(
            surface, title, title_font,
            text_color=(255, 255, 255),
            outline_color=(120, 20, 20),
            x=ribbon_rect.centerx,
            y=ribbon_rect.centery,
            outline_width=2,
            shadow_offset=(0, 2),
            shadow_color=(0, 0, 0, 100),
            center=True
        )

# ==============================================================================
# PROCEDURAL GOLDEN STARS
# ==============================================================================
def draw_star(surface, cx, cy, radius=18, color=COLOR_GOLD, outline_color=(120, 70, 10)):
    """ Draws a cheerful 5-point cartoon star with outline """
    pts = []
    for i in range(10):
        angle = -math.pi / 2 + i * (math.pi / 5)
        r = radius if (i % 2 == 0) else radius * 0.45
        pts.append((cx + math.cos(angle) * r, cy + math.sin(angle) * r))
    pygame.draw.polygon(surface, outline_color, pts)
    # Inner star
    inner_pts = []
    for i in range(10):
        angle = -math.pi / 2 + i * (math.pi / 5)
        r = (radius - 2) if (i % 2 == 0) else (radius * 0.45 - 1)
        inner_pts.append((cx + math.cos(angle) * r, cy + math.sin(angle) * r))
    pygame.draw.polygon(surface, color, inner_pts)

# ==============================================================================
# CARTOON CLOUDS & SKY BACKGROUND
# ==============================================================================
class SkyDecorations:
    """
    Renders a nostalgic sunny blue sky with drifting puffy cartoon clouds.
    """
    def __init__(self, width=1280, height=720):
        self.width = width
        self.height = height
        self.clouds = [
            {"x": 60,   "y": 60,  "speed": 0.35, "scale": 1.1},
            {"x": 420,  "y": 105, "speed": 0.22, "scale": 0.85},
            {"x": 820,  "y": 50,  "speed": 0.38, "scale": 1.25},
            {"x": 1140, "y": 135, "speed": 0.26, "scale": 0.95},
        ]
        self.cloud_surf = self._make_cloud_surface()
        
    def _make_cloud_surface(self):
        surf = pygame.Surface((220, 100), pygame.SRCALPHA)
        circles = [
            (50, 60, 36), (90, 48, 44), (135, 52, 40), (170, 62, 32), (110, 68, 38)
        ]
        for cx, cy, r in circles:
            pygame.draw.circle(surf, (215, 230, 245, 180), (cx, cy + 5), r)
        for cx, cy, r in circles:
            pygame.draw.circle(surf, (255, 255, 255, 240), (cx, cy), r)
        for cx, cy, r in circles:
            pygame.draw.circle(surf, (255, 255, 255, 255), (cx - 4, cy - 6), max(10, r - 8))
        return surf

    def update(self):
        for c in self.clouds:
            c["x"] += c["speed"]
            if c["x"] > self.width + 120:
                c["x"] = -180

    def draw_sky(self, surface):
        top_color = COLOR_SKY_TOP
        bot_color = COLOR_SKY_BOTTOM
        steps = 40
        step_h = self.height / steps
        for i in range(steps):
            t = i / float(steps)
            r = int(top_color[0] * (1 - t) + bot_color[0] * t)
            g = int(top_color[1] * (1 - t) + bot_color[1] * t)
            b = int(top_color[2] * (1 - t) + bot_color[2] * t)
            pygame.draw.rect(surface, (r, g, b), (0, int(i * step_h), self.width, int(step_h) + 1))

        for c in self.clouds:
            scaled = pygame.transform.scale(
                self.cloud_surf, 
                (int(220 * c["scale"]), int(100 * c["scale"]))
            )
            surface.blit(scaled, (int(c["x"]), int(c["y"])))

# ==============================================================================
# CARTOON BALLOON DECORATION
# ==============================================================================
def draw_cartoon_balloon(surface, cx, cy, radius=32, color=(240, 60, 60), string_len=55, wobble=0.0):
    """
    Draws a cheerful cartoon balloon with highlight sheen, knot, and curled string.
    """
    outline_color = (max(0, color[0] - 80), max(0, color[1] - 80), max(0, color[2] - 80))
    
    # 1. Curled string
    pts = []
    for i in range(12):
        t = i / 11.0
        sy = cy + radius + 8 + t * string_len
        sx = cx + math.sin(t * 3.5 + wobble) * 8
        pts.append((sx, sy))
    if len(pts) > 1:
        pygame.draw.lines(surface, (180, 160, 140), False, pts, 2)
        
    # 2. Balloon knot
    knot_y = cy + radius + 4
    pygame.draw.polygon(surface, outline_color, [
        (cx - 6, knot_y + 6), (cx + 6, knot_y + 6), (cx, knot_y)
    ])
    pygame.draw.polygon(surface, color, [
        (cx - 5, knot_y + 5), (cx + 5, knot_y + 5), (cx, knot_y + 1)
    ])

    # 3. Balloon oval body
    oval_rect = pygame.Rect(cx - radius, cy - int(radius * 1.15), radius * 2, int(radius * 2.3))
    pygame.draw.ellipse(surface, outline_color, oval_rect)
    pygame.draw.ellipse(surface, color, oval_rect.inflate(-4, -4))

    # 4. Gloss specular highlight
    high_x = cx - int(radius * 0.45)
    high_y = cy - int(radius * 0.55)
    high_rect = pygame.Rect(high_x, high_y, int(radius * 0.55), int(radius * 0.8))
    high_surf = pygame.Surface((high_rect.width, high_rect.height), pygame.SRCALPHA)
    pygame.draw.ellipse(high_surf, (255, 255, 255, 170), high_surf.get_rect())
    surface.blit(high_surf, (high_rect.x, high_rect.y))

# ==============================================================================
# VISUAL-ONLY PARTICLE & FEEDBACK SYSTEM
# ==============================================================================
class VisualEffectManager:
    """
    Manages lightweight, satisfying visual-only effects:
    - Balloon pop confetti & star sparkles
    - Floating '+1' score popups
    - Subtle screen shake trigger
    """
    def __init__(self):
        self.particles = []
        self.popups = []
        self.shake_frames = 0
        self.shake_magnitude = 0

    def trigger_pop(self, x, y, base_color=(255, 80, 80)):
        palette = [
            (255, 75, 75), (255, 215, 0), (46, 204, 113), 
            (52, 152, 219), (255, 120, 200), (255, 255, 255)
        ]
        for _ in range(14):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(3.5, 9.5)
            self.particles.append({
                "x": x + 150,
                "y": y + 140,
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed - 2.5,
                "color": random.choice(palette),
                "size": random.randint(5, 10),
                "rot": random.uniform(0, 360),
                "vrot": random.uniform(-15, 15),
                "life": 1.0,
                "decay": random.uniform(0.035, 0.055)
            })
            
        self.popups.append({
            "x": x + 150,
            "y": y + 100,
            "text": "+1",
            "color": (255, 235, 60),
            "life": 1.0,
            "decay": 0.04
        })

        self.shake_frames = 3
        self.shake_magnitude = 3

    def update(self):
        for p in self.particles[:]:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vy"] += 0.35
            p["rot"] += p["vrot"]
            p["life"] -= p["decay"]
            if p["life"] <= 0:
                self.particles.remove(p)

        for pop in self.popups[:]:
            pop["y"] -= 1.8
            pop["life"] -= pop["decay"]
            if pop["life"] <= 0:
                self.popups.remove(pop)

        if self.shake_frames > 0:
            self.shake_frames -= 1

    def get_screen_offset(self):
        if self.shake_frames > 0:
            ox = random.randint(-self.shake_magnitude, self.shake_magnitude)
            oy = random.randint(-self.shake_magnitude, self.shake_magnitude)
            return ox, oy
        return 0, 0

    def draw(self, surface):
        for p in self.particles:
            alpha = max(0, min(255, int(p["life"] * 255)))
            s = int(p["size"])
            part_surf = pygame.Surface((s * 2, s * 2), pygame.SRCALPHA)
            pygame.draw.rect(part_surf, (*p["color"], alpha), (0, 0, s, s))
            rotated = pygame.transform.rotate(part_surf, p["rot"])
            surface.blit(rotated, (p["x"] - rotated.get_width() // 2, p["y"] - rotated.get_height() // 2))

        popup_font = get_arcade_font(32, bold=True)
        for pop in self.popups:
            alpha = max(0, min(255, int(pop["life"] * 255)))
            text_surf = popup_font.render(pop["text"], True, pop["color"])
            text_surf.set_alpha(alpha)
            
            out_surf = popup_font.render(pop["text"], True, (70, 30, 10))
            out_surf.set_alpha(alpha)
            
            w, h = text_surf.get_size()
            comp = pygame.Surface((w + 8, h + 8), pygame.SRCALPHA)
            for dx, dy in [(-2,0), (2,0), (0,-2), (0,2)]:
                comp.blit(out_surf, (4 + dx, 4 + dy))
            comp.blit(text_surf, (4, 4))
            
            surface.blit(comp, (pop["x"] - w // 2, pop["y"]))

# ==============================================================================
# CLASSIC ARCADE HUD
# ==============================================================================
def draw_arcade_hud(surface, score, high_score, time_remain, mode_text, window_width=1280):
    """
    Draws a charming childhood arcade header:
    - Vintage cream boxes with colorful arcade borders
    - Chunky padded score: '000120'
    - High score: 'BEST: 000500'
    - Mode badge
    - Pulsing arcade countdown clock
    """
    font_val = get_arcade_font(34, bold=True)
    font_lbl = get_arcade_font(20, bold=True)

    hud_y = 18

    # 1. SCORE BOX
    box1_x, box1_w = 25, 230
    box_h = 70
    _draw_hud_box(surface, box1_x, hud_y, box1_w, box_h, 
                  label="SCORE", value=f"{score:06d}", 
                  font_lbl=font_lbl, font_val=font_val, 
                  border_color=(235, 130, 20), val_color=(70, 30, 10))

    # 2. HIGH SCORE BOX
    box2_x, box2_w = 270, 210
    _draw_hud_box(surface, box2_x, hud_y, box2_w, box_h, 
                  label="BEST", value=f"{high_score:06d}", 
                  font_lbl=font_lbl, font_val=font_val, 
                  border_color=(46, 204, 113), val_color=(30, 90, 50))

    # 3. DIFFICULTY BADGE (Center)
    badge_colors = {
        "EASY": ((46, 204, 113), (25, 110, 60)),
        "NORMAL": ((243, 156, 18), (140, 80, 10)),
        "HARD": ((231, 76, 60), (120, 30, 20))
    }
    bg_c, out_c = badge_colors.get(mode_text, ((52, 152, 219), (20, 75, 115)))
    
    badge_w, badge_h = 170, 46
    badge_x = (window_width - badge_w) // 2
    badge_rect = pygame.Rect(badge_x, hud_y + 12, badge_w, badge_h)
    
    # Drop shadow
    pygame.draw.rect(surface, (0, 0, 0, 60), badge_rect.move(0, 3), border_radius=16)
    pygame.draw.rect(surface, bg_c, badge_rect, border_radius=16)
    pygame.draw.rect(surface, (255, 255, 255), badge_rect, 3, border_radius=16)
    draw_text_with_outline(
        surface, f"{mode_text}", get_arcade_font(22, bold=True),
        text_color=(255, 255, 255), outline_color=out_c,
        x=badge_rect.centerx, y=badge_rect.centery,
        outline_width=2, center=True
    )

    # 4. TIMER BOX (Right side)
    box3_w = 200
    box3_x = window_width - box3_w - 170
    is_urgent = time_remain <= 10
    time_color = (230, 40, 40) if is_urgent else (70, 30, 10)
    time_border = (230, 40, 40) if is_urgent else (52, 152, 219)
    
    _draw_hud_box(surface, box3_x, hud_y, box3_w, box_h, 
                  label="TIME LEFT", value=f"{max(0, time_remain):02d}s", 
                  font_lbl=font_lbl, font_val=font_val, 
                  border_color=time_border, val_color=time_color)
    return {"score": (box1_x, hud_y, box1_w, box_h), "best": (box2_x, hud_y, box2_w, box_h), "time": (box3_x, hud_y, box3_w, box_h)}

def _draw_hud_box(surface, x, y, w, h, label, value, font_lbl, font_val, border_color, val_color):
    rect = pygame.Rect(x, y, w, h)
    
    shadow = pygame.Surface((w + 6, h + 6), pygame.SRCALPHA)
    pygame.draw.rect(shadow, (0, 0, 0, 65), (3, 4, w, h), border_radius=16)
    surface.blit(shadow, (x - 3, y - 2))

    pygame.draw.rect(surface, COLOR_PANEL_BG, rect, border_radius=16)
    pygame.draw.rect(surface, border_color, rect, 4, border_radius=16)
    
    pygame.draw.circle(surface, (255, 215, 0), (x + 12, y + 12), 3)
    pygame.draw.circle(surface, (255, 215, 0), (x + w - 12, y + 12), 3)
    
    draw_text_with_outline(
        surface, label, font_lbl,
        text_color=border_color, outline_color=(255, 255, 255),
        x=rect.centerx, y=y + 18, outline_width=2, center=True
    )
    
    draw_text_with_outline(
        surface, value, font_val,
        text_color=val_color, outline_color=(255, 255, 255),
        x=rect.centerx, y=y + 45, outline_width=2, center=True
    )
