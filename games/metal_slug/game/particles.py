"""
Arcade Particle and Visual Effects System.
Handles explosions, smoke trails, sparks, plasma arcs, floating scores, and screen shake.
"""

from typing import List, Tuple, Optional
import random
import math
import pygame
from config import COLOR_AMBER, COLOR_ORANGE, COLOR_RED, COLOR_YELLOW, COLOR_WHITE, COLOR_CYAN

class Particle:
    """Base particle with velocity, lifespan, and fading alpha."""
    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        radius: float,
        color: Tuple[int, int, int],
        lifetime: float,
        decay_rate: float = 1.0,
        drag: float = 0.98
    ):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.radius = radius
        self.initial_radius = radius
        self.color = color
        self.lifetime = lifetime
        self.age = 0.0
        self.decay_rate = decay_rate
        self.drag = drag
        self.alive = True

    def update(self, dt: float) -> None:
        self.age += dt
        if self.age >= self.lifetime:
            self.alive = False
            return

        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= self.drag
        self.vy *= self.drag

        # Shrink over lifetime
        progress = self.age / self.lifetime
        self.radius = max(0.5, self.initial_radius * (1.0 - progress * self.decay_rate))

    def render(self, surface: pygame.Surface) -> None:
        if not self.alive:
            return
        progress = self.age / self.lifetime
        alpha = int(255 * (1.0 - progress))
        if alpha <= 0 or self.radius < 0.5:
            return

        # Draw fast antialiased/filled circle with alpha
        size = int(self.radius * 2) + 2
        part_surf = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(part_surf, (*self.color, alpha), (size // 2, size // 2), int(self.radius))
        surface.blit(part_surf, (int(self.x - size // 2), int(self.y - size // 2)))


class SmokePuff(Particle):
    """Smoke puff that expands and drifts backward from missile exhaust."""
    def __init__(self, x: float, y: float, vx: float, vy: float):
        super().__init__(
            x, y, vx, vy,
            radius=random.uniform(4.0, 9.0),
            color=(180, 180, 190),
            lifetime=random.uniform(0.4, 0.75),
            decay_rate=-0.8,  # expands
            drag=0.92
        )


class FloatingText:
    """Floating score / combo popup text that floats upward and fades."""
    def __init__(self, x: float, y: float, text: str, color: Tuple[int, int, int], size: int = 22, duration: float = 0.85):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.duration = duration
        self.age = 0.0
        self.alive = True
        self.vy = -55.0  # upward speed
        self.font = pygame.font.SysFont("Segoe UI, Arial, Trebuchet MS, sans-serif", size, bold=True)

    def update(self, dt: float) -> None:
        self.age += dt
        if self.age >= self.duration:
            self.alive = False
            return
        self.y += self.vy * dt

    def render(self, surface: pygame.Surface) -> None:
        if not self.alive:
            return
        progress = self.age / self.duration
        alpha = int(255 * (1.0 - progress * progress))

        # Render clean drop shadow and text
        shadow = self.font.render(self.text, True, (10, 12, 16))
        shadow.set_alpha(alpha)
        text_surf = self.font.render(self.text, True, self.color)
        text_surf.set_alpha(alpha)

        px, py = int(self.x), int(self.y)
        surface.blit(shadow, (px + 1, py + 1))
        surface.blit(text_surf, (px, py))


class ParticleSystem:
    """Manager for particles, floating texts, and screen shake."""
    def __init__(self):
        self.particles: List[Particle] = []
        self.floating_texts: List[FloatingText] = []

        # Screen shake
        self.shake_magnitude = 0.0
        self.shake_duration = 0.0
        self.shake_timer = 0.0
        self.shake_offset = (0, 0)

    def update(self, dt: float) -> None:
        """Update particles, text objects, and shake effect."""
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.alive]

        for ft in self.floating_texts:
            ft.update(dt)
        self.floating_texts = [ft for ft in self.floating_texts if ft.alive]

        # Screen shake timer
        if self.shake_timer > 0:
            self.shake_timer -= dt
            decay = self.shake_timer / max(0.001, self.shake_duration)
            mag = self.shake_magnitude * decay
            self.shake_offset = (
                int(random.uniform(-mag, mag)),
                int(random.uniform(-mag, mag))
            )
        else:
            self.shake_offset = (0, 0)

    def render(self, surface: pygame.Surface) -> None:
        """Render all active visual effects."""
        for p in self.particles:
            p.render(surface)
        for ft in self.floating_texts:
            ft.render(surface)

    def trigger_shake(self, magnitude: float = 6.0, duration: float = 0.3) -> None:
        """Trigger camera screen shake."""
        self.shake_magnitude = max(self.shake_magnitude, magnitude)
        self.shake_duration = max(self.shake_duration, duration)
        self.shake_timer = self.shake_duration

    def get_shake_offset(self) -> Tuple[int, int]:
        return self.shake_offset

    def add_floating_text(self, x: float, y: float, text: str, color: Tuple[int, int, int] = COLOR_YELLOW, size: int = 22) -> None:
        self.floating_texts.append(FloatingText(x, y, text, color, size))

    def create_explosion(self, x: float, y: float, size_multiplier: float = 1.0) -> None:
        """Create intense Metal Slug style multi-layered explosion."""
        count = int(28 * size_multiplier)
        # Fireball core
        colors = [COLOR_YELLOW, COLOR_AMBER, COLOR_ORANGE, COLOR_RED, (60, 60, 60)]
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(50, 320) * size_multiplier
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            radius = random.uniform(6.0, 18.0) * size_multiplier
            color = random.choice(colors)
            lifetime = random.uniform(0.35, 0.75)
            self.particles.append(Particle(x, y, vx, vy, radius, color, lifetime, decay_rate=0.7))

        # Debris sparks
        for _ in range(int(15 * size_multiplier)):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(180, 480) * size_multiplier
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            self.particles.append(Particle(x, y, vx, vy, radius=2.5, color=COLOR_WHITE, lifetime=0.3, drag=0.94))

        self.trigger_shake(magnitude=5.0 * size_multiplier, duration=0.25 * size_multiplier)

    def create_missile_smoke(self, x: float, y: float) -> None:
        """Add smoke puff behind missile rocket exhaust."""
        vx = random.uniform(-60, -20)
        vy = random.uniform(-20, 20)
        self.particles.append(SmokePuff(x, y, vx, vy))

    def create_hit_sparks(self, x: float, y: float, color: Tuple[int, int, int] = COLOR_AMBER) -> None:
        """Create bright directional sparks on bullet impact."""
        for _ in range(7):
            angle = random.uniform(math.pi * 0.7, math.pi * 1.3)
            speed = random.uniform(120, 260)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            self.particles.append(Particle(x, y, vx, vy, radius=2.0, color=color, lifetime=0.2, drag=0.9))

    def create_laser_impact(self, x: float, y: float) -> None:
        """Create energetic cyan plasma spark rings."""
        for _ in range(10):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(100, 300)
            self.particles.append(Particle(x, y, math.cos(angle)*speed, math.sin(angle)*speed, radius=3.0, color=COLOR_CYAN, lifetime=0.25))
