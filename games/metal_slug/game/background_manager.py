"""
Background Manager for the Retro Arcade Aircraft Game.
Handles automatic discovery of all available backgrounds, thumbnail generation,
selected background switching, and smooth parallax side-scrolling during combat.
"""

from pathlib import Path
from typing import List, Dict, Optional, Tuple
import random
import pygame
from config import BASE_DIR, SCREEN_WIDTH, SCREEN_HEIGHT

SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

class BackgroundInfo:
    """Stores metadata and cached surfaces for a selectable background."""
    def __init__(self, filename: str, path: Path, title: str):
        self.filename = filename
        self.path = path
        self.title = title
        self.surface: Optional[pygame.Surface] = None
        self.thumbnail: Optional[pygame.Surface] = None

class BackgroundManager:
    """Discovers, manages, and renders scrolling gameplay backgrounds."""
    def __init__(self, settings: dict):
        self.settings = settings
        self.available_backgrounds: List[BackgroundInfo] = []
        self.current_index: int = 0
        self.current_background: Optional[BackgroundInfo] = None

        # Parallax scrolling variables
        self.scroll_x: float = 0.0
        self.scroll_speed: float = 90.0  # pixels per second horizontal drift
        self.clouds: List[Dict[str, float]] = []

        self._discover_backgrounds()
        self._init_selection()
        self._init_parallax_clouds()

    def _discover_backgrounds(self) -> None:
        """Scan project root and asset directories for background images."""
        search_dirs = [
            BASE_DIR,
            BASE_DIR / "assets" / "backgrounds",
            BASE_DIR / "assets",
        ]

        found_files: Dict[str, Path] = {}

        for directory in search_dirs:
            if directory.exists() and directory.is_dir():
                for item in sorted(directory.iterdir()):
                    if item.is_file() and item.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS:
                        name_lower = item.name.lower()
                        # Match backgrounds by filename pattern or presence in backgrounds dir
                        if "background" in name_lower or "bg" in name_lower or directory.name == "backgrounds":
                            if item.name not in found_files:
                                found_files[item.name] = item

        # Also fallback if no background files matched pattern
        if not found_files:
            for item in sorted(BASE_DIR.iterdir()):
                if item.is_file() and item.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS:
                    found_files[item.name] = item

        for filename, path in found_files.items():
            clean_title = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").upper()
            info = BackgroundInfo(filename, path, clean_title)
            # Create thumbnail
            info.thumbnail = self._create_thumbnail(path)
            self.available_backgrounds.append(info)

        # Fallback procedural background if none found
        if not self.available_backgrounds:
            procedural_surf = self._create_procedural_bg()
            info = BackgroundInfo("default_grid.png", BASE_DIR / "default.png", "DESERT OPERATION")
            info.surface = procedural_surf
            info.thumbnail = pygame.transform.scale(procedural_surf, (240, 135))
            self.available_backgrounds.append(info)

    def _create_thumbnail(self, path: Path) -> pygame.Surface:
        """Create a scaled thumbnail for the background selection menu."""
        try:
            surf = pygame.image.load(str(path)).convert()
            return pygame.transform.scale(surf, (240, 135))
        except Exception as e:
            print(f"[BG_MANAGER] Error creating thumbnail for {path}: {e}")
            surf = pygame.Surface((240, 135))
            surf.fill((40, 50, 40))
            return surf

    def _init_selection(self) -> None:
        """Set the initially selected background from settings or default to index 0."""
        target_name = self.settings.get("selected_background", "")
        selected_idx = 0
        for idx, bg in enumerate(self.available_backgrounds):
            if bg.filename.lower() == target_name.lower():
                selected_idx = idx
                break

        self.current_index = selected_idx
        self.set_background_by_index(self.current_index)

    def _init_parallax_clouds(self) -> None:
        """Generate subtle distant cloud layers for enhanced sense of forward flight."""
        import random
        self.clouds.clear()
        for i in range(8):
            self.clouds.append({
                "x": random.uniform(0, SCREEN_WIDTH),
                "y": random.uniform(20, SCREEN_HEIGHT * 0.45),
                "width": random.uniform(160, 340),
                "height": random.uniform(40, 90),
                "speed": random.uniform(140, 220),
                "alpha": random.randint(30, 80)
            })

    def set_background(self, filename: str) -> bool:
        """Set active gameplay background by filename."""
        for idx, bg in enumerate(self.available_backgrounds):
            if bg.filename.lower() == filename.lower():
                return self.set_background_by_index(idx)
        return False

    def set_background_by_index(self, index: int) -> bool:
        """Select background by index, load high-res surface, and persist setting."""
        if 0 <= index < len(self.available_backgrounds):
            self.current_index = index
            bg_info = self.available_backgrounds[index]

            if bg_info.surface is None:
                try:
                    loaded = pygame.image.load(str(bg_info.path)).convert()
                    # Scale to match screen height while maintaining aspect ratio
                    aspect = loaded.get_width() / loaded.get_height()
                    new_height = SCREEN_HEIGHT
                    new_width = max(SCREEN_WIDTH, int(new_height * aspect))
                    bg_info.surface = pygame.transform.scale(loaded, (new_width, new_height))
                except Exception as e:
                    print(f"[BG_MANAGER] Error loading background {bg_info.path}: {e}")
                    bg_info.surface = self._create_procedural_bg()

            self.current_background = bg_info
            self.settings["selected_background"] = bg_info.filename
            return True
        return False

    def next_background(self) -> None:
        """Cycle to next background."""
        new_idx = (self.current_index + 1) % len(self.available_backgrounds)
        self.set_background_by_index(new_idx)

    def prev_background(self) -> None:
        """Cycle to previous background."""
        new_idx = (self.current_index - 1) % len(self.available_backgrounds)
        self.set_background_by_index(new_idx)

    def get_current_background(self) -> BackgroundInfo:
        """Return currently active background."""
        if not self.current_background and self.available_backgrounds:
            self.set_background_by_index(0)
        return self.current_background

    def update(self, dt: float, speed_multiplier: float = 1.0) -> None:
        """Advance horizontal scroll offset and cloud positions."""
        bg = self.get_current_background()
        if bg and bg.surface:
            bg_w = bg.surface.get_width()
            self.scroll_x = (self.scroll_x + self.scroll_speed * speed_multiplier * dt) % bg_w

        # Update clouds
        for c in self.clouds:
            c["x"] -= c["speed"] * speed_multiplier * dt
            if c["x"] + c["width"] < 0:
                c["x"] = SCREEN_WIDTH + 50
                import random
                c["y"] = random.uniform(20, SCREEN_HEIGHT * 0.45)

    def render(self, surface: pygame.Surface) -> None:
        """Render seamless scrolling background and parallax clouds."""
        bg = self.get_current_background()
        if not bg or not bg.surface:
            surface.fill((20, 24, 30))
            return

        bg_surf = bg.surface
        bg_w = bg_surf.get_width()
        x_offset = int(self.scroll_x)

        # Draw main background tiled horizontally to cover full 1280 width
        # Flying left to right means scenery scrolls to the left (-x_offset)
        surface.blit(bg_surf, (-x_offset, 0))
        if bg_w - x_offset < SCREEN_WIDTH:
            surface.blit(bg_surf, (bg_w - x_offset, 0))
        if 2 * bg_w - x_offset < SCREEN_WIDTH:
            surface.blit(bg_surf, (2 * bg_w - x_offset, 0))

        # Render subtle parallax clouds / atmospheric dust
        for c in self.clouds:
            cloud_surf = pygame.Surface((int(c["width"]), int(c["height"])), pygame.SRCALPHA)
            pygame.draw.ellipse(cloud_surf, (240, 240, 255, int(c["alpha"])), cloud_surf.get_rect())
            surface.blit(cloud_surf, (int(c["x"]), int(c["y"])))

    def _create_procedural_bg(self) -> pygame.Surface:
        """Create fallback military desert battleground."""
        surf = pygame.Surface((SCREEN_WIDTH * 2, SCREEN_HEIGHT))
        # Sky gradient
        for y in range(int(SCREEN_HEIGHT * 0.6)):
            ratio = y / (SCREEN_HEIGHT * 0.6)
            r = int(120 + 80 * ratio)
            g = int(170 + 50 * ratio)
            b = int(210 - 20 * ratio)
            pygame.draw.line(surf, (r, g, b), (0, y), (surf.get_width(), y))
        # Ground
        for y in range(int(SCREEN_HEIGHT * 0.6), SCREEN_HEIGHT):
            ratio = (y - SCREEN_HEIGHT * 0.6) / (SCREEN_HEIGHT * 0.4)
            r = int(180 - 40 * ratio)
            g = int(140 - 40 * ratio)
            b = int(70 - 20 * ratio)
            pygame.draw.line(surf, (r, g, b), (0, y), (surf.get_width(), y))
        return surf
