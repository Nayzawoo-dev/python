import cv2
import mediapipe as mp
import pygame
import random

# --- Hand detection setup ---
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1)
mp_draw = mp.solutions.drawing_utils

# --- Pygame setup ---
pygame.init()
infoObject = pygame.display.Info()  # get screen size
screen_width = infoObject.current_w
screen_height = infoObject.current_h

# Fullscreen mode
screen = pygame.display.set_mode((screen_width, screen_height), pygame.FULLSCREEN)
pygame.display.set_caption("Hand Shooting Game")
clock = pygame.time.Clock()

# Bullet setup
bullets = []

# Target setup
target_pos = [random.randint(50, screen_width - 50), random.randint(50, screen_height - 50)]
target_radius = 30

# Score
score = 0

# --- OpenCV capture ---
cap = cv2.VideoCapture(0)

running = True
while running:
    ret, frame = cap.read()
    if not ret:
        break
    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb_frame)

    hand_x, hand_y = None, None

    # --- Hand detection ---
    if result.multi_hand_landmarks:
        for hand_landmarks in result.multi_hand_landmarks:
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            h, w, c = frame.shape
            # Scale hand coordinates to fullscreen
            hand_x = int(hand_landmarks.landmark[8].x * screen_width)
            hand_y = int(hand_landmarks.landmark[8].y * screen_height)

    # --- Pygame drawing ---
    screen.fill((0, 0, 0))

    # Draw target
    pygame.draw.circle(screen, (255, 0, 0), target_pos, target_radius)

    # Draw bullets
    for b in bullets:
        pygame.draw.circle(screen, (255, 255, 0), b, 5)
        b[1] -= 15  # bullet moves up faster
    bullets = [b for b in bullets if b[1] > 0]

    # Draw hand pointer
    if hand_x and hand_y:
        pygame.draw.circle(screen, (0, 255, 0), (hand_x, hand_y), 15)

    # Check collision
    for b in bullets:
        dist = ((b[0]-target_pos[0])**2 + (b[1]-target_pos[1])**2)**0.5
        if dist < target_radius:
            score += 1
            target_pos = [random.randint(50, screen_width - 50), random.randint(50, screen_height - 50)]
            bullets.remove(b)

    # --- Event handling ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if hand_x and hand_y:
                bullets.append([hand_x, hand_y])
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False  # ESC to exit

    # Display score
    font = pygame.font.SysFont(None, 48)
    text = font.render(f"Score: {score}", True, (255, 255, 255))
    screen.blit(text, (20, 20))

    pygame.display.flip()
    clock.tick(30)

    # Show webcam frame
    cv2.imshow("Hand Detection", frame)
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
pygame.quit()
