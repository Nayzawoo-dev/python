"""
Core Game Engine and State Machine for Operation Slug Wing.
Orchestrates waves, boss encounter, combat collisions, particles,
audio, input devices, and state transitions.
"""

from typing import List, Optional, Tuple
import math
import random
import pygame
from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, STATE_MENU, STATE_BACKGROUND_SELECT,
    STATE_CALIBRATION, STATE_PLAYING, STATE_PAUSED, STATE_GAME_OVER,
    STATE_VICTORY, STATE_SETTINGS, WEAPON_MACHINE_GUN, WEAPON_MISSILE,
    WEAPON_LASER, save_settings
)
from game.audio_manager import AudioManager
from game.background_manager import BackgroundManager
from game.hand_controller import HandController
from game.particles import ParticleSystem
from game.player import PlayerAircraft
from game.enemy import Enemy, ScoutFighter, Interceptor, HeavyBomber, DreadnoughtBoss
from game.projectile import Projectile, HomingMissile
from game.collision import CollisionManager
from game.ui import UIManager

class GameEngine:
    """Central engine running game state logic, updates, and rendering."""
    def __init__(self, settings: dict):
        self.settings = settings
        self.state = STATE_MENU

        # Core subsystems
        self.audio = AudioManager(settings)
        self.bg_manager = BackgroundManager(settings)
        self.hand_controller = HandController(settings)
        self.particles = ParticleSystem()
        self.collision = CollisionManager(self.particles, self.audio)
        self.ui = UIManager(settings, self.bg_manager)

        # Gameplay Entities
        self.player: Optional[PlayerAircraft] = None
        self.enemies: List[Enemy] = []
        self.player_projectiles: List[Projectile] = []
        self.enemy_projectiles: List[Projectile] = []
        self.boss: Optional[DreadnoughtBoss] = None

        # Combat Stats & Wave Logic
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.combo_timer = 0.0
        self.wave = 1
        self.wave_timer = 0.0
        self.wave_enemies_spawned = 0
        self.wave_spawn_delay = 0.0
        self.boss_spawned = False
        self.is_mission_complete = False

        # Menu State navigation
        self.menu_items = ["START MISSION", "SELECT AIRSPACE", "HAND CALIBRATION", "SETTINGS", "EXIT"]
        self.menu_index = 0
        self.pause_options = ["RESUME", "RESTART", "SETTINGS", "QUIT TO MENU"]
        self.pause_index = 0
        self.settings_index = 0

        # Debouncing and timers
        self.prev_pinch = False
        self.fire_hold_timer = 0.0
        self.game_over_timer = 0.0

        # Start background music
        self.audio.play_music(loop=True)

    def reset_mission(self) -> None:
        """Initialize or reset a gameplay mission session."""
        selected_craft = self.settings.get("selected_aircraft", "plane1.gif")
        self.player = PlayerAircraft(x=200, y=360, aircraft_asset=selected_craft)
        self.enemies.clear()
        self.player_projectiles.clear()
        self.enemy_projectiles.clear()
        self.boss = None

        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.combo_timer = 0.0
        self.wave = 1
        self.wave_timer = 0.0
        self.wave_enemies_spawned = 0
        self.wave_spawn_delay = 1.0
        self.boss_spawned = False
        self.is_mission_complete = False
        self.game_over_timer = 0.0

        # Clear particles and screen shake
        self.particles.particles.clear()
        self.particles.floating_texts.clear()
        self.particles.shake_timer = 0.0
        self.particles.shake_offset = (0, 0)

        self.audio.start_engine_sound()

    def reset_to_main_menu(self) -> None:
        """Cleanly reset all combat session state and return to Main Menu without exiting."""
        self.audio.stop_engine_sound()
        self.player = None
        self.enemies.clear()
        self.player_projectiles.clear()
        self.enemy_projectiles.clear()
        self.boss = None
        self.boss_spawned = False
        self.is_mission_complete = False

        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.combo_timer = 0.0
        self.wave = 1
        self.wave_timer = 0.0
        self.wave_enemies_spawned = 0
        self.wave_spawn_delay = 0.0
        self.game_over_timer = 0.0

        # Clear particles and shake
        self.particles.particles.clear()
        self.particles.floating_texts.clear()
        self.particles.shake_timer = 0.0
        self.particles.shake_offset = (0, 0)

        self.state = STATE_MENU
        self.audio.play_music(loop=True)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle user events. Returns False if game should exit."""
        if event.type == pygame.QUIT:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F11:
                # Toggle fullscreen
                cur = self.settings.get("fullscreen", False)
                self.settings["fullscreen"] = not cur
                save_settings(self.settings)

            # State-specific Key Handling
            if self.state == STATE_MENU:
                if event.key in (pygame.K_UP, pygame.K_w):
                    self.menu_index = (self.menu_index - 1) % len(self.menu_items)
                    self.audio.play_sound("menu_select")
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.menu_index = (self.menu_index + 1) % len(self.menu_items)
                    self.audio.play_sound("menu_select")
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.audio.play_sound("menu_confirm")
                    choice = self.menu_items[self.menu_index]
                    if choice == "START MISSION":
                        # Per rule 12: Go to Background Selection before starting!
                        self.state = STATE_BACKGROUND_SELECT
                    elif choice == "SELECT AIRSPACE":
                        self.state = STATE_BACKGROUND_SELECT
                    elif choice == "HAND CALIBRATION":
                        self.state = STATE_CALIBRATION
                    elif choice == "SETTINGS":
                        self.state = STATE_SETTINGS
                    elif choice == "EXIT":
                        return False

            elif self.state == STATE_BACKGROUND_SELECT:
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    self.bg_manager.prev_background()
                    self.audio.play_sound("menu_select")
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.bg_manager.next_background()
                    self.audio.play_sound("menu_select")
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.audio.play_sound("menu_confirm")
                    save_settings(self.settings)
                    # Proceed to mission or calibration
                    self.reset_mission()
                    self.state = STATE_PLAYING
                elif event.key == pygame.K_ESCAPE:
                    self.audio.play_sound("menu_select")
                    self.state = STATE_MENU

            elif self.state == STATE_CALIBRATION:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    self.audio.play_sound("menu_confirm")
                    self.state = STATE_BACKGROUND_SELECT
                elif event.key == pygame.K_ESCAPE:
                    self.audio.play_sound("menu_select")
                    self.state = STATE_MENU

            elif self.state == STATE_PLAYING:
                if event.key == pygame.K_ESCAPE:
                    self.audio.stop_engine_sound()
                    self.audio.play_sound("menu_select")
                    self.state = STATE_PAUSED
                elif event.key == pygame.K_1:
                    if self.player: self.player.switch_weapon(WEAPON_MACHINE_GUN)
                    self.audio.play_sound("menu_select")
                elif event.key == pygame.K_2:
                    if self.player: self.player.switch_weapon(WEAPON_MISSILE)
                    self.audio.play_sound("menu_select")
                elif event.key == pygame.K_3:
                    if self.player: self.player.switch_weapon(WEAPON_LASER)
                    self.audio.play_sound("menu_select")

            elif self.state == STATE_PAUSED:
                if event.key in (pygame.K_UP, pygame.K_w):
                    self.pause_index = (self.pause_index - 1) % len(self.pause_options)
                    self.audio.play_sound("menu_select")
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.pause_index = (self.pause_index + 1) % len(self.pause_options)
                    self.audio.play_sound("menu_select")
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.audio.play_sound("menu_confirm")
                    choice = self.pause_options[self.pause_index]
                    if choice == "RESUME":
                        self.audio.start_engine_sound()
                        self.state = STATE_PLAYING
                    elif choice == "RESTART":
                        self.reset_mission()
                        self.state = STATE_PLAYING
                    elif choice == "SETTINGS":
                        self.state = STATE_SETTINGS
                    elif choice == "QUIT TO MENU":
                        self.audio.play_sound("menu_select")
                        self.reset_to_main_menu()
                elif event.key == pygame.K_ESCAPE:
                    self.audio.start_engine_sound()
                    self.state = STATE_PLAYING

            elif self.state == STATE_GAME_OVER:
                if event.key == pygame.K_r:
                    self.audio.play_sound("menu_confirm")
                    self.reset_mission()
                    self.state = STATE_PLAYING
                elif event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                    self.audio.play_sound("menu_select")
                    self.reset_to_main_menu()

            elif self.state == STATE_VICTORY:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.audio.play_sound("menu_confirm")
                    self.reset_mission()
                    self.state = STATE_PLAYING
                elif event.key == pygame.K_ESCAPE:
                    self.audio.play_sound("menu_select")
                    self.reset_to_main_menu()

            elif self.state == STATE_SETTINGS:
                if event.key in (pygame.K_UP, pygame.K_w):
                    self.settings_index = (self.settings_index - 1) % 7
                    self.audio.play_sound("menu_select")
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.settings_index = (self.settings_index + 1) % 7
                    self.audio.play_sound("menu_select")
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    self._adjust_setting(self.settings_index, -1)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self._adjust_setting(self.settings_index, 1)
                elif event.key == pygame.K_ESCAPE:
                    self.audio.play_sound("menu_select")
                    save_settings(self.settings)
                    self.state = STATE_MENU

        return True

    def _adjust_setting(self, idx: int, delta: int) -> None:
        """Modify specific setting value and trigger update."""
        self.audio.play_sound("menu_select")
        if idx == 0:  # Master Volume
            v = max(0.0, min(1.0, self.settings.get("master_volume", 0.8) + delta * 0.1))
            self.settings["master_volume"] = round(v, 2)
            self.audio.set_master_volume(v)
        elif idx == 1:  # SFX Volume
            v = max(0.0, min(1.0, self.settings.get("sfx_volume", 0.85) + delta * 0.1))
            self.settings["sfx_volume"] = round(v, 2)
            self.audio.set_sfx_volume(v)
        elif idx == 2:  # Music Volume
            v = max(0.0, min(1.0, self.settings.get("music_volume", 0.65) + delta * 0.1))
            self.settings["music_volume"] = round(v, 2)
            self.audio.set_music_volume(v)
        elif idx == 3:  # Sensitivity
            s = max(0.5, min(3.0, self.settings.get("hand_sensitivity", 1.25) + delta * 0.15))
            self.settings["hand_sensitivity"] = round(s, 2)
        elif idx == 4:  # Smoothing
            sm = max(0.2, min(0.9, self.settings.get("hand_smoothing", 0.65) + delta * 0.05))
            self.settings["hand_smoothing"] = round(sm, 2)
        elif idx == 5:  # Webcam overlay
            self.settings["show_webcam_feed"] = not self.settings.get("show_webcam_feed", True)
        elif idx == 6:  # Screen shake
            self.settings["screen_shake_enabled"] = not self.settings.get("screen_shake_enabled", True)

    def update(self, dt: float) -> None:
        """Update active game state."""
        self.hand_controller.update(dt)
        self.ui.update(dt)

        if self.state == STATE_PLAYING:
            self._update_playing(dt)
        elif self.state == STATE_GAME_OVER:
            self.game_over_timer -= dt
            self.particles.update(dt)
            self.bg_manager.update(dt, speed_multiplier=0.3)
            if self.game_over_timer <= 0:
                self.reset_to_main_menu()
        else:
            # Idle background scroll during menus
            self.bg_manager.update(dt, speed_multiplier=0.4)

    def _update_playing(self, dt: float) -> None:
        """Core combat gameplay update."""
        if not self.player or not self.player.alive:
            self.audio.stop_engine_sound()
            self.state = STATE_GAME_OVER
            self.game_over_timer = 5.0
            return

        # 1. Update background parallax scroll
        self.bg_manager.update(dt, speed_multiplier=1.2)

        # 2. Hand / Keyboard movement & gestures
        target_pos = None
        if self.hand_controller.hand_detected:
            target_pos = self.hand_controller.get_position()
            # Gesture weapon selection
            weapon_idx = self.hand_controller.get_selected_weapon_index()
            if weapon_idx == 1:
                self.player.switch_weapon(WEAPON_MACHINE_GUN)
            elif weapon_idx == 2:
                self.player.switch_weapon(WEAPON_MISSILE)
            elif weapon_idx == 3:
                self.player.switch_weapon(WEAPON_LASER)

        keys = pygame.key.get_pressed()
        self.player.update(dt, target_pos=target_pos, keys=keys if not target_pos else None)

        # 3. Fire logic: Pinch gesture OR Space bar
        is_pinching = self.hand_controller.is_firing()
        should_fire = is_pinching or keys[pygame.K_SPACE]

        if should_fire:
            fired = self.player.fire()
            if fired:
                self.player_projectiles.extend(fired)
                # Play weapon sound
                if self.player.current_weapon == WEAPON_MACHINE_GUN:
                    self.audio.play_sound("gun")
                elif self.player.current_weapon == WEAPON_MISSILE:
                    self.audio.play_sound("missile")
                elif self.player.current_weapon == WEAPON_LASER:
                    self.audio.play_sound("laser")

        # 4. Update Projectiles
        # Find nearest target for homing missiles
        nearest_enemy = None
        min_dist = 999999.0
        for e in self.enemies:
            if e.alive and e.x > self.player.x:
                d = math.hypot(e.x - self.player.x, e.y - self.player.y)
                if d < min_dist:
                    min_dist = d
                    nearest_enemy = e

        for p in self.player_projectiles:
            p.update(dt, target=nearest_enemy)
            if hasattr(p, "is_player") and p.is_player and isinstance(p, HomingMissile):
                self.particles.create_missile_smoke(p.x - 12, p.y)

        for ep in self.enemy_projectiles:
            ep.update(dt)

        self.player_projectiles = [p for p in self.player_projectiles if p.alive]
        self.enemy_projectiles = [p for p in self.enemy_projectiles if p.alive]

        # 5. Enemy Waves & Spawner
        self._update_enemy_spawning(dt)

        # 6. Update Active Enemies
        for e in self.enemies:
            new_ordnance = e.update(dt, self.player.x, self.player.y)
            if new_ordnance:
                self.enemy_projectiles.extend(new_ordnance)

        # 7. Collisions: Player projectiles vs Enemies
        destroyed_list = self.collision.check_player_projectiles(self.player_projectiles, self.enemies)
        for enemy, pts in destroyed_list:
            self._handle_enemy_destroyed(enemy, pts)

        # 8. Collisions: Enemy projectiles vs Player
        self.collision.check_enemy_projectiles(self.enemy_projectiles, self.player)

        # 9. Collisions: Aircraft body ramming
        rammed_destroyed = self.collision.check_body_collisions(self.player, self.enemies)
        for enemy, pts in rammed_destroyed:
            self._handle_enemy_destroyed(enemy, pts)

        # 10. Clean dead enemies
        self.enemies = [e for e in self.enemies if e.alive]

        # 11. Combo decay timer
        if self.combo > 0:
            self.combo_timer -= dt
            if self.combo_timer <= 0:
                self.combo = 0

        # 12. Check Boss Defeat / Victory
        if self.boss_spawned and self.boss and not self.boss.alive:
            if not self.is_mission_complete:
                self.is_mission_complete = True
                self.audio.stop_engine_sound()
                self.audio.play_sound("menu_confirm")
                self.state = STATE_VICTORY

        # 13. Particles & Effects update
        self.particles.update(dt)

    def _handle_enemy_destroyed(self, enemy: Enemy, pts: int) -> None:
        """Process enemy destruction, combo multiplier, sound, and score."""
        self.combo += 1
        self.max_combo = max(self.max_combo, self.combo)
        self.combo_timer = 3.2

        multiplier = 1.0 + (self.combo * 0.1)
        awarded_score = int(pts * multiplier)
        self.score += awarded_score

        if enemy.is_boss:
            # Huge boss explosion sequence
            self.particles.create_explosion(enemy.x, enemy.y, size_multiplier=3.2)
            self.particles.create_explosion(enemy.x - 80, enemy.y - 40, size_multiplier=2.5)
            self.particles.create_explosion(enemy.x + 80, enemy.y + 40, size_multiplier=2.5)
            self.audio.play_sound("boss_explosion")
            self.particles.add_floating_text(enemy.x, enemy.y - 60, f"+{awarded_score} BOSS ELIMINATED!", size=32)
        else:
            self.particles.create_explosion(enemy.x, enemy.y, size_multiplier=1.3)
            self.audio.play_sound("explosion")
            self.particles.add_floating_text(enemy.x, enemy.y - 20, f"+{awarded_score}")

        if self.combo in (3, 5, 10, 15, 20):
            self.audio.play_sound("combo")

    def _update_enemy_spawning(self, dt: float) -> None:
        """Spawn enemy waves systematically."""
        if self.boss_spawned:
            return

        self.wave_timer += dt
        self.wave_spawn_delay -= dt

        if self.wave == 1:
            # Wave 1: Scout Squadrons (Total 8 scouts)
            if self.wave_spawn_delay <= 0 and self.wave_enemies_spawned < 8:
                self.wave_spawn_delay = random.uniform(1.2, 2.0)
                y_coord = random.uniform(120, SCREEN_HEIGHT - 120)
                pat = random.choice(["sine", "dive"])
                self.enemies.append(ScoutFighter(SCREEN_WIDTH + 80, y_coord, pattern=pat))
                self.wave_enemies_spawned += 1
            elif self.wave_enemies_spawned >= 8 and len(self.enemies) == 0:
                self.wave = 2
                self.wave_enemies_spawned = 0
                self.wave_spawn_delay = 2.0
                self.particles.add_floating_text(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2, "WAVE 02: INTERCEPTORS!", size=28)

        elif self.wave == 2:
            # Wave 2: Interceptors + Scouts (Total 10)
            if self.wave_spawn_delay <= 0 and self.wave_enemies_spawned < 10:
                self.wave_spawn_delay = random.uniform(1.4, 2.2)
                y_coord = random.uniform(100, SCREEN_HEIGHT - 100)
                if self.wave_enemies_spawned % 2 == 0:
                    self.enemies.append(Interceptor(SCREEN_WIDTH + 80, y_coord))
                else:
                    self.enemies.append(ScoutFighter(SCREEN_WIDTH + 80, y_coord, pattern="sine"))
                self.wave_enemies_spawned += 1
            elif self.wave_enemies_spawned >= 10 and len(self.enemies) == 0:
                self.wave = 3
                self.wave_enemies_spawned = 0
                self.wave_spawn_delay = 2.0
                self.particles.add_floating_text(SCREEN_WIDTH // 2 - 120, SCREEN_HEIGHT // 2, "WAVE 03: HEAVY BOMBERS!", size=28)

        elif self.wave == 3:
            # Wave 3: Heavy Bomber Mini-boss + Escort fighters
            if self.wave_spawn_delay <= 0 and self.wave_enemies_spawned < 6:
                self.wave_spawn_delay = random.uniform(2.2, 3.2)
                if self.wave_enemies_spawned == 0 or self.wave_enemies_spawned == 3:
                    self.enemies.append(HeavyBomber(SCREEN_WIDTH + 140, SCREEN_HEIGHT * 0.35))
                else:
                    self.enemies.append(Interceptor(SCREEN_WIDTH + 80, random.uniform(150, SCREEN_HEIGHT - 150)))
                self.wave_enemies_spawned += 1
            elif self.wave_enemies_spawned >= 6 and len(self.enemies) == 0:
                # BOSS WARNING
                self.boss_spawned = True
                self.audio.play_boss_alarm()
                self.audio.play_sound("warning")
                self.particles.trigger_shake(magnitude=12.0, duration=1.2)
                self.boss = DreadnoughtBoss()
                self.enemies.append(self.boss)
                self.particles.add_floating_text(SCREEN_WIDTH // 2 - 160, SCREEN_HEIGHT // 2, "⚠ ABNORMAL RADAR CONTACT! ⚠", size=32)

    def render(self, display_surface: pygame.Surface) -> None:
        """Render active state onto screen."""
        shake_offset = (0, 0)
        if self.settings.get("screen_shake_enabled", True):
            shake_offset = self.particles.get_shake_offset()

        # Temporary drawing surface for applying camera shake
        draw_surf = display_surface
        if shake_offset != (0, 0):
            draw_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

        # Render State
        if self.state == STATE_PLAYING:
            self._render_playing(draw_surf)
        elif self.state == STATE_MENU:
            self.bg_manager.render(draw_surf)
            webcam_ok = self.hand_controller.webcam_connected
            hand_ok = self.hand_controller.hand_detected
            self.ui.render_main_menu(draw_surf, self.menu_index, self.menu_items, webcam_ok, hand_ok)
        elif self.state == STATE_BACKGROUND_SELECT:
            self.ui.render_background_selection(draw_surf)
        elif self.state == STATE_CALIBRATION:
            preview = self.hand_controller.get_preview_surface()
            self.ui.render_calibration(
                draw_surf,
                preview,
                self.hand_controller.hand_detected,
                self.hand_controller.is_firing(),
                self.hand_controller.extended_fingers_count,
                self.hand_controller.pinch_distance
            )
        elif self.state == STATE_PAUSED:
            if self.player:
                self._render_playing(draw_surf)
            self.ui.render_pause_menu(draw_surf, self.pause_index, self.pause_options)
        elif self.state == STATE_GAME_OVER:
            self.bg_manager.render(draw_surf)
            self.particles.render(draw_surf)
            self.ui.render_game_over(draw_surf, self.score, self.max_combo)
        elif self.state == STATE_VICTORY:
            if self.player:
                self._render_playing(draw_surf)
            self.ui.render_victory(draw_surf, self.score, self.max_combo)
        elif self.state == STATE_SETTINGS:
            self.ui.render_settings(draw_surf, self.settings_index)

        # Apply screen shake offset if active
        if shake_offset != (0, 0):
            display_surface.fill((0, 0, 0))
            display_surface.blit(draw_surf, shake_offset)

    def _render_playing(self, surface: pygame.Surface) -> None:
        """Render active combat scene and HUD."""
        # 1. Scrolling background
        self.bg_manager.render(surface)

        # 2. Projectiles
        for p in self.player_projectiles:
            p.render(surface)
        for ep in self.enemy_projectiles:
            ep.render(surface)

        # 3. Enemies
        for e in self.enemies:
            e.render(surface)

        # 4. Player aircraft
        if self.player:
            self.player.render(surface)

        # 5. Explosions and particles
        self.particles.render(surface)

        # 6. Combat HUD
        if self.player:
            self.ui.render_hud(
                surface,
                score=self.score,
                armor=self.player.armor,
                max_armor=self.player.max_armor,
                current_weapon=self.player.current_weapon,
                ammo=self.player.ammo_counts[self.player.current_weapon],
                combo=self.combo,
                combo_timer=self.combo_timer,
                wave=self.wave,
                boss=self.boss if (self.boss_spawned and self.boss and self.boss.alive) else None,
                hand_detected=self.hand_controller.hand_detected
            )

    def cleanup(self) -> None:
        """Clean shutdown of background threads and audio."""
        self.hand_controller.stop()
        self.audio.stop_engine_sound()
        self.audio.stop_music()
        save_settings(self.settings)
