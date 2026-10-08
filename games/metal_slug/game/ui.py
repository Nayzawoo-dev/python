"""
Retro Military Arcade User Interface and Menu Screens (Metal Slug Style).
Features clean, highly-readable typography, polished visual hierarchy,
interactive background selector, calibration view, and arcade HUD without bloat.
"""

from typing import List, Dict, Optional, Tuple
import math
import pygame
from config import (
    BASE_DIR, SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_BLACK, COLOR_DARK_GREEN,
    COLOR_MILITARY_GREEN, COLOR_OLIVE, COLOR_KHAKI, COLOR_AMBER, COLOR_ORANGE,
    COLOR_RED, COLOR_CRIMSON, COLOR_YELLOW, COLOR_WHITE, COLOR_GRAY, COLOR_STEEL, COLOR_CYAN,
    WEAPONS_INFO, WEAPON_MACHINE_GUN, WEAPON_MISSILE, WEAPON_LASER
)
from game.background_manager import BackgroundManager

class UIManager:
    """Manages all game UI rendering, HUD, menus, and overlays."""
    def __init__(self, settings: dict, bg_manager: BackgroundManager):
        self.settings = settings
        self.bg_manager = bg_manager

        # Initialize readable typography system
        self._init_fonts()

        # Pulse and blink timers
        self.blink_timer: float = 0.0

    def _init_fonts(self) -> None:
        """Load crisp system fonts with clean, readable weights and proper hierarchy."""
        pygame.font.init()
        # High-legibility system fonts on Windows
        font_family = "Segoe UI, Arial, Trebuchet MS, sans-serif"

        # Clear typography hierarchy (bold where needed, clean and readable throughout)
        self.font_title = pygame.font.SysFont(font_family, 42, bold=True)
        self.font_large = pygame.font.SysFont(font_family, 28, bold=True)
        self.font_medium_bold = pygame.font.SysFont(font_family, 20, bold=True)
        self.font_medium = pygame.font.SysFont(font_family, 20, bold=False)
        self.font_small_bold = pygame.font.SysFont(font_family, 15, bold=True)
        self.font_small = pygame.font.SysFont(font_family, 15, bold=False)
        self.font_tiny = pygame.font.SysFont(font_family, 13, bold=False)

    def update(self, dt: float) -> None:
        """Update UI timers."""
        self.blink_timer += dt

    def draw_pixel_box(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        bg_color: Tuple[int, int, int, int] = (18, 22, 28, 215),
        border_color: Tuple[int, int, int] = COLOR_AMBER,
        border_width: int = 2
    ) -> None:
        """Draw a retro arcade military box with clean borders and corner notches."""
        box_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        box_surf.fill(bg_color)
        surface.blit(box_surf, (rect.x, rect.y))

        # Thin clean border
        pygame.draw.rect(surface, border_color, rect, border_width)

        # Corner rivets (subtle Metal Slug aesthetic)
        notch = 4
        x, y, w, h = rect.x, rect.y, rect.width, rect.height
        pygame.draw.rect(surface, COLOR_YELLOW, (x, y, notch, notch))
        pygame.draw.rect(surface, COLOR_YELLOW, (x + w - notch, y, notch, notch))
        pygame.draw.rect(surface, COLOR_YELLOW, (x, y + h - notch, notch, notch))
        pygame.draw.rect(surface, COLOR_YELLOW, (x + w - notch, y + h - notch, notch, notch))

    def draw_text(
        self,
        surface: pygame.Surface,
        font: pygame.font.Font,
        text: str,
        x: int,
        y: int,
        color: Tuple[int, int, int],
        align: str = "left",
        shadow: bool = True
    ) -> pygame.Rect:
        """Render readable arcade text with a subtle 1-pixel drop shadow instead of heavy bloat."""
        if shadow:
            shadow_surf = font.render(text, True, (12, 14, 18))
            rect_s = shadow_surf.get_rect()
            if align == "center":
                rect_s.center = (x + 1, y + 1)
            elif align == "right":
                rect_s.topright = (x + 1, y + 1)
            else:
                rect_s.topleft = (x + 1, y + 1)
            surface.blit(shadow_surf, rect_s)

        text_surf = font.render(text, True, color)
        rect = text_surf.get_rect()
        if align == "center":
            rect.center = (x, y)
        elif align == "right":
            rect.topright = (x, y)
        else:
            rect.topleft = (x, y)
        surface.blit(text_surf, rect)
        return rect

    # -------------------------------------------------------------
    # COMBAT HUD
    # -------------------------------------------------------------
    def render_hud(
        self,
        surface: pygame.Surface,
        score: int,
        armor: int,
        max_armor: int,
        current_weapon: str,
        ammo: int,
        combo: int,
        combo_timer: float,
        wave: int,
        boss=None,
        hand_detected: bool = False
    ) -> None:
        """Render combat HUD with clean typography and NO live webcam feed covering screen."""
        # 1. Top Left Panel: Armor Bar & Stage Info
        top_left_rect = pygame.Rect(20, 16, 290, 68)
        self.draw_pixel_box(surface, top_left_rect)

        self.draw_text(surface, self.font_small, f"MISSION 01 : STAGE {wave}", 34, 25, COLOR_KHAKI)

        # Armor Bar Label
        self.draw_text(surface, self.font_small_bold, "ARMOR", 34, 46, COLOR_YELLOW)
        bar_x = 95
        bar_y = 47
        bar_w = 175
        bar_h = 16

        pygame.draw.rect(surface, (35, 12, 12), (bar_x, bar_y, bar_w, bar_h))
        fill_ratio = max(0.0, min(1.0, armor / max_armor))
        fill_w = int(bar_w * fill_ratio)

        if fill_ratio > 0.5:
            bar_color = (60, 210, 50)
        elif fill_ratio > 0.25:
            bar_color = COLOR_AMBER
        else:
            bar_color = COLOR_RED

        if fill_w > 0:
            pygame.draw.rect(surface, bar_color, (bar_x, bar_y, fill_w, bar_h))
            for seg in range(1, 8):
                sx = bar_x + seg * (bar_w // 8)
                pygame.draw.line(surface, (20, 20, 20), (sx, bar_y), (sx, bar_y + bar_h), 1)

        pygame.draw.rect(surface, COLOR_KHAKI, (bar_x, bar_y, bar_w, bar_h), 1)
        self.draw_text(surface, self.font_tiny, f"{int(fill_ratio * 100)}%", bar_x + bar_w + 6, bar_y + 1, COLOR_WHITE)

        # 2. Top Center: Score Display
        self.draw_text(surface, self.font_small_bold, "SCORE", SCREEN_WIDTH // 2, 16, COLOR_KHAKI, align="center")
        score_str = f"{score:08d}"
        self.draw_text(surface, self.font_large, score_str, SCREEN_WIDTH // 2, 34, COLOR_YELLOW, align="center")

        # 3. Combo Display (Under Score)
        if combo >= 2:
            combo_color = COLOR_ORANGE if combo >= 5 else COLOR_AMBER
            mult = 1.0 + combo * 0.1
            self.draw_text(
                surface, self.font_medium_bold,
                f"★ {combo} HIT COMBO! (x{mult:.1f}) ★",
                SCREEN_WIDTH // 2, 64, combo_color, align="center"
            )

        # 4. Top Right: Hand Tracking Status Badge (Subtle, NO video feed)
        status_rect = pygame.Rect(SCREEN_WIDTH - 200, 16, 180, 32)
        self.draw_pixel_box(surface, status_rect, bg_color=(15, 20, 25, 190), border_color=COLOR_STEEL, border_width=1)
        if hand_detected:
            self.draw_text(surface, self.font_tiny, "● HAND TRACKING: ACTIVE", status_rect.centerx, status_rect.centery, (80, 230, 80), align="center")
        else:
            self.draw_text(surface, self.font_tiny, "⌨ KEYBOARD CONTROL", status_rect.centerx, status_rect.centery, COLOR_KHAKI, align="center")

        # 5. Bottom Left: Weapon Status Panel (Procedural, NO gunhandle.gif)
        weapon_rect = pygame.Rect(20, SCREEN_HEIGHT - 85, 270, 68)
        self.draw_pixel_box(surface, weapon_rect)

        w_info = WEAPONS_INFO.get(current_weapon, {})
        w_name = w_info.get("name", current_weapon)

        # Weapon badge accent color
        badge_color = COLOR_AMBER
        badge_tag = "MG"
        if current_weapon == WEAPON_MISSILE:
            badge_color = COLOR_ORANGE
            badge_tag = "MSL"
        elif current_weapon == WEAPON_LASER:
            badge_color = COLOR_CYAN
            badge_tag = "LSR"

        badge_box = pygame.Rect(weapon_rect.x + 12, weapon_rect.y + 14, 46, 40)
        pygame.draw.rect(surface, (25, 30, 38), badge_box)
        pygame.draw.rect(surface, badge_color, badge_box, 2)
        self.draw_text(surface, self.font_small_bold, badge_tag, badge_box.centerx, badge_box.centery, badge_color, align="center")

        # Weapon Name & Ammo
        self.draw_text(surface, self.font_medium_bold, w_name, weapon_rect.x + 68, weapon_rect.y + 14, COLOR_WHITE)
        ammo_str = "AMMO: ∞" if ammo == -1 else f"AMMO: {ammo:02d}"
        self.draw_text(surface, self.font_small, ammo_str, weapon_rect.x + 68, weapon_rect.y + 38, COLOR_KHAKI)

        # 6. Boss Bar (When Boss is Active)
        if boss and boss.alive:
            boss_bar_w = 540
            boss_bar_h = 20
            boss_bar_x = (SCREEN_WIDTH - boss_bar_w) // 2
            boss_bar_y = 80

            blink = int(self.blink_timer * 6) % 2 == 0
            warn_color = COLOR_RED if blink else COLOR_YELLOW
            self.draw_text(
                surface, self.font_small_bold,
                "⚠ TARGET: G-088 DREADNOUGHT ⚠",
                SCREEN_WIDTH // 2, boss_bar_y - 14, warn_color, align="center"
            )

            pygame.draw.rect(surface, (35, 10, 10), (boss_bar_x, boss_bar_y, boss_bar_w, boss_bar_h))
            b_ratio = max(0.0, min(1.0, boss.hp / boss.max_hp))
            b_fill = int(boss_bar_w * b_ratio)
            if b_fill > 0:
                pygame.draw.rect(surface, COLOR_CRIMSON, (boss_bar_x, boss_bar_y, b_fill, boss_bar_h))
                for s in range(0, b_fill, 24):
                    pygame.draw.line(surface, COLOR_ORANGE, (boss_bar_x + s, boss_bar_y), (boss_bar_x + s + 10, boss_bar_y + boss_bar_h), 2)
            pygame.draw.rect(surface, COLOR_AMBER, (boss_bar_x, boss_bar_y, boss_bar_w, boss_bar_h), 1)

    # -------------------------------------------------------------
    # MANDATORY BACKGROUND SELECTION SCREEN
    # -------------------------------------------------------------
    def render_background_selection(self, surface: pygame.Surface) -> None:
        """Render the Mandatory Background Selection Screen with clear typography."""
        surface.fill((12, 16, 20))

        header_rect = pygame.Rect(60, 30, SCREEN_WIDTH - 120, 68)
        self.draw_pixel_box(surface, header_rect, border_color=COLOR_AMBER)
        self.draw_text(
            surface, self.font_title,
            "SELECT MISSION AIRSPACE",
            SCREEN_WIDTH // 2, 64, COLOR_YELLOW, align="center"
        )

        bgs = self.bg_manager.available_backgrounds
        curr_idx = self.bg_manager.current_index

        thumb_w = 280
        thumb_h = 160
        spacing = 40
        total_w = len(bgs) * thumb_w + (len(bgs) - 1) * spacing
        start_x = max(80, (SCREEN_WIDTH - total_w) // 2)
        y_pos = 215

        for i, bg in enumerate(bgs):
            x_pos = start_x + i * (thumb_w + spacing)
            is_selected = (i == curr_idx)
            thumb_rect = pygame.Rect(x_pos, y_pos, thumb_w, thumb_h)

            if bg.thumbnail:
                scaled_thumb = pygame.transform.scale(bg.thumbnail, (thumb_w, thumb_h))
                surface.blit(scaled_thumb, (x_pos, y_pos))
            else:
                pygame.draw.rect(surface, (30, 40, 50), thumb_rect)

            if is_selected:
                blink = int(self.blink_timer * 5) % 2 == 0
                border_col = COLOR_YELLOW if blink else COLOR_ORANGE
                pygame.draw.rect(surface, border_col, thumb_rect, 4)

                self.draw_text(
                    surface, self.font_large, "▼",
                    x_pos + thumb_w // 2, y_pos - 24, COLOR_YELLOW, align="center"
                )

                indicator_rect = pygame.Rect(x_pos, y_pos + thumb_h + 10, thumb_w, 32)
                self.draw_pixel_box(surface, indicator_rect, bg_color=(190, 85, 10, 230), border_color=COLOR_YELLOW)
                self.draw_text(
                    surface, self.font_small_bold,
                    "[ SELECTED ]",
                    x_pos + thumb_w // 2, y_pos + thumb_h + 26, COLOR_WHITE, align="center"
                )
            else:
                pygame.draw.rect(surface, COLOR_STEEL, thumb_rect, 2)

            self.draw_text(
                surface, self.font_small_bold,
                bg.title,
                x_pos + thumb_w // 2, y_pos + thumb_h + (52 if is_selected else 18),
                COLOR_KHAKI, align="center"
            )

        # Instructions Footer
        footer_rect = pygame.Rect(100, SCREEN_HEIGHT - 120, SCREEN_WIDTH - 200, 75)
        self.draw_pixel_box(surface, footer_rect, border_color=COLOR_KHAKI)

        self.draw_text(
            surface, self.font_medium_bold,
            "◀ LEFT / RIGHT ARROWS ▶ : CHANGE SELECTION    |    ENTER / SPACE : CONFIRM",
            SCREEN_WIDTH // 2, SCREEN_HEIGHT - 96, COLOR_YELLOW, align="center"
        )
        self.draw_text(
            surface, self.font_small,
            "HAND GESTURE: POINT OR PINCH TO CONFIRM    |    ESC : MAIN MENU",
            SCREEN_WIDTH // 2, SCREEN_HEIGHT - 68, COLOR_WHITE, align="center"
        )

    # -------------------------------------------------------------
    # HAND CALIBRATION SCREEN
    # -------------------------------------------------------------
    def render_calibration(
        self,
        surface: pygame.Surface,
        webcam_surf: Optional[pygame.Surface],
        hand_detected: bool,
        is_pinching: bool,
        finger_count: int,
        pinch_dist: float
    ) -> None:
        """Render Calibration screen (live camera feed is appropriate here for setup)."""
        surface.fill((14, 18, 22))

        header_rect = pygame.Rect(80, 25, SCREEN_WIDTH - 160, 60)
        self.draw_pixel_box(surface, header_rect)
        self.draw_text(
            surface, self.font_title,
            "HAND CONTROL CALIBRATION",
            SCREEN_WIDTH // 2, 55, COLOR_AMBER, align="center"
        )

        # Left Column: Camera View
        cam_box = pygame.Rect(80, 105, 540, 410)
        self.draw_pixel_box(surface, cam_box, border_color=COLOR_YELLOW)

        if webcam_surf:
            cam_large = pygame.transform.scale(webcam_surf, (520, 390))
            surface.blit(cam_large, (90, 115))
        else:
            self.draw_text(
                surface, self.font_medium,
                "WEBCAM FEED NOT DETECTED (KEYBOARD READY)",
                cam_box.centerx, cam_box.centery, COLOR_RED, align="center"
            )

        # Right Column: Diagnostics
        diag_box = pygame.Rect(650, 105, 550, 410)
        self.draw_pixel_box(surface, diag_box)

        self.draw_text(surface, self.font_large, "SYSTEM STATUS", 680, 130, COLOR_YELLOW)

        det_color = (60, 230, 60) if hand_detected else COLOR_RED
        det_text = "HAND DETECTED  ✓" if hand_detected else "SEARCHING FOR HAND... ✗"
        self.draw_text(surface, self.font_medium_bold, det_text, 680, 175, det_color)

        pinch_color = (60, 230, 60) if is_pinching else COLOR_ORANGE
        pinch_text = "FIRE TRIGGER: [ ACTIVE! ]" if is_pinching else "FIRE TRIGGER: [ READY (PINCH) ]"
        self.draw_text(surface, self.font_medium_bold, pinch_text, 680, 220, pinch_color)
        self.draw_text(surface, self.font_small, f"Pinch Distance: {pinch_dist:.3f}", 680, 250, COLOR_GRAY)

        weapon_names = {1: "1 FINGER -> VULCAN CANNON", 2: "2 FINGERS -> HOMING MISSILES", 3: "3 FINGERS -> PLASMA BEAM"}
        w_text = weapon_names.get(finger_count, "OPEN PALM")
        self.draw_text(surface, self.font_medium_bold, f"GESTURE: {w_text}", 680, 290, COLOR_AMBER)

        inst_y = 345
        self.draw_text(surface, self.font_small, "• Move hand across camera to steer aircraft", 680, inst_y, COLOR_WHITE)
        self.draw_text(surface, self.font_small, "• Pinch Thumb + Index finger to FIRE weapons", 680, inst_y + 24, COLOR_WHITE)
        self.draw_text(surface, self.font_small, "• Raise 1, 2, or 3 fingers to switch loadout", 680, inst_y + 48, COLOR_WHITE)
        self.draw_text(surface, self.font_small, "• Keyboard fallback always available (WASD/SPACE)", 680, inst_y + 72, COLOR_KHAKI)

        btn_rect = pygame.Rect(SCREEN_WIDTH // 2 - 180, SCREEN_HEIGHT - 100, 360, 55)
        self.draw_pixel_box(surface, btn_rect, bg_color=(170, 75, 10, 230), border_color=COLOR_YELLOW)
        self.draw_text(
            surface, self.font_large,
            "▶ START MISSION [SPACE]",
            SCREEN_WIDTH // 2, SCREEN_HEIGHT - 72, COLOR_WHITE, align="center"
        )

    # -------------------------------------------------------------
    # MAIN MENU SCREEN
    # -------------------------------------------------------------
    def render_main_menu(
        self,
        surface: pygame.Surface,
        selected_index: int,
        menu_items: List[str],
        webcam_connected: bool,
        hand_detected: bool
    ) -> None:
        """Render the Main Menu with clean, legible arcade styling."""
        dim = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        dim.fill((10, 14, 18, 180))
        surface.blit(dim, (0, 0))

        # Title Banner
        title_rect = pygame.Rect(SCREEN_WIDTH // 2 - 360, 65, 720, 115)
        self.draw_pixel_box(surface, title_rect, bg_color=(20, 26, 30, 240), border_color=COLOR_YELLOW, border_width=3)

        self.draw_text(
            surface, self.font_title,
            "AIR STRIKE : SLUG WING",
            SCREEN_WIDTH // 2, 105, COLOR_YELLOW, align="center"
        )
        self.draw_text(
            surface, self.font_small,
            "- HAND-CONTROLLED RETRO MILITARY ARCADE -",
            SCREEN_WIDTH // 2, 148, COLOR_KHAKI, align="center"
        )

        # Menu List
        menu_y = 240
        for i, item in enumerate(menu_items):
            is_sel = (i == selected_index)
            box_w = 380
            box_h = 48
            box_x = (SCREEN_WIDTH - box_w) // 2
            curr_y = menu_y + i * 60
            box_rect = pygame.Rect(box_x, curr_y, box_w, box_h)

            if is_sel:
                blink = int(self.blink_timer * 6) % 2 == 0
                bg_col = (170, 65, 10, 240) if blink else (130, 48, 10, 240)
                self.draw_pixel_box(surface, box_rect, bg_color=bg_col, border_color=COLOR_YELLOW, border_width=2)
                self.draw_text(
                    surface, self.font_medium_bold,
                    f"▶  {item}",
                    SCREEN_WIDTH // 2, curr_y + 24, COLOR_YELLOW, align="center"
                )
            else:
                self.draw_pixel_box(surface, box_rect, bg_color=(24, 30, 36, 190), border_color=COLOR_STEEL, border_width=1)
                self.draw_text(
                    surface, self.font_medium,
                    item,
                    SCREEN_WIDTH // 2, curr_y + 24, COLOR_WHITE, align="center"
                )

        # Hardware Status Panel Bottom
        status_rect = pygame.Rect(SCREEN_WIDTH // 2 - 280, SCREEN_HEIGHT - 85, 560, 46)
        self.draw_pixel_box(surface, status_rect)

        cam_str = "WEBCAM: READY ✓" if webcam_connected else "WEBCAM: OFF (KEYBOARD READY)"
        cam_col = (80, 240, 80) if webcam_connected else COLOR_ORANGE
        self.draw_text(surface, self.font_small, cam_str, SCREEN_WIDTH // 2 - 140, SCREEN_HEIGHT - 62, cam_col, align="center")

        hand_str = "HAND TRACK: ACTIVE" if hand_detected else "STANDBY"
        hand_col = (80, 240, 80) if hand_detected else COLOR_KHAKI
        self.draw_text(surface, self.font_small, hand_str, SCREEN_WIDTH // 2 + 140, SCREEN_HEIGHT - 62, hand_col, align="center")

    # -------------------------------------------------------------
    # PAUSE MENU
    # -------------------------------------------------------------
    def render_pause_menu(self, surface: pygame.Surface, selected_index: int, options: List[str]) -> None:
        """Render the Pause overlay with readable options."""
        dim = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        dim.fill((10, 12, 16, 210))
        surface.blit(dim, (0, 0))

        title_box = pygame.Rect(SCREEN_WIDTH // 2 - 220, 140, 440, 60)
        self.draw_pixel_box(surface, title_box, border_color=COLOR_AMBER)
        self.draw_text(
            surface, self.font_title,
            "MISSION PAUSED",
            SCREEN_WIDTH // 2, 170, COLOR_YELLOW, align="center"
        )

        for i, opt in enumerate(options):
            is_sel = (i == selected_index)
            y = 250 + i * 58
            rect = pygame.Rect(SCREEN_WIDTH // 2 - 180, y, 360, 44)

            if is_sel:
                self.draw_pixel_box(surface, rect, bg_color=(150, 55, 10, 230), border_color=COLOR_YELLOW)
                self.draw_text(surface, self.font_medium_bold, f"▶  {opt}", SCREEN_WIDTH // 2, y + 22, COLOR_YELLOW, align="center")
            else:
                self.draw_pixel_box(surface, rect, border_color=COLOR_STEEL)
                self.draw_text(surface, self.font_medium, opt, SCREEN_WIDTH // 2, y + 22, COLOR_WHITE, align="center")

    # -------------------------------------------------------------
    # GAME OVER SCREEN
    # -------------------------------------------------------------
    def render_game_over(self, surface: pygame.Surface, final_score: int, max_combo: int) -> None:
        """Render Mission Failed screen returning cleanly to the Main Menu."""
        dim = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        dim.fill((22, 6, 6, 230))
        surface.blit(dim, (0, 0))

        box = pygame.Rect(SCREEN_WIDTH // 2 - 280, 130, 560, 440)
        self.draw_pixel_box(surface, box, bg_color=(20, 10, 10, 240), border_color=COLOR_RED, border_width=3)

        self.draw_text(surface, self.font_title, "MISSION FAILED", SCREEN_WIDTH // 2, 185, COLOR_RED, align="center")
        self.draw_text(surface, self.font_large, f"FINAL SCORE : {final_score:08d}", SCREEN_WIDTH // 2, 260, COLOR_YELLOW, align="center")
        self.draw_text(surface, self.font_medium, f"MAX COMBO : {max_combo} HITS", SCREEN_WIDTH // 2, 310, COLOR_ORANGE, align="center")

        # Action prompts
        btn_menu = pygame.Rect(SCREEN_WIDTH // 2 - 200, 370, 400, 46)
        self.draw_pixel_box(surface, btn_menu, bg_color=(150, 50, 10, 220), border_color=COLOR_YELLOW)
        self.draw_text(surface, self.font_medium_bold, "▶  RETURN TO MAIN MENU  [ENTER / SPACE]", SCREEN_WIDTH // 2, 393, COLOR_WHITE, align="center")

        btn_retry = pygame.Rect(SCREEN_WIDTH // 2 - 160, 435, 320, 40)
        self.draw_pixel_box(surface, btn_retry, bg_color=(30, 20, 20, 200), border_color=COLOR_STEEL)
        self.draw_text(surface, self.font_small_bold, "[ R ] : QUICK RETRY", SCREEN_WIDTH // 2, 455, COLOR_KHAKI, align="center")

        self.draw_text(surface, self.font_tiny, "Auto-returning to Main Menu...", SCREEN_WIDTH // 2, 510, COLOR_GRAY, align="center")

    # -------------------------------------------------------------
    # VICTORY SCREEN
    # -------------------------------------------------------------
    def render_victory(self, surface: pygame.Surface, final_score: int, max_combo: int) -> None:
        """Render Mission Accomplished screen."""
        dim = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        dim.fill((8, 18, 10, 230))
        surface.blit(dim, (0, 0))

        box = pygame.Rect(SCREEN_WIDTH // 2 - 320, 110, 640, 480)
        self.draw_pixel_box(surface, box, bg_color=(14, 24, 18, 240), border_color=COLOR_YELLOW, border_width=3)

        self.draw_text(surface, self.font_title, "MISSION ACCOMPLISHED!", SCREEN_WIDTH // 2, 165, COLOR_YELLOW, align="center")
        self.draw_text(surface, self.font_small, "AIRSPACE SECURED - ENEMY FORCES ELIMINATED", SCREEN_WIDTH // 2, 215, COLOR_KHAKI, align="center")

        self.draw_text(surface, self.font_large, f"TOTAL SCORE : {final_score:08d}", SCREEN_WIDTH // 2, 280, COLOR_WHITE, align="center")
        self.draw_text(surface, self.font_medium, f"HIGHEST COMBO : {max_combo} HITS", SCREEN_WIDTH // 2, 330, COLOR_AMBER, align="center")
        self.draw_text(surface, self.font_large, "MISSION RATING : RANK S", SCREEN_WIDTH // 2, 385, (80, 240, 80), align="center")

        btn_play = pygame.Rect(SCREEN_WIDTH // 2 - 180, 440, 360, 44)
        self.draw_pixel_box(surface, btn_play, bg_color=(150, 70, 10, 230), border_color=COLOR_YELLOW)
        self.draw_text(surface, self.font_medium_bold, "[ ENTER / SPACE ] : PLAY AGAIN", SCREEN_WIDTH // 2, 462, COLOR_WHITE, align="center")

        self.draw_text(surface, self.font_small, "[ ESC ] : RETURN TO MENU", SCREEN_WIDTH // 2, 515, COLOR_KHAKI, align="center")

    # -------------------------------------------------------------
    # SETTINGS SCREEN
    # -------------------------------------------------------------
    def render_settings(self, surface: pygame.Surface, selected_idx: int) -> None:
        """Render settings menu with clean typography."""
        surface.fill((12, 16, 20))

        header = pygame.Rect(SCREEN_WIDTH // 2 - 220, 30, 440, 58)
        self.draw_pixel_box(surface, header)
        self.draw_text(surface, self.font_title, "SYSTEM SETTINGS", SCREEN_WIDTH // 2, 59, COLOR_YELLOW, align="center")

        items = [
            ("MASTER VOLUME", f"{int(self.settings.get('master_volume', 0.8) * 100)}%"),
            ("SFX VOLUME", f"{int(self.settings.get('sfx_volume', 0.85) * 100)}%"),
            ("MUSIC VOLUME", f"{int(self.settings.get('music_volume', 0.65) * 100)}%"),
            ("HAND SENSITIVITY", f"{self.settings.get('hand_sensitivity', 1.25):.2f}x"),
            ("HAND SMOOTHING", f"{self.settings.get('hand_smoothing', 0.65):.2f}"),
            ("SCREEN SHAKE", "ON" if self.settings.get("screen_shake_enabled", True) else "OFF"),
        ]

        start_y = 135
        for i, (label, val_str) in enumerate(items):
            is_sel = (i == selected_idx)
            y = start_y + i * 58
            row_rect = pygame.Rect(SCREEN_WIDTH // 2 - 280, y, 560, 44)

            if is_sel:
                self.draw_pixel_box(surface, row_rect, bg_color=(140, 55, 10, 230), border_color=COLOR_YELLOW)
                self.draw_text(surface, self.font_medium_bold, f"▶ {label}", row_rect.x + 18, y + 22, COLOR_YELLOW)
                self.draw_text(surface, self.font_medium_bold, f"◀ {val_str} ▶", row_rect.right - 18, y + 22, COLOR_WHITE, align="right")
            else:
                self.draw_pixel_box(surface, row_rect, border_color=COLOR_STEEL)
                self.draw_text(surface, self.font_medium, label, row_rect.x + 18, y + 22, COLOR_WHITE)
                self.draw_text(surface, self.font_medium, val_str, row_rect.right - 18, y + 22, COLOR_KHAKI, align="right")

        self.draw_text(
            surface, self.font_small,
            "UP / DOWN : Navigate   |   LEFT / RIGHT : Adjust Value   |   ESC : Back to Menu",
            SCREEN_WIDTH // 2, SCREEN_HEIGHT - 65, COLOR_YELLOW, align="center"
        )
