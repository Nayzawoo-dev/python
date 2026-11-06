"""
Enemy Aircraft and Boss Encounters.
Implements Scout Fighters, Interceptors, Heavy Bombers, and the massive multi-phase Dreadnought Boss.
"""

from typing import List, Optional, Tuple
import math
import random
import pygame
from config import BASE_DIR, SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_RED, COLOR_AMBER, COLOR_YELLOW, COLOR_WHITE
from game.animation import AssetLoader, AnimatedSprite
from game.projectile import Projectile, EnemyBullet, EnemyMissile

class Enemy:
    """Base class for all enemy aircraft."""
    def __init__(
        self,
        x: float,
        y: float,
        hp: int,
        score_value: int,
        asset_name: str,
        scale: float = 1.4,
        flip_x: bool = True  # Enemies face left towards player
    ):
        self.x = x
        self.y = y
        self.max_hp = hp
        self.hp = hp
        self.score_value = score_value
        self.alive = True
        self.is_boss = False

        # Load animated sprite
        self.anim: AnimatedSprite = AssetLoader.load_gif(
            BASE_DIR / asset_name,
            scale=scale,
            flip_x=flip_x
        )

        self.hit_flash_timer = 0.0
        self.fire_timer = random.uniform(0.5, 1.8)

    def update(self, dt: float, player_x: float, player_y: float) -> List[Projectile]:
        self.anim.update(dt)
        if self.hit_flash_timer > 0:
            self.hit_flash_timer -= dt

        # Offscreen cleanup (left edge)
        if self.x < -160:
            self.alive = False

        return []

    def take_damage(self, damage: int) -> bool:
        """Apply damage. Returns True if destroyed."""
        self.hp -= damage
        self.hit_flash_timer = 0.08
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            return True
        return False

    def get_hitbox(self) -> pygame.Rect:
        curr = self.anim.get_current_frame()
        w = int(curr.get_width() * 0.75)
        h = int(curr.get_height() * 0.75)
        return pygame.Rect(int(self.x - w // 2), int(self.y - h // 2), w, h)

    def render(self, surface: pygame.Surface) -> None:
        if not self.alive:
            return

        frame = self.anim.get_current_frame()
        rect = frame.get_rect(center=(int(self.x), int(self.y)))

        if self.hit_flash_timer > 0:
            # White/bright flash on hit
            flash_surf = frame.copy()
            flash_surf.fill((255, 255, 255, 200), special_flags=pygame.BLEND_RGB_ADD)
            surface.blit(flash_surf, rect)
        else:
            surface.blit(frame, rect)


class ScoutFighter(Enemy):
    """Nimble enemy scout using plane1.gif flying in sine wave or straight pass."""
    def __init__(self, x: float, y: float, pattern: str = "sine"):
        super().__init__(x, y, hp=35, score_value=150, asset_name="plane1.gif", scale=1.4, flip_x=True)
        self.pattern = pattern
        self.speed = random.uniform(220, 310)
        self.base_y = y
        self.sine_time = random.uniform(0, 6.28)
        self.amplitude = random.uniform(40, 80)
        self.frequency = random.uniform(2.5, 4.0)

    def update(self, dt: float, player_x: float, player_y: float) -> List[Projectile]:
        super().update(dt, player_x, player_y)
        self.x -= self.speed * dt

        if self.pattern == "sine":
            self.sine_time += dt * self.frequency
            self.y = self.base_y + math.sin(self.sine_time) * self.amplitude
        elif self.pattern == "dive":
            if self.x > player_x + 100:
                self.y += 60 * dt
            else:
                self.y -= 80 * dt

        # Firing
        self.fire_timer -= dt
        if self.fire_timer <= 0:
            self.fire_timer = random.uniform(1.8, 3.0)
            if self.x > player_x + 80 and self.x < SCREEN_WIDTH:
                # Fire bullet toward player
                angle = math.atan2(player_y - self.y, player_x - self.x)
                speed = 360.0
                vx = math.cos(angle) * speed
                vy = math.sin(angle) * speed
                return [EnemyBullet(self.x - 30, self.y, vx, vy, damage=12)]

        return []


class Interceptor(Enemy):
    """Heavier attack aircraft using plane2.gif with burst fire."""
    def __init__(self, x: float, y: float):
        super().__init__(x, y, hp=65, score_value=280, asset_name="plane2.gif", scale=1.45, flip_x=True)
        self.speed = 190.0
        self.target_y = y

    def update(self, dt: float, player_x: float, player_y: float) -> List[Projectile]:
        super().update(dt, player_x, player_y)
        self.x -= self.speed * dt

        # Smoothly track player Y level to intercept
        dy = player_y - self.y
        self.y += dy * min(1.0, 1.2 * dt)

        self.fire_timer -= dt
        if self.fire_timer <= 0:
            self.fire_timer = random.uniform(2.0, 3.5)
            if self.x > player_x + 50 and self.x < SCREEN_WIDTH:
                # Twin burst
                return [
                    EnemyBullet(self.x - 35, self.y - 12, vx=-420.0, vy=0.0, damage=14),
                    EnemyBullet(self.x - 35, self.y + 12, vx=-420.0, vy=0.0, damage=14)
                ]

        return []


class HeavyBomber(Enemy):
    """Elite mini-boss / heavy gunship using bossplane2.gif."""
    def __init__(self, x: float, y: float):
        super().__init__(x, y, hp=240, score_value=750, asset_name="bossplane2.gif", scale=1.1, flip_x=False)
        self.speed = 95.0
        self.hover_dir = 1.0

    def update(self, dt: float, player_x: float, player_y: float) -> List[Projectile]:
        super().update(dt, player_x, player_y)
        # Advance into screen, then hover up and down
        if self.x > SCREEN_WIDTH * 0.78:
            self.x -= 140 * dt
        else:
            self.y += self.hover_dir * 70 * dt
            if self.y < 120:
                self.hover_dir = 1.0
            elif self.y > SCREEN_HEIGHT - 120:
                self.hover_dir = -1.0

        self.fire_timer -= dt
        if self.fire_timer <= 0:
            self.fire_timer = 1.8
            # 3-way spread attack
            projectiles = []
            for angle_offset in [-0.25, 0.0, 0.25]:
                angle = math.pi + angle_offset
                vx = math.cos(angle) * 350.0
                vy = math.sin(angle) * 350.0
                projectiles.append(EnemyBullet(self.x - 50, self.y, vx, vy, damage=18))
            return projectiles

        return []


class DreadnoughtBoss(Enemy):
    """The massive 40-frame stage boss using bossplane1.gif."""
    def __init__(self):
        super().__init__(
            x=SCREEN_WIDTH + 320,
            y=SCREEN_HEIGHT * 0.5,
            hp=1600,
            score_value=5000,
            asset_name="bossplane1.gif",
            scale=1.1,
            flip_x=False
        )
        self.is_boss = True
        self.target_x = SCREEN_WIDTH * 0.76
        self.hover_timer = 0.0
        self.attack_timer = 2.0
        self.current_phase = 1
        self.laser_warning = 0.0

    def update(self, dt: float, player_x: float, player_y: float) -> List[Projectile]:
        super().update(dt, player_x, player_y)

        # Entrance advance
        if self.x > self.target_x:
            self.x -= 160 * dt
        else:
            # Hover in majestic vertical figure-8 wave
            self.hover_timer += dt * 1.2
            self.y = SCREEN_HEIGHT * 0.5 + math.sin(self.hover_timer) * 160.0

        # Phase transitions based on HP
        hp_ratio = self.hp / self.max_hp
        if hp_ratio > 0.6:
            self.current_phase = 1
        elif hp_ratio > 0.25:
            self.current_phase = 2
        else:
            self.current_phase = 3  # OVERDRIVE

        projectiles: List[Projectile] = []
        self.attack_timer -= dt

        if self.attack_timer <= 0:
            if self.current_phase == 1:
                # Phase 1: Vulcan sweep + missiles
                self.attack_timer = 1.6
                projectiles.append(EnemyMissile(self.x - 120, self.y - 50, player_x, player_y))
                projectiles.append(EnemyMissile(self.x - 120, self.y + 50, player_x, player_y))
            elif self.current_phase == 2:
                # Phase 2: Rapid 5-way spread cannons
                self.attack_timer = 1.2
                for offset in [-0.35, -0.18, 0.0, 0.18, 0.35]:
                    angle = math.pi + offset
                    vx = math.cos(angle) * 380.0
                    vy = math.sin(angle) * 380.0
                    projectiles.append(EnemyBullet(self.x - 140, self.y, vx, vy, damage=16))
            else:
                # Phase 3: Overdrive bullet curtain + heavy missiles
                self.attack_timer = 0.85
                projectiles.append(EnemyMissile(self.x - 100, self.y - 70, player_x, player_y, speed=420))
                projectiles.append(EnemyMissile(self.x - 100, self.y + 70, player_x, player_y, speed=420))
                for offset in [-0.4, -0.2, 0.0, 0.2, 0.4]:
                    angle = math.pi + offset + math.sin(self.hover_timer * 3) * 0.1
                    vx = math.cos(angle) * 440.0
                    vy = math.sin(angle) * 440.0
                    projectiles.append(EnemyBullet(self.x - 150, self.y, vx, vy, damage=18))

        return projectiles

    def get_hitbox(self) -> pygame.Rect:
        # Generous boss hitbox matching its central fuselage
        return pygame.Rect(int(self.x - 180), int(self.y - 90), 360, 180)
