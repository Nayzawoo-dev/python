"""
Audio Manager for the Retro Arcade Aircraft Game.
Handles background music, sound effects, engine loops, procedural audio synthesis,
and volume controls with full error resilience.
"""

from pathlib import Path
from typing import Dict, Optional
import math
import numpy as np
import pygame
from config import BASE_DIR

class AudioManager:
    """Central audio system managing music, sound effects, and volume."""
    def __init__(self, settings: dict):
        self.settings = settings
        self.master_volume: float = settings.get("master_volume", 0.8)
        self.sfx_volume: float = settings.get("sfx_volume", 0.85)
        self.music_volume: float = settings.get("music_volume", 0.65)

        self.audio_enabled = False
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.channels: Dict[str, pygame.mixer.Channel] = {}
        self.engine_channel: Optional[pygame.mixer.Channel] = None
        self.boss_alarm_channel: Optional[pygame.mixer.Channel] = None
        self.is_engine_playing = False

        self._init_mixer()
        self._load_sounds()

    def _init_mixer(self) -> None:
        """Initialize the Pygame audio mixer safely."""
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            pygame.mixer.set_num_channels(32)
            self.audio_enabled = True
            self.engine_channel = pygame.mixer.Channel(0)
            self.boss_alarm_channel = pygame.mixer.Channel(1)
        except Exception as e:
            print(f"[AUDIO] Warning: Audio mixer could not be initialized: {e}")
            self.audio_enabled = False

    def _load_sounds(self) -> None:
        """Load provided user sound files and generate procedural sound effects."""
        if not self.audio_enabled:
            return

        # Attempt to load user-provided audio assets
        user_sound_files = {
            "gun": ["gun.wav", "assets/sounds/gun.wav"],
            "engine": ["planesound.wav", "assets/sounds/planesound.wav"],
            "boss_alarm": ["bossplanesound.wav", "assets/sounds/bossplanesound.wav"],
        }

        for sound_name, paths in user_sound_files.items():
            loaded = False
            for p in paths:
                full_path = BASE_DIR / p
                if full_path.exists():
                    try:
                        snd = pygame.mixer.Sound(str(full_path))
                        self.sounds[sound_name] = snd
                        loaded = True
                        break
                    except Exception as e:
                        print(f"[AUDIO] Error loading '{full_path}': {e}")
            if not loaded:
                print(f"[AUDIO] Missing '{sound_name}' sound, will use procedural generator.")

        # Synthesize missing arcade sound effects via NumPy
        self._synthesize_procedural_sounds()
        self.update_volumes()

    def _synthesize_procedural_sounds(self) -> None:
        """Generate classic 90s arcade sound effects procedurally."""
        sr = 44100

        # 1. Explosion sound (filtered noise + pitch drop rumble)
        if "explosion" not in self.sounds:
            dur = 0.65
            t = np.linspace(0, dur, int(sr * dur), False)
            noise = np.random.uniform(-1.0, 1.0, len(t))
            envelope = np.exp(-5.5 * t)
            # Low-frequency rumble sine
            rumble = np.sin(2 * np.pi * (70 * np.exp(-3 * t)) * t)
            waveform = (0.7 * noise + 0.5 * rumble) * envelope
            self.sounds["explosion"] = self._create_sound_from_waveform(waveform)

        # 2. Big Boss explosion sound
        if "boss_explosion" not in self.sounds:
            dur = 1.6
            t = np.linspace(0, dur, int(sr * dur), False)
            noise = np.random.uniform(-1.0, 1.0, len(t))
            envelope = np.exp(-2.2 * t)
            rumble = np.sin(2 * np.pi * (50 * np.exp(-1.5 * t)) * t)
            waveform = (0.75 * noise + 0.6 * rumble) * envelope
            self.sounds["boss_explosion"] = self._create_sound_from_waveform(waveform)

        # 3. Missile launch / rocket whoosh
        if "missile" not in self.sounds:
            dur = 0.4
            t = np.linspace(0, dur, int(sr * dur), False)
            freq = 350 + 200 * np.sin(2 * np.pi * 8 * t) - 150 * t
            sine = np.sin(2 * np.pi * freq * t)
            noise = np.random.uniform(-0.5, 0.5, len(t))
            envelope = np.sin(np.pi * t / dur) ** 0.5 * np.exp(-2 * t)
            waveform = (0.6 * sine + 0.5 * noise) * envelope
            self.sounds["missile"] = self._create_sound_from_waveform(waveform)

        # 4. Plasma Laser sound (high to low frequency sweep)
        if "laser" not in self.sounds:
            dur = 0.22
            t = np.linspace(0, dur, int(sr * dur), False)
            freq = 1400 * np.exp(-14 * t) + 180
            waveform = np.sin(2 * np.pi * freq * t) * np.exp(-8 * t)
            # Add harmonic
            waveform += 0.3 * np.sin(4 * np.pi * freq * t) * np.exp(-10 * t)
            self.sounds["laser"] = self._create_sound_from_waveform(waveform)

        # 5. Hit impact / metallic ricochet
        if "hit" not in self.sounds:
            dur = 0.12
            t = np.linspace(0, dur, int(sr * dur), False)
            freq = 800 * np.exp(-25 * t)
            noise = np.random.uniform(-0.6, 0.6, len(t))
            waveform = (0.5 * np.sin(2 * np.pi * freq * t) + 0.5 * noise) * np.exp(-22 * t)
            self.sounds["hit"] = self._create_sound_from_waveform(waveform)

        # 6. UI Menu Beep / Select
        if "menu_select" not in self.sounds:
            dur = 0.08
            t = np.linspace(0, dur, int(sr * dur), False)
            waveform = np.sin(2 * np.pi * 920 * t) * np.exp(-15 * t)
            self.sounds["menu_select"] = self._create_sound_from_waveform(waveform)

        # 7. UI Confirm / Mission Start
        if "menu_confirm" not in self.sounds:
            dur = 0.18
            t = np.linspace(0, dur, int(sr * dur), False)
            freq = np.where(t < 0.09, 650, 1050)
            waveform = np.sin(2 * np.pi * freq * t) * (1.0 - t / dur)
            self.sounds["menu_confirm"] = self._create_sound_from_waveform(waveform)

        # 8. Combo alert
        if "combo" not in self.sounds:
            dur = 0.22
            t = np.linspace(0, dur, int(sr * dur), False)
            freq = 523 + 400 * t
            waveform = np.sin(2 * np.pi * freq * t) * np.sin(np.pi * t / dur)
            self.sounds["combo"] = self._create_sound_from_waveform(waveform)

        # 9. Warning Klaxon
        if "warning" not in self.sounds:
            dur = 0.35
            t = np.linspace(0, dur, int(sr * dur), False)
            freq = 880 + 300 * np.sin(2 * np.pi * 6 * t)
            waveform = np.sign(np.sin(2 * np.pi * freq * t)) * 0.4
            self.sounds["warning"] = self._create_sound_from_waveform(waveform)

    def _create_sound_from_waveform(self, waveform: np.ndarray) -> pygame.mixer.Sound:
        """Convert a 1D float numpy array (-1.0 to 1.0) into a stereo Pygame Sound."""
        clamped = np.clip(waveform, -1.0, 1.0)
        int16_mono = (clamped * 32767).astype(np.int16)
        stereo = np.column_stack((int16_mono, int16_mono))
        return pygame.sndarray.make_sound(stereo)

    def update_volumes(self) -> None:
        """Apply current volume multipliers to mixer and active sounds."""
        if not self.audio_enabled:
            return

        effective_sfx = self.master_volume * self.sfx_volume
        effective_music = self.master_volume * self.music_volume

        for name, sound in self.sounds.items():
            if name == "engine":
                # Engine sound kept at gentle background level
                sound.set_volume(effective_sfx * 0.4)
            elif name == "boss_alarm":
                sound.set_volume(effective_sfx * 0.75)
            else:
                sound.set_volume(effective_sfx)

        try:
            pygame.mixer.music.set_volume(effective_music)
        except Exception:
            pass

    def play_sound(self, name: str) -> None:
        """Play a one-shot sound effect."""
        if not self.audio_enabled:
            return
        sound = self.sounds.get(name)
        if sound:
            try:
                sound.play()
            except Exception as e:
                print(f"[AUDIO] Error playing sound '{name}': {e}")

    def play_music(self, loop: bool = True) -> None:
        """Play background music track bgm.mp3 if available."""
        if not self.audio_enabled:
            return

        bgm_paths = [BASE_DIR / "bgm.mp3", BASE_DIR / "assets/sounds/bgm.mp3"]
        for p in bgm_paths:
            if p.exists():
                try:
                    pygame.mixer.music.load(str(p))
                    effective_music = self.master_volume * self.music_volume
                    pygame.mixer.music.set_volume(effective_music)
                    pygame.mixer.music.play(-1 if loop else 0)
                    return
                except Exception as e:
                    print(f"[AUDIO] Error loading bgm '{p}': {e}")

    def stop_music(self) -> None:
        """Stop background music."""
        if self.audio_enabled:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass

    def start_engine_sound(self) -> None:
        """Start playing player jet turbine sound on dedicated looping channel."""
        if not self.audio_enabled or self.is_engine_playing:
            return
        engine_sound = self.sounds.get("engine")
        if engine_sound and self.engine_channel:
            try:
                self.engine_channel.play(engine_sound, loops=-1)
                self.is_engine_playing = True
            except Exception:
                pass

    def stop_engine_sound(self) -> None:
        """Stop player jet engine loop."""
        if not self.audio_enabled or not self.is_engine_playing:
            return
        if self.engine_channel:
            try:
                self.engine_channel.stop()
                self.is_engine_playing = False
            except Exception:
                pass

    def play_boss_alarm(self) -> None:
        """Play dramatic boss entrance roar/alarm."""
        if not self.audio_enabled:
            return
        alarm = self.sounds.get("boss_alarm")
        if alarm and self.boss_alarm_channel:
            try:
                self.boss_alarm_channel.play(alarm, loops=0)
            except Exception:
                pass

    def set_master_volume(self, val: float) -> None:
        self.master_volume = max(0.0, min(1.0, val))
        self.update_volumes()

    def set_sfx_volume(self, val: float) -> None:
        self.sfx_volume = max(0.0, min(1.0, val))
        self.update_volumes()

    def set_music_volume(self, val: float) -> None:
        self.music_volume = max(0.0, min(1.0, val))
        self.update_volumes()
