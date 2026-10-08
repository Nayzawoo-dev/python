"""
Configuration module for the Metal Slug-inspired Retro Arcade Aircraft Game.
Contains display settings, color palettes, paths, weapon stats, and state definitions.
"""

from pathlib import Path
import json
import os

# Base directory relative to this file
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CONFIG_FILE = DATA_DIR / "config.json"

# Screen and Display Settings
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
TITLE = "AIR STRIKE: OPERATION SLUG WING"

# Retro Military Arcade Color Palette (Metal Slug Style)
COLOR_BLACK = (10, 12, 16)
COLOR_DARK_GREEN = (28, 43, 26)
COLOR_MILITARY_GREEN = (45, 68, 42)
COLOR_OLIVE = (85, 107, 47)
COLOR_KHAKI = (189, 175, 128)
COLOR_AMBER = (255, 191, 0)
COLOR_ORANGE = (255, 128, 0)
COLOR_RED = (220, 20, 60)
COLOR_DARK_RED = (139, 0, 0)
COLOR_CRIMSON = (237, 41, 57)
COLOR_WHITE = (245, 245, 245)
COLOR_GRAY = (128, 128, 136)
COLOR_STEEL = (70, 80, 95)
COLOR_CYAN = (0, 230, 255)
COLOR_YELLOW = (255, 220, 0)
COLOR_HUD_PANEL = (20, 24, 28, 200)
COLOR_HUD_BORDER = (230, 160, 20)

# Game States
STATE_MENU = "MENU"
STATE_BACKGROUND_SELECT = "BACKGROUND_SELECT"
STATE_AIRCRAFT_SELECT = "AIRCRAFT_SELECT"
STATE_CALIBRATION = "CALIBRATION"
STATE_PLAYING = "PLAYING"
STATE_PAUSED = "PAUSED"
STATE_GAME_OVER = "GAME_OVER"
STATE_VICTORY = "VICTORY"
STATE_SETTINGS = "SETTINGS"

# Weapon Types
WEAPON_MACHINE_GUN = "VULCAN CANNON"
WEAPON_MISSILE = "HOMING MISSILES"
WEAPON_LASER = "PLASMA BEAM"

WEAPONS_INFO = {
    WEAPON_MACHINE_GUN: {
        "name": "VULCAN CANNON",
        "description": "Rapid dual fire machine gun",
        "cooldown": 0.09,     # seconds between shots
        "damage": 16,
        "speed": 18,
        "color": COLOR_AMBER,
        "ammo": -1,           # infinite
        "gesture": "1 FINGER (INDEX)",
    },
    WEAPON_MISSILE: {
        "name": "HOMING MISSILES",
        "description": "Twin tracking warheads with blast radius",
        "cooldown": 0.45,
        "damage": 65,
        "speed": 11,
        "color": COLOR_ORANGE,
        "ammo": 30,
        "gesture": "2 FINGERS (INDEX + MIDDLE)",
    },
    WEAPON_LASER: {
        "name": "PLASMA BEAM",
        "description": "Continuous high-energy piercing laser",
        "cooldown": 0.16,
        "damage": 32,
        "speed": 30,
        "color": COLOR_CYAN,
        "ammo": 50,
        "gesture": "3 FINGERS (INDEX + MID + RING)",
    }
}

# Player Stats
PLAYER_DEFAULT_ARMOR = 100
PLAYER_SPEED = 9.0
PLAYER_INVULN_TIME = 1.8  # seconds after being hit
PLAYER_SCALE = 1.6        # sprite display scaling

# Hand Controller Settings
DEFAULT_SETTINGS = {
    "master_volume": 0.8,
    "sfx_volume": 0.85,
    "music_volume": 0.65,
    "hand_sensitivity": 1.25,
    "hand_smoothing": 0.65,
    "pinch_threshold": 0.055,
    "show_webcam_feed": True,
    "screen_shake_enabled": True,
    "fullscreen": False,
    "selected_background": "background1.jpg",
    "selected_aircraft": "plane1.gif",
    "camera_id": 0,
}

def load_settings() -> dict:
    """Load settings from config.json or return defaults."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                merged = {**DEFAULT_SETTINGS, **data}
                return merged
        except Exception as e:
            print(f"[CONFIG] Warning loading {CONFIG_FILE}: {e}")
    return DEFAULT_SETTINGS.copy()

def save_settings(settings: dict) -> None:
    """Save settings dictionary to config.json."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        print(f"[CONFIG] Error saving settings: {e}")
