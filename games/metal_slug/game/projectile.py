"""
Projectiles System for Player and Enemy Weapons.
Implements Vulcan tracers, Homing Missiles with smoke trails, Plasma Lasers,
and Enemy ordnance.
"""

from typing import Tuple, Optional, List
import math
import random
import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_AMBER, COLOR_ORANGE, COLOR_CYAN, COLOR_RED, COLOR_YELLOW

class Projectile:
    """Base class for all in-flight projectiles."""
    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        damage: int,
        is_player: bool = True
    ):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.damage = damage
        self.is_player = is_player
        self.alive = True
        self.radius = 4.0

    def update(self, dt: float, target=None) -> None:
        self.x += self.vx * dt
        self.y += self.vy * dt

        # Bounds check
        if self.x < -100 or self.x > SCREEN_WIDTH + 100 or self.y < -100 or self.y > SCREEN_HEIGHT + 100:
            self.alive = False

    def render(self, surface: pygame.Surface) -> None:
        pass

    def get_hitbox(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - self.radius), int(self.y - self.radius), int(self.radius * 2), int(self.radius * 2))


class VulcanBullet(Projectile):
    """High-velocity tracer bullet fired by Vulcan Machine Gun."""
    def __init__(self, x: float, y: float, damage: int = 16, vy_offset: float = 0.0):
        super().__init__(x, y, vx=1250.0, vy=vy_offset, damage=damage, is_player=True)
        self.radius = 5.0
        self.length = 22.0

    def render(self, surface: pygame.Surface) -> None:
        # Elongated tracer bullet
        start_x = int(self.x - self.length)
        end_x = int(self.x)
        y = int(self.y)
        # Glow outer line
        pygame.draw.line(surface, COLOR_ORANGE, (start_x, y), (end_x, y), 5)
        # Bright core line
        pygame.draw.line(surface, COLOR_YELLOW, (start_x + 6, y), (end_x, y), 2)
        # Bullet head tip
        pygame.draw.circle(surface, (255, 255, 255), (end_x, y), 3)


class HomingMissile(Projectile):
    """Guided rocket tracking nearest enemy target with smoke emission."""
    def __init__(self, x: float, y: float, damage: int = 65, initial_vy: float = 0.0):
        super().__init__(x, y, vx=550.0, vy=initial_vy, damage=damage, is_player=True)
        self.radius = 7.0
        self.speed = 650.0
        self.angle = 0.0  # radians (0 is pointing right)
        self.turn_rate = 3.8  # radians/sec tracking agility
        self.lifetime = 3.5
        self.age = 0.0

    def update(self, dt: float, target=None) -> None:
        self.age += dt
        if self.age >= self.lifetime:
            self.alive = False
            return

        # Target acquisition & homing guidance
        if target and target.alive:
            dx = target.x - self.x
            dy = target.y - self.y
            target_angle = math.atan2(dy, dx)
            # Shortest angle difference
            angle_diff = (target_angle - self.angle + math.pi) % (2 * math.pi) - math.pi
            if abs(angle_diff) > 0.01:
                self.angle += math.copysign(min(abs(angle_diff), self.turn_rate * dt), angle_diff)

        self.vx = math.cos(self.angle) * self.speed
        self.vy = math.sin(self.angle) * self.speed

        self.x += self.vx * dt
        self.y += self.vy * dt

        if self.x < -100 or self.x > SCREEN_WIDTH + 150 or self.y < -100 or self.y > SCREEN_HEIGHT + 100:
            self.alive = False

    def render(self, surface: pygame.Surface) -> None:
        # Draw rotated missile body
        cos_a = math.cos(self.angle)
        sin_a = math.sin(self.angle)
        head_x = self.x + cos_a * 10
        head_y = self.y + sin_a * 10
        tail_x = self.x - cos_a * 10
        tail_y = self.y - sin_a * 10

        # Body
        pygame.draw.line(surface, (220, 220, 230), (int(tail_x), int(tail_y)), (int(head_x), int(head_y)), 6)
        # Red warhead tip
        pygame.draw.circle(surface, COLOR_RED, (int(head_x), int(head_y)), 4)
        # Exhaust flame
        flame_x = tail_x - cos_a * random.uniform(4, 8)
        flame_y = tail_y - sin_a * random.uniform(4, 8)
        pygame.draw.circle(surface, COLOR_ORANGE, (int(flame_x), int(flame_y)), random.randint(3, 5))


class PlasmaLaser(Projectile):
    """High-energy beam that pierces through enemies."""
    def __init__(self, x: float, y: float, damage: int = 32):
        super().__init__(x, y, vx=2200.0, vy=0.0, damage=damage, is_player=True)
        self.radius = 8.0
        self.length = 75.0
        self.pierce_count = 3  # can hit multiple targets

    def render(self, surface: pygame.Surface) -> None:
        start_x = int(self.x - self.length)
        end_x = int(self.x)
        y = int(self.y)
        # Cyan aura glow
        pygame.draw.line(surface, (0, 180, 255), (start_x, y), (end_x, y), 10)
        # Pure white plasma core
        pygame.draw.line(surface, (255, 255, 255), (start_x + 10, y), (end_x, y), 4)
        # Energy ring
        pygame.draw.circle(surface, COLOR_CYAN, (end_x, y), 6)


class EnemyBullet(Projectile):
    """Red energy orb or bullet fired by enemy aircraft."""
    def __init__(self, x: float, y: float, vx: float, vy: float, damage: int = 15):
        super().__init__(x, y, vx, vy, damage, is_player=False)
        self.radius = 6.0

    def render(self, surface: pygame.Surface) -> None:
        px, py = int(self.x), int(self.y)
        # Outer crimson glow
        pygame.draw.circle(surface, (255, 40, 60), (px, py), 7)
        # Inner bright core
        pygame.draw.circle(surface, (255, 220, 200), (px, py), 4)


class EnemyMissile(Projectile):
    """Heavy guided missile fired by Boss."""
    def __init__(self, x: float, y: float, target_x: float, target_y: float, speed: float = 380.0):
        angle = math.atan2(target_y - y, target_x - x)
        vx = math.cos(angle) * speed
        vy = math.sin(angle) * speed
        super().__init__(x, y, vx, vy, damage=28, is_player=False)
        self.radius = 8.0

    def render(self, surface: pygame.Surface) -> None:
        px, py = int(self.x), int(self.y)
        pygame.draw.circle(surface, (255, 120, 0), (px, py), 9)
        pygame.draw.circle(surface, (255, 255, 0), (px, py), 5)
