# AIR STRIKE: OPERATION SLUG WING
### Hand-Controlled Retro Military Arcade Aircraft Shooter

A complete, high-intensity 90s military arcade aircraft combat game inspired by the aesthetic of classic SNK arcade titles such as *Metal Slug*. Control an agile combat aircraft using real-time webcam hand tracking or seamless keyboard controls, battle waves of enemy jet fighters, dodge bullet curtains, and defeat the massive airborne Dreadnought boss.

---

## 🎮 Features

- **Real-Time Hand Tracking**: Powered by OpenCV and MediaPipe Hands with low-latency threaded tracking and coordinate smoothing.
- **Pinch-to-Fire & Gesture Loadout**:
  - Pinch thumb and index finger to fire.
  - Raise 1 finger for Vulcan Cannon, 2 fingers for Homing Missiles, 3 fingers for Plasma Laser Beam.
- **Mandatory Airspace Selection**: Choose your mission combat background before starting, featuring auto-discovery of all `.jpg`, `.png`, and `.webp` backgrounds in the project.
- **Metal Slug Arcade Aesthetic**: Clean military status panels, hazard stripes, floating score counters, combo multipliers, screen shake, and authentic challenge (no crosshair: aim with your aircraft).
- **Asset-First Design**: Custom animated aircraft sprites (`plane1.gif`, `plane2.gif`, `bossplane2.gif`), the 40-frame Dreadnought boss (`bossplane1.gif`), genuine vulcan sound effects (`gun.wav`), turbine engine sound (`planesound.wav`), boss alarm (`bossplanesound.wav`), and arcade soundtrack (`bgm.mp3`).
- **Complete Procedural Audio Fallback**: Synthesized retro sound effects for explosions, missile launches, laser blasts, hit impacts, and warning sirens.
- **Robust Keyboard Fallback**: Completely playable without a webcam.

---

## 💻 System Requirements

- **Python**: 3.11 or 3.12+ (64-bit)
- **OS**: Windows 10/11, macOS, Linux
- **Webcam**: Any standard 720p or 1080p USB or integrated webcam (optional, keyboard fallback included)

---

## 📦 Installation

1. Navigate to the game directory:
   ```bash
   cd metal_slug
   ```

2. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```
   *(Or using the Python Launcher: `py -m pip install -r requirements.txt`)*

---

## 🚀 How to Run

Run the game directly with Python:

```bash
python main.py
```
*(Or on Windows: `py main.py`)*

---

## ✋ Controls Guide

### Hand Tracking Controls (Webcam)
| Action | Gesture |
| :--- | :--- |
| **Steer Aircraft** | Move hand across camera view (aircraft follows smoothly) |
| **Fire Weapons** | Pinch Thumb tip + Index fingertip together |
| **Vulcan Cannon** | Extend 1 finger (Index) |
| **Homing Missiles** | Extend 2 fingers (Index + Middle) |
| **Plasma Laser** | Extend 3 fingers (Index + Middle + Ring) |

### Keyboard Fallback Controls
| Key | Action |
| :--- | :--- |
| **W, A, S, D** or **Arrow Keys** | Move aircraft in 8 directions |
| **SPACEBAR** | Fire active weapon |
| **1** | Select Vulcan Machine Gun |
| **2** | Select Homing Missiles |
| **3** | Select Plasma Laser Beam |
| **ESC** | Pause Mission / Return |
| **R** | Quick Retry Mission |
| **F11** | Toggle Fullscreen |

---

## 🖼️ Background Selection Screen

Before every mission, the game presents the **SELECT MISSION AIRSPACE** screen:
- Browse real-time thumbnails of all available background images (`background1.jpg`, `background2.jpg`, etc.).
- Use **Left / Right Arrow Keys** to cycle through airspaces.
- Press **ENTER** or **SPACEBAR** to confirm and start the mission.
- Any new image (`.jpg`, `.png`, `.webp`) placed in the project or `assets/backgrounds/` will be automatically detected and made selectable without changing any code.

---

## 📁 Project Structure

```
metal_slug/
├── main.py                 # Main application entry point & 60 FPS game loop
├── config.py               # Constants, colors, weapon stats, settings loader
├── requirements.txt        # Python dependency manifest
├── README.md               # Complete game documentation & guide
├── background1.jpg         # Desert canyon combat background
├── background2.jpg         # Mountain fortress dusk background
├── bgm.mp3                 # Epic military arcade soundtrack
├── bossplane1.gif          # 40-frame Dreadnought Stage Boss
├── bossplane2.gif          # Heavy Gunship escort mini-boss
├── bossplanesound.wav      # Dreadnought turbine roar & warning sound
├── crosshair.png           # Tactical military HUD reticle
├── gun.wav                 # Heavy vulcan machine gun sound effect
├── gunhandle.gif           # 39-frame recoiling cockpit turret animation
├── plane1.gif              # Agile Slug Fighter / Scout jet
├── plane2.gif              # Heavy Falcon Interceptor jet
├── planesound.wav          # Jet engine loop audio
├── game/
│   ├── __init__.py
│   ├── game.py             # Main game orchestrator & wave manager
│   ├── player.py           # Player aircraft, weapons, tilt banking
│   ├── enemy.py            # Scout, Interceptor, Bomber, Dreadnought Boss
│   ├── projectile.py       # Vulcan tracers, Homing Missiles, Plasma Lasers
│   ├── animation.py        # Pillow GIF frame extractor & cache
│   ├── particles.py        # Arcade explosions, smoke trails, screen shake
│   ├── collision.py        # Hitbox collision & blast radius logic
│   ├── hand_controller.py  # OpenCV & MediaPipe Hands threaded tracker
│   ├── audio_manager.py    # Multi-channel audio mixer & procedural synth
│   ├── background_manager.py # Auto-discovery & parallax scrolling
│   └── ui.py               # Retro Metal Slug HUD, menus, calibration
└── data/
    └── config.json         # Persisted player settings & preferences
```

---

## ⚙️ Configuration & Settings

Settings are automatically saved to `data/config.json`:
- **Master / SFX / Music Volume**: Audio volume balancing.
- **Hand Sensitivity**: Multiplier for hand movement range.
- **Hand Smoothing**: Exponential moving average coefficient (0.2 to 0.9).
- **Show Webcam Overlay**: Toggles the picture-in-picture camera feed in the bottom-right corner.
- **Screen Shake**: Toggles dramatic impact camera shake.

---

## 🔧 Troubleshooting

1. **"Webcam Not Found"**:
   - Verify that your camera is not being used by another application (Zoom, Teams, Browser).
   - The game will automatically enable **Keyboard Control** so you can play immediately.
2. **Camera Lag / Low FPS**:
   - The camera capture and hand detection runs on an isolated background thread, so your game render loop remains at a solid 60 FPS.
   - Adjust `HAND SENSITIVITY` and `HAND SMOOTHING` in the Settings menu for your room lighting.
3. **No Sound**:
   - Ensure your default audio device is active. The engine catches all audio driver issues silently and will never crash if sound hardware is absent.

---

## 📦 Packaging to Standalone Windows EXE

To create a single portable executable using PyInstaller:

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```

2. Build the executable:
   ```bash
   pyinstaller --noconfirm --onedir --windowed --add-data "*.gif;." --add-data "*.jpg;." --add-data "*.png;." --add-data "*.wav;." --add-data "*.mp3;." main.py -n "SlugWing"
   ```

3. The generated standalone game will be located in the `dist/SlugWing/` folder.
