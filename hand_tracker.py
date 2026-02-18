import cv2
import mediapipe as mp

class HandTracker:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands()
        self.mp_draw = mp.solutions.drawing_utils

    def get_hand_position(self):
        success, img = self.cap.read()
        if not success:
            return None

        img = cv2.flip(img, 1)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = self.hands.process(img_rgb)

        if results.multi_hand_landmarks:
            for handLms in results.multi_hand_landmarks:
                h, w, _ = img.shape
                lm = handLms.landmark[8]  # index finger tip
                cx, cy = int(lm.x * w), int(lm.y * h)
                return cy  # return Y position

        return None
