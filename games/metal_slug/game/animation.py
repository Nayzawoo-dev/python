"""
Animation and Sprite Loading System using Pillow and Pygame.
Extracts GIF frames, handles alpha transparency, scales, caches, and handles frame timing.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple, Dict, Optional
import pygame
from PIL import Image, ImageSequence

class AnimatedSprite:
    """Manages an animated sequence of Pygame surfaces with frame timing."""
    def __init__(self, frames: List[pygame.Surface], frame_durations: List[float], loop: bool = True):
        self.frames = frames if frames else [pygame.Surface((32, 32), pygame.SRCALPHA)]
        self.frame_durations = frame_durations if frame_durations else [0.1]
        self.loop = loop
        self.current_frame_index = 0
        self.time_accumulator = 0.0
        self.finished = False

    def update(self, dt: float) -> None:
        """Update the animation frame based on delta time."""
        if self.finished:
            return

        self.time_accumulator += dt
        current_duration = self.frame_durations[self.current_frame_index]
        if current_duration <= 0.001:
            current_duration = 0.1  # fallback default duration

        while self.time_accumulator >= current_duration:
            self.time_accumulator -= current_duration
            if self.current_frame_index + 1 < len(self.frames):
                self.current_frame_index += 1
            elif self.loop:
                self.current_frame_index = 0
            else:
                self.finished = True
                break
            current_duration = self.frame_durations[self.current_frame_index]
            if current_duration <= 0.001:
                current_duration = 0.1

    def get_current_frame(self) -> pygame.Surface:
        """Return the current frame surface."""
        return self.frames[self.current_frame_index]

    def reset(self) -> None:
        """Reset animation to the beginning."""
        self.current_frame_index = 0
        self.time_accumulator = 0.0
        self.finished = False

    def clone(self) -> 'AnimatedSprite':
        """Create a new instance sharing the frame surfaces."""
        return AnimatedSprite(self.frames, self.frame_durations, self.loop)


class AssetLoader:
    """Singleton/Static helper to load, scale, and cache sprites and GIFs."""
    _cache: Dict[Tuple[str, float, bool, bool], AnimatedSprite] = {}
    _image_cache: Dict[Tuple[str, Tuple[int, int]], pygame.Surface] = {}

    @classmethod
    def load_gif(
        cls,
        path: Path | str,
        scale: float = 1.0,
        flip_x: bool = False,
        flip_y: bool = False,
        default_frame_duration: float = 0.08,
        loop: bool = True
    ) -> AnimatedSprite:
        """Load an animated GIF with Pillow and convert to Pygame surfaces."""
        path_str = str(Path(path).resolve())
        cache_key = (path_str, scale, flip_x, flip_y, loop)

        if cache_key in cls._cache:
            return cls._cache[cache_key].clone()

        if not Path(path_str).exists():
            print(f"[ASSETS] Warning: GIF not found at '{path_str}', generating procedural placeholder.")
            placeholder = cls._create_placeholder_surface(int(64 * scale), int(64 * scale))
            anim = AnimatedSprite([placeholder], [0.1], loop=loop)
            cls._cache[cache_key] = anim
            return anim.clone()

        frames = []
        durations = []

        try:
            with Image.open(path_str) as pil_img:
                for frame in ImageSequence.Iterator(pil_img):
                    # Convert to RGBA
                    frame_rgba = frame.convert("RGBA")
                    raw_data = frame_rgba.tobytes()
                    size = frame_rgba.size

                    # Create pygame surface
                    surf = pygame.image.fromstring(raw_data, size, "RGBA")

                    # Apply scaling
                    if scale != 1.0:
                        new_w = max(1, int(size[0] * scale))
                        new_h = max(1, int(size[1] * scale))
                        surf = pygame.transform.scale(surf, (new_w, new_h))

                    # Apply flipping
                    if flip_x or flip_y:
                        surf = pygame.transform.flip(surf, flip_x, flip_y)

                    frames.append(surf)

                    # Duration in milliseconds converted to seconds
                    duration_ms = frame.info.get("duration", 0)
                    if duration_ms <= 10:
                        duration_ms = int(default_frame_duration * 1000)
                    durations.append(duration_ms / 1000.0)

            if not frames:
                raise ValueError("No frames extracted from GIF")

            anim = AnimatedSprite(frames, durations, loop=loop)
            cls._cache[cache_key] = anim
            return anim.clone()

        except Exception as e:
            print(f"[ASSETS] Error loading GIF '{path_str}': {e}. Using procedural placeholder.")
            placeholder = cls._create_placeholder_surface(int(64 * scale), int(64 * scale))
            anim = AnimatedSprite([placeholder], [0.1], loop=loop)
            cls._cache[cache_key] = anim
            return anim.clone()

    @classmethod
    def load_image(
        cls,
        path: Path | str,
        target_size: Optional[Tuple[int, int]] = None
    ) -> pygame.Surface:
        """Load a static image file with caching and optional resizing."""
        path_str = str(Path(path).resolve())
        cache_key = (path_str, target_size if target_size else (0, 0))

        if cache_key in cls._image_cache:
            return cls._image_cache[cache_key].copy()

        if not Path(path_str).exists():
            print(f"[ASSETS] Warning: Image not found at '{path_str}', generating placeholder.")
            w, h = target_size if target_size else (128, 128)
            surf = cls._create_placeholder_surface(w, h)
            cls._image_cache[cache_key] = surf
            return surf.copy()

        try:
            surf = pygame.image.load(path_str).convert_alpha()
            if target_size:
                surf = pygame.transform.scale(surf, target_size)
            cls._image_cache[cache_key] = surf
            return surf.copy()
        except Exception as e:
            print(f"[ASSETS] Error loading image '{path_str}': {e}")
            w, h = target_size if target_size else (128, 128)
            surf = cls._create_placeholder_surface(w, h)
            cls._image_cache[cache_key] = surf
            return surf.copy()

    @staticmethod
    def _create_placeholder_surface(width: int, height: int) -> pygame.Surface:
        """Create a retro styled military aircraft placeholder surface."""
        surf = pygame.Surface((width, height), pygame.SRCALPHA)
        # Military green jet silhouette
        color = (60, 90, 50, 240)
        cockpit = (0, 220, 255, 255)
        # Draw retro aircraft polygon
        w, h = width, height
        pts = [
            (w * 0.9, h * 0.5),
            (w * 0.4, h * 0.2),
            (w * 0.1, h * 0.1),
            (w * 0.2, h * 0.4),
            (0, h * 0.45),
            (0, h * 0.55),
            (w * 0.2, h * 0.6),
            (w * 0.1, h * 0.9),
            (w * 0.4, h * 0.8),
        ]
        pygame.draw.polygon(surf, color, pts)
        pygame.draw.polygon(surf, (200, 220, 100), pts, 2)
        # Cockpit window
        pygame.draw.ellipse(surf, cockpit, (int(w * 0.5), int(h * 0.4), int(w * 0.2), int(h * 0.2)))
        return surf
