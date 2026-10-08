"""
Main entry point for Operation Slug Wing: Retro Military Arcade Aircraft Game.
Initializes Pygame display, manages main loop at 60 FPS, and handles shutdown.
"""

import sys
import time
from pathlib import Path
import pygame

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE, load_settings, save_settings
from game.game import GameEngine

def main():
    # Initialize Pygame core
    pygame.init()
    pygame.display.set_caption(TITLE)

    settings = load_settings()

    # Setup display surface
    flags = pygame.DOUBLEBUF
    if settings.get("fullscreen", False):
        flags |= pygame.FULLSCREEN

    try:
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
    except Exception as e:
        print(f"[MAIN] Warning: Display mode failed with flags ({e}), falling back to standard window.")
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

    # Initialize Engine
    clock = pygame.time.Clock()
    engine = GameEngine(settings)

    running = True
    last_time = time.time()

    print("==================================================")
    print("  OPERATION SLUG WING : RETRO ARCADE COMBAT")
    print("  Hand-Controlled Military Aircraft Shooter")
    print("==================================================")
    print("Controls:")
    print("  - Hand Tracking: Move hand to steer aircraft")
    print("  - Fire Gesture: Pinch Thumb + Index finger")
    print("  - Weapons: 1 finger (Vulcan), 2 fingers (Missiles), 3 fingers (Laser)")
    print("  - Keyboard Fallback: WASD / Arrows to move, Space to fire")
    print("  - Keys 1/2/3 to switch weapon, ESC to pause, R to retry")
    print("==================================================")

    try:
        while running:
            current_time = time.time()
            dt = current_time - last_time
            last_time = current_time

            # Cap dt to prevent physics glitches if window paused or dragged
            dt = min(0.08, max(0.001, dt))

            # Event pump
            for event in pygame.event.get():
                if not engine.handle_event(event):
                    running = False
                    break

            if not running:
                break

            # Update & Render
            engine.update(dt)
            engine.render(screen)

            pygame.display.flip()
            clock.tick(FPS)

    except KeyboardInterrupt:
        print("\n[MAIN] User interrupted execution.")
    except Exception as e:
        import traceback
        print(f"[MAIN] Unexpected error in game loop: {e}")
        traceback.print_exc()
    finally:
        print("[MAIN] Cleaning up game engine resources...")
        engine.cleanup()
        pygame.quit()
        sys.exit(0)

if __name__ == "__main__":
    main()
