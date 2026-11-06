"""
Player Aircraft Class.
Handles movement, boundary clamping, weapons, invulnerability frames,
tilt banking animations, and firing logic.
"""

from typing import List, Optional, Tuple
import math
import pygame
from config import (
    BASE_DIR, SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_DEFAULT_ARMOR,
    PLAYER_INVULN_TIME, PLAYER_SCALE, WEAPON_MACHINE_GUN, WEAPON_MISSILE,
    WEAPON_LASER, WEAPONS_INFO, COLOR_WHITE, COLOR_RED, COLOR_AMBER, COLOR_YELLOW
)
from game.animation import AssetLoader, AnimatedSprite
from game.projectile import Projectile, VulcanBullet, HomingMissile, PlasmaLaser

class PlayerAircraft:
    """The player's combat aircraft."""
    def __init__(self, x: float = 200, y: float = 360, aircraft_asset: str = "plane1.gif"):
        self.x = x
        self.y = y
        self.prev_y = y
        self.vx = 0.0
        self.vy = 0.0

        # Load animated sprite using user's asset
        # Plane1 and Plane2 point to the right; we ensure correct horizontal orientation
        self.aircraft_asset = aircraft_asset
        self.anim: AnimatedSprite = AssetLoader.load_gif(
            BASE_DIR / aircraft_asset,
            scale=PLAYER_SCALE,
            flip_x=False
        )

        # Combat stats
        self.max_armor = PLAYER_DEFAULT_ARMOR
        self.armor = self.max_armor
        self.invulnerable_timer = 0.0
        self.is_invulnerable = False
        self.alive = True

        # Weapons
        self.current_weapon = WEAPON_MACHINE_GUN
        self.fire_cooldown = 0.0
        self.ammo_counts = {
            WEAPON_MACHINE_GUN: -1,
            WEAPON_MISSILE: WEAPONS_INFO[WEAPON_MISSILE]["ammo"],
            WEAPON_LASER: WEAPONS_INFO[WEAPON_LASER]["ammo"],
        }
        self.barrel_toggle = 0  # Alternates left/right gun fire

        # Visual banking tilt
        self.tilt_angle = 0.0

    def set_aircraft(self, asset_name: str) -> None:
        """Switch player aircraft model."""
        self.aircraft_asset = asset_name
        self.anim = AssetLoader.load_gif(BASE_DIR / asset_name, scale=PLAYER_SCALE, flip_x=False)

    def switch_weapon(self, weapon_type: str) -> None:
        """Switch active weapon."""
        if weapon_type in WEAPONS_INFO:
            self.current_weapon = weapon_type

    def update(self, dt: float, target_pos: Optional[Tuple[float, float]] = None, keys=None) -> None:
        """Update position, animation, tilt, and weapon cooldown."""
        self.prev_y = self.y

        # Movement: smoothly interpolate toward target_pos (hand tracking)
        if target_pos:
            tx, ty = target_pos
            # Clamping target position within comfortable player zone (left 75% of screen)
            tx = max(80, min(SCREEN_WIDTH * 0.75, tx))
            ty = max(60, min(SCREEN_HEIGHT - 80, ty))

            dx = tx - self.x
            dy = ty - self.y
            # Smooth arcade flight interpolation
            follow_speed = 12.0
            self.x += dx * min(1.0, follow_speed * dt)
            self.y += dy * min(1.0, follow_speed * dt)
        elif keys:
            # Fallback keyboard controls
            speed = 460.0
            move_x, move_y = 0.0, 0.0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]: move_x -= 1.0
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]: move_x += 1.0
            if keys[pygame.K_UP] or keys[pygame.K_w]: move_y -= 1.0
            if keys[pygame.K_DOWN] or keys[pygame.K_s]: move_y += 1.0

            if move_x != 0 and move_y != 0:
                move_x *= 0.7071
                move_y *= 0.7071

            self.x += move_x * speed * dt
            self.y += move_y * speed * dt

        # Screen boundary clamping
        self.x = max(70, min(SCREEN_WIDTH * 0.75, self.x))
        self.y = max(50, min(SCREEN_HEIGHT - 60, self.y))

        # Dynamic banking tilt based on vertical movement
        vy = (self.y - self.prev_y) / max(0.001, dt)
        target_tilt = max(-16.0, min(16.0, vy * -0.04))
        self.tilt_angle += (target_tilt - self.tilt_angle) * min(1.0, 10.0 * dt)

        # Update sprite animation
        self.anim.update(dt)

        # Cooldowns and invulnerability
        if self.fire_cooldown > 0:
            self.fire_cooldown = max(0.0, self.fire_cooldown - dt)

        if self.invulnerable_timer > 0:
            self.invulnerable_timer -= dt
            self.is_invulnerable = self.invulnerable_timer > 0
        else:
            self.is_invulnerable = False

    def fire(self) -> List[Projectile]:
        """Fire active weapon and return created projectiles."""
        if self.fire_cooldown > 0 or not self.alive:
            return []

        w_info = WEAPONS_INFO[self.current_weapon]
        ammo = self.ammo_counts[self.current_weapon]

        # Check ammo
        if ammo == 0:
            # Fallback to Vulcan Cannon if out of ammo
            self.current_weapon = WEAPON_MACHINE_GUN
            w_info = WEAPONS_INFO[self.current_weapon]

        self.fire_cooldown = w_info["cooldown"]
        if ammo > 0:
            self.ammo_counts[self.current_weapon] -= 1

        projectiles: List[Projectile] = []
        nose_x = self.x + 40
        self.barrel_toggle = 1 - self.barrel_toggle
        y_offset = -12 if self.barrel_toggle == 0 else 12

        if self.current_weapon == WEAPON_MACHINE_GUN:
            # Rapid dual vulcan shots
            projectiles.append(VulcanBullet(nose_x, self.y + y_offset, damage=w_info["damage"]))
        elif self.current_weapon == WEAPON_MISSILE:
            # Twin homing missiles
            projectiles.append(HomingMissile(nose_x, self.y - 18, damage=w_info["damage"], initial_vy=-80))
            projectiles.append(HomingMissile(nose_x, self.y + 18, damage=w_info["damage"], initial_vy=80))
        elif self.current_weapon == WEAPON_LASER:
            # Piercing plasma beam
            projectiles.append(PlasmaLaser(nose_x, self.y, damage=w_info["damage"]))

        return projectiles

    def take_damage(self, amount: int) -> bool:
        """Apply damage unless invulnerable. Returns True if destroyed."""
        if self.is_invulnerable or not self.alive:
            return False

        self.armor -= amount
        self.invulnerable_timer = PLAYER_INVULN_TIME
        self.is_invulnerable = True

        if self.armor <= 0:
            self.armor = 0
            self.alive = False
            return True
        return False

    def repair(self, amount: int) -> None:
        """Heal player armor."""
        self.armor = min(self.max_armor, self.armor + amount)

    def add_ammo(self, weapon: str, amount: int) -> None:
        """Replenish ammo for specified weapon."""
        if weapon in self.ammo_counts and self.ammo_counts[weapon] != -1:
            self.ammo_counts[weapon] += amount

    def get_hitbox(self) -> pygame.Rect:
        """Generates tight hitbox smaller than visual sprite for fair arcade dodging."""
        hw = 36
        hh = 20
        return pygame.Rect(int(self.x - hw // 2), int(self.y - hh // 2), hw, hh)

    def render(self, surface: pygame.Surface) -> None:
        """Render player aircraft with tilt banking and invulnerability flashing."""
        if not self.alive:
            return

        # Invulnerability flicker (flash every 0.1s)
        if self.is_invulnerable and int(self.invulnerable_timer * 15) % 2 == 0:
            return

        frame = self.anim.get_current_frame()
        # Rotate based on tilt
        if abs(self.tilt_angle) > 0.5:
            rotated = pygame.transform.rotate(frame, self.tilt_angle)
        else:
            rotated = frame

        rect = rotated.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(rotated, rect)

        # Subtle jet engine exhaust glow at tail
        tail_x = int(self.x - 38)
        tail_y = int(self.y)
        pygame.draw.circle(surface, COLOR_AMBER, (tail_x, tail_y), 4)
