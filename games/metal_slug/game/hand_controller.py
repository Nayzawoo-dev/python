"""
Hand Controller using OpenCV and MediaPipe Hands.
Provides threaded real-time hand tracking, gesture-based weapon firing
(closed fist, two fingers, three fingers), coordinate smoothing,
webcam preview feed, and seamless keyboard fallback.
"""

from typing import Tuple, Optional
import threading
import time
import math
import numpy as np
import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT

# Weapon indices: 1 = Machine Gun, 2 = Missile Launcher, 3 = Laser Beam.
# Only these exact hand gestures activate a weapon.
WEAPON_BY_FINGER_COUNT = {
    0: 1,  # Closed fist -> Machine Gun
    2: 2,  # Two fingers -> Missile Launcher
    3: 3,  # Three fingers -> Laser Beam
}

# MediaPipe landmark chains for the four non-thumb fingers: (MCP, PIP, TIP)
FINGER_CHAINS = (
    (5, 6, 8),    # Index
    (9, 10, 12),  # Middle
    (13, 14, 16), # Ring
    (17, 18, 20), # Pinky
)

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
        self.extended_fingers_count: int = 0
        self.detected_weapon_index: int = 0  # 0: none, 1: Vulcan, 2: Missile, 3: Laser
        self.is_firing_gesture: bool = False

        # Gesture stability (avoids weapon flicker from noisy landmark frames)
        self._candidate_weapon_index: int = 0
        self._candidate_frames: int = 0

        # Threading and Webcam frame caching
        self.lock = threading.Lock()
        self.capture_thread: Optional[threading.Thread] = None
        self.latest_preview_surf: Optional[pygame.Surface] = None
        self.raw_landmarks_data = None

        if self.hand_tracking_available:
            self.start()

    @staticmethod
    def _distance(a, b) -> float:
        """2D Euclidean distance between two landmarks."""
        return math.hypot(a[0] - b[0], a[1] - b[1])

    @classmethod
    def _joint_angle(cls, a, b, c) -> float:
        """Return the angle in degrees at joint b formed by points a-b-c."""
        v1 = (a[0] - b[0], a[1] - b[1])
        v2 = (c[0] - b[0], c[1] - b[1])
        n1 = math.hypot(*v1)
        n2 = math.hypot(*v2)
        if n1 == 0.0 or n2 == 0.0:
            return 0.0
        cosine = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)))
        return math.degrees(math.acos(cosine))

    @classmethod
    def _is_finger_extended(cls, landmarks, mcp_idx: int, pip_idx: int, tip_idx: int) -> bool:
        """Rotation-tolerant finger extension test using joint straightness and reach."""
        wrist = landmarks[0]
        mcp = landmarks[mcp_idx]
        pip = landmarks[pip_idx]
        tip = landmarks[tip_idx]

        # A straight finger has an almost 180-degree angle at the PIP joint.
        if cls._joint_angle(mcp, pip, tip) < 150.0:
            return False

        # The fingertip must reach clearly beyond the PIP and MCP toward the wrist.
        tip_reach = cls._distance(wrist, tip)
        pip_reach = cls._distance(wrist, pip)
        mcp_reach = cls._distance(wrist, mcp)
        return tip_reach > pip_reach * 1.10 and tip_reach > mcp_reach * 1.25

    @classmethod
    def count_extended_fingers(cls, landmarks) -> int:
        """Count extended index/middle/ring/pinky fingers (thumb excluded)."""
        return sum(
            1 for mcp_idx, pip_idx, tip_idx in FINGER_CHAINS
            if cls._is_finger_extended(landmarks, mcp_idx, pip_idx, tip_idx)
        )

    @staticmethod
    def weapon_index_for_finger_count(finger_count: int) -> int:
        """Map an exact finger count to a weapon index, or 0 when invalid."""
        return WEAPON_BY_FINGER_COUNT.get(finger_count, 0)

    def _apply_gesture(self, finger_count: int) -> None:
        """Stabilize the detected gesture and update the active weapon/fire state."""
        weapon_index = self.weapon_index_for_finger_count(finger_count)

        if weapon_index == self._candidate_weapon_index:
            self._candidate_frames += 1
        else:
            self._candidate_weapon_index = weapon_index
            self._candidate_frames = 1
            # Stop firing immediately if the gesture changes or becomes invalid.
            self.is_firing_gesture = False

        # Require two consecutive frames so transient detection noise cannot
        # switch weapons or trigger a shot on its own.
        if self._candidate_frames >= 2:
            self.detected_weapon_index = weapon_index
            self.is_firing_gesture = weapon_index != 0

    def _clear_gesture(self) -> None:
        """Reset gesture state immediately when the hand is lost."""
        self.is_pinching = False
        self.is_firing_gesture = False
        self.detected_weapon_index = 0
        self.extended_fingers_count = 0
        self._candidate_weapon_index = 0
        self._candidate_frames = 0

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
                    finger_count = 0
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

                        # Pinch distance is kept for the calibration diagnostics.
                        thumb_tip = hand_landmarks.landmark[4]
                        index_tip = hand_landmarks.landmark[8]
                        dist = math.hypot(thumb_tip.x - index_tip.x, thumb_tip.y - index_tip.y)
                        pinch = dist < self.settings.get("pinch_threshold", 0.055)

                        # Exact non-thumb finger count drives weapon firing:
                        # fist (0) -> MG, two fingers -> Missile, three -> Laser.
                        finger_count = self.count_extended_fingers(landmarks_list)

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
                            self._apply_gesture(finger_count)
                        else:
                            self._clear_gesture()

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
        """Return True only while a valid weapon gesture is actively held."""
        return self.hand_detected and self.is_firing_gesture

    def get_selected_weapon_index(self) -> int:
        """Return weapon index (0 for none, 1, 2, or 3) from the gesture."""
        return self.detected_weapon_index if self.hand_detected else 0

    def get_preview_surface(self) -> Optional[pygame.Surface]:
        """Return current webcam video frame preview surface."""
        with self.lock:
            if self.latest_preview_surf:
                return self.latest_preview_surf.copy()
        return None
