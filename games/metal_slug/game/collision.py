"""
Collision Detection and Resolution System.
Handles projectile-to-aircraft, aircraft-to-aircraft body collisions,
and area-of-effect blast damage.
"""

from typing import List, Tuple
import math
import pygame
from game.player import PlayerAircraft
from game.enemy import Enemy
from game.projectile import Projectile, HomingMissile, PlasmaLaser
from game.particles import ParticleSystem
from game.audio_manager import AudioManager

class CollisionManager:
    """Manages hit detection and resolves combat collisions."""
    def __init__(self, particles: ParticleSystem, audio: AudioManager):
        self.particles = particles
        self.audio = audio

    def check_player_projectiles(
        self,
        projectiles: List[Projectile],
        enemies: List[Enemy]
    ) -> List[Tuple[Enemy, int]]:
        """Check player bullets/missiles/lasers hitting enemy aircraft."""
        destroyed_enemies: List[Tuple[Enemy, int]] = []

        for proj in projectiles:
            if not proj.alive or not proj.is_player:
                continue

            proj_rect = proj.get_hitbox()

            for enemy in enemies:
                if not enemy.alive:
                    continue

                if proj_rect.colliderect(enemy.get_hitbox()):
                    # Register hit
                    self.particles.create_hit_sparks(proj.x, proj.y)
                    self.audio.play_sound("hit")

                    destroyed = enemy.take_damage(proj.damage)

                    # Projectile-specific effects
                    if isinstance(proj, HomingMissile):
                        # Area blast
                        self.particles.create_explosion(proj.x, proj.y, size_multiplier=1.2)
                        self.audio.play_sound("explosion")
                        proj.alive = False
                    elif isinstance(proj, PlasmaLaser):
                        self.particles.create_laser_impact(proj.x, proj.y)
                        proj.pierce_count -= 1
                        if proj.pierce_count <= 0:
                            proj.alive = False
                    else:
                        proj.alive = False

                    if destroyed:
                        destroyed_enemies.append((enemy, enemy.score_value))
                    break

        return destroyed_enemies

    def check_enemy_projectiles(
        self,
        projectiles: List[Projectile],
        player: PlayerAircraft
    ) -> bool:
        """Check enemy bullets hitting player aircraft. Returns True if player damaged."""
        if not player.alive or player.is_invulnerable:
            return False

        player_rect = player.get_hitbox()
        player_hit = False

        for proj in projectiles:
            if not proj.alive or proj.is_player:
                continue

            if player_rect.colliderect(proj.get_hitbox()):
                proj.alive = False
                self.particles.create_hit_sparks(player.x, player.y, (255, 60, 60))
                self.particles.trigger_shake(magnitude=8.0, duration=0.35)
                self.audio.play_sound("hit")
                player.take_damage(proj.damage)
                player_hit = True

        return player_hit

    def check_body_collisions(
        self,
        player: PlayerAircraft,
        enemies: List[Enemy]
    ) -> List[Tuple[Enemy, int]]:
        """Check direct ramming collision between player and enemy aircraft."""
        destroyed: List[Tuple[Enemy, int]] = []
        if not player.alive or player.is_invulnerable:
            return destroyed

        player_rect = player.get_hitbox()

        for enemy in enemies:
            if not enemy.alive:
                continue

            if player_rect.colliderect(enemy.get_hitbox()):
                # Ram damage
                player.take_damage(25)
                self.particles.create_explosion((player.x + enemy.x) / 2, (player.y + enemy.y) / 2, size_multiplier=1.4)
                self.audio.play_sound("explosion")
                self.particles.trigger_shake(magnitude=10.0, duration=0.4)

                if not enemy.is_boss:
                    is_dead = enemy.take_damage(60)
                    if is_dead:
                        destroyed.append((enemy, enemy.score_value))

        return destroyed
