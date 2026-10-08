"""
Hand Controller using OpenCV and MediaPipe Hands.
Provides threaded real-time hand tracking, gesture detection (pinch fire, finger weapon switch),
coordinate smoothing, webcam preview feed, and seamless keyboard fallback.
"""

from typing import Tuple, Optional, Dict
import threading
import time
import math
import numpy as np
import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT

# Graceful import of cv2 and mediapipe
OPENCV_AVAILABLE = False
MEDIAPIPE_AVAILABLE = False

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    print("[HAND_CTRL] OpenCV (cv2) is not available.")

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    print("[HAND_CTRL] MediaPipe is not available.")


class HandController:
    """Threaded real-time hand tracking and gesture recognition controller."""
    def __init__(self, settings: dict):
        self.settings = settings
        self.camera_id = settings.get("camera_id", 0)
        self.smoothing = settings.get("hand_smoothing", 0.65)
        self.sensitivity = settings.get("hand_sensitivity", 1.25)
        self.pinch_threshold = settings.get("pinch_threshold", 0.055)

        # State flags
        self.is_running = False
        self.webcam_connected = False
        self.hand_detected = False
        self.hand_tracking_available = OPENCV_AVAILABLE and MEDIAPIPE_AVAILABLE

        # Normalized coordinates (0.0 to 1.0)
        self.raw_x: float = 0.5
        self.raw_y: float = 0.5
        self.smooth_x: float = 0.5
        self.smooth_y: float = 0.5

        # Screen coordinates (0 to SCREEN_WIDTH, 0 to SCREEN_HEIGHT)
        self.screen_x: float = SCREEN_WIDTH * 0.25
        self.screen_y: float = SCREEN_HEIGHT * 0.5

        # Gestures
        self.is_pinching = False
        self.pinch_distance: float = 1.0
        self.extended_fingers_count: int = 1
        self.detected_weapon_index: int = 1  # 1: Vulcan, 2: Missile, 3: Laser

        # Threading and Webcam frame caching
        self.lock = threading.Lock()
        self.capture_thread: Optional[threading.Thread] = None
        self.latest_preview_surf: Optional[pygame.Surface] = None
        self.raw_landmarks_data = None

        if self.hand_tracking_available:
            self.start()

    def start(self) -> None:
        """Start the background camera tracking thread."""
        if self.is_running or not self.hand_tracking_available:
            return
        self.is_running = True
        self.capture_thread = threading.Thread(target=self._camera_worker, daemon=True)
        self.capture_thread.start()

    def stop(self) -> None:
        """Stop background worker thread."""
        self.is_running = False
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=1.0)

    def _camera_worker(self) -> None:
        """Background thread worker for OpenCV capture and MediaPipe inference."""
        cap = None
        try:
            cap = cv2.VideoCapture(self.camera_id)
            if not cap.isOpened():
                print(f"[HAND_CTRL] Warning: Cannot open camera ID {self.camera_id}")
                self.webcam_connected = False
                return

            # Set camera resolution to 640x480 for fast low-latency processing
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.webcam_connected = True

            mp_hands = mp.solutions.hands
            with mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                min_detection_confidence=0.55,
                min_tracking_confidence=0.55
            ) as hands:
                while self.is_running:
                    ret, frame = cap.read()
                    if not ret:
                        time.sleep(0.02)
                        continue

                    # Mirror horizontally for natural webcam mirror feel
                    frame = cv2.flip(frame, 1)
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    results = hands.process(rgb_frame)

                    hand_found = False
                    curr_x, curr_y = self.raw_x, self.raw_y
                    pinch = False
                    dist = 1.0
                    finger_count = 1
                    landmarks_list = None

                    if results.multi_hand_landmarks:
                        hand_found = True
                        hand_landmarks = results.multi_hand_landmarks[0]
                        landmarks_list = [(lm.x, lm.y, lm.z) for lm in hand_landmarks.landmark]

                        # Use palm center / index MCP (landmark 9) or wrist (0) and index (8) for stable position
                        palm_x = (hand_landmarks.landmark[0].x + hand_landmarks.landmark[9].x) / 2.0
                        palm_y = (hand_landmarks.landmark[0].y + hand_landmarks.landmark[9].y) / 2.0

                        # Apply sensitivity scaling relative to center
                        sens = self.settings.get("hand_sensitivity", 1.25)
                        adjusted_x = 0.5 + (palm_x - 0.5) * sens
                        adjusted_y = 0.5 + (palm_y - 0.5) * sens
                        curr_x = max(0.05, min(0.95, adjusted_x))
                        curr_y = max(0.05, min(0.95, adjusted_y))

                        # Pinch Detection: Thumb tip (4) to Index tip (8)
                        thumb_tip = hand_landmarks.landmark[4]
                        index_tip = hand_landmarks.landmark[8]
                        dist = math.hypot(thumb_tip.x - index_tip.x, thumb_tip.y - index_tip.y)
                        pinch = dist < self.settings.get("pinch_threshold", 0.055)

                        # Extended Fingers count for Weapon Selection:
                        # Index (8 vs 6), Middle (12 vs 10), Ring (16 vs 14), Pinky (20 vs 18)
                        idx_up = hand_landmarks.landmark[8].y < hand_landmarks.landmark[6].y
                        mid_up = hand_landmarks.landmark[12].y < hand_landmarks.landmark[10].y
                        ring_up = hand_landmarks.landmark[16].y < hand_landmarks.landmark[14].y
                        pinky_up = hand_landmarks.landmark[20].y < hand_landmarks.landmark[18].y

                        count = 0
                        if idx_up: count += 1
                        if mid_up: count += 1
                        if ring_up: count += 1
                        if pinky_up: count += 1
                        finger_count = max(1, min(3, count))

                        # Draw subtle military tracking overlay on camera preview frame
                        for lm in hand_landmarks.landmark:
                            px = int(lm.x * frame.shape[1])
                            py = int(lm.y * frame.shape[0])
                            cv2.circle(frame, (px, py), 3, (0, 255, 200), -1)

                    # Create small pygame preview surface (160x120 or 200x150)
                    preview_small = cv2.resize(frame, (200, 150))
                    preview_rgb = cv2.cvtColor(preview_small, cv2.COLOR_BGR2RGB)
                    preview_surf = pygame.image.frombuffer(preview_rgb.tobytes(), (200, 150), "RGB")

                    with self.lock:
                        self.hand_detected = hand_found
                        if hand_found:
                            self.raw_x = curr_x
                            self.raw_y = curr_y
                            self.is_pinching = pinch
                            self.pinch_distance = dist
                            self.extended_fingers_count = finger_count
                            if finger_count in (1, 2, 3):
                                self.detected_weapon_index = finger_count
                        else:
                            self.is_pinching = False

                        self.latest_preview_surf = preview_surf
                        self.raw_landmarks_data = landmarks_list

                    time.sleep(0.01)

        except Exception as e:
            print(f"[HAND_CTRL] Worker exception: {e}")
            self.webcam_connected = False
        finally:
            if cap:
                cap.release()

    def update(self, dt: float) -> None:
        """Update coordinate smoothing and map to game screen resolution."""
        alpha = self.settings.get("hand_smoothing", 0.65)
        # Smoothing: smooth = prev * alpha + raw * (1 - alpha)
        self.smooth_x = self.smooth_x * alpha + self.raw_x * (1.0 - alpha)
        self.smooth_y = self.smooth_y * alpha + self.raw_y * (1.0 - alpha)

        # Map to screen dimensions
        self.screen_x = self.smooth_x * SCREEN_WIDTH
        self.screen_y = self.smooth_y * SCREEN_HEIGHT

    def get_position(self) -> Tuple[float, float]:
        """Return smoothed aircraft target position (x, y)."""
        return self.screen_x, self.screen_y

    def is_firing(self) -> bool:
        """Return whether fire trigger is currently active."""
        return self.is_pinching

    def get_selected_weapon_index(self) -> int:
        """Return weapon index (1, 2, or 3) from finger gestures."""
        return self.detected_weapon_index

    def get_preview_surface(self) -> Optional[pygame.Surface]:
        """Return current webcam video frame preview surface."""
        with self.lock:
            if self.latest_preview_surf:
                return self.latest_preview_surf.copy()
        return None
