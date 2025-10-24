
import cv2
from gaze_tracking import GazeTracking
from cursor_control import CursorController
import time

gaze = GazeTracking()
webcam = cv2.VideoCapture(0)
cursor = CursorController()
screen_w, screen_h = cursor.get_screen_size()

# Simple exponential moving average smoother for gaze ratios
class RatioSmoother:
	def __init__(self, alpha: float = 0.25):
		self.alpha = alpha
		self._x = None
		self._y = None

	def update(self, rx, ry):
		if rx is None or ry is None:
			return self._x, self._y
		if self._x is None:
			self._x = rx
			self._y = ry
		else:
			self._x = self.alpha * rx + (1 - self.alpha) * self._x
			self._y = self.alpha * ry + (1 - self.alpha) * self._y
		return self._x, self._y

smoother = RatioSmoother(alpha=0.15)
control_enabled = False
last_toggle_time = 0
TOGGLE_COOLDOWN_SEC = 0.5

# Absolute mapping sensitivity settings (iris-based)
SENS_GAIN_X = 2.2  # >1 increases sensitivity around center
SENS_GAIN_Y = 2.2  # >1 increases sensitivity around center

# Neutral center calibration for ratios (set via hotkey 'C')
center_rx = 0.5
center_ry = 0.5

# Pixel position EMA smoother
px_smooth = None  # (x, y)
PIXEL_EMA_ALPHA = 0.25

while True:
    # We get a new frame from the webcam
    _, frame = webcam.read()

    # We send this frame to GazeTracking to analyze it
    gaze.refresh(frame)

    frame = gaze.annotated_frame()
    
    # Resize frame to make it larger (increase scale for bigger window)
    # Scale factor: 1.5 = 150% larger, 2.0 = 200% larger, etc.
    scale_factor = 1.2
    width = int(frame.shape[1] * scale_factor)
    height = int(frame.shape[0] * scale_factor)
    frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_LINEAR)
    
    text = ""

    if gaze.is_blinking():
        text = "Blinking"
    elif gaze.is_right():
        text = "Looking right"
    elif gaze.is_left():
        text = "Looking left"
    elif gaze.is_center():
        text = "Looking center"

    cv2.putText(frame, text, (90, 60), cv2.FONT_HERSHEY_DUPLEX, 1.6, (147, 58, 31), 2)

    left_pupil = gaze.pupil_left_coords()
    right_pupil = gaze.pupil_right_coords()
    cv2.putText(frame, "Left pupil:  " + str(left_pupil), (90, 130), cv2.FONT_HERSHEY_DUPLEX, 0.9, (147, 58, 31), 1)
    cv2.putText(frame, "Right pupil: " + str(right_pupil), (90, 165), cv2.FONT_HERSHEY_DUPLEX, 0.9, (147, 58, 31), 1)

    # Absolute iris-based mapping with sensitivity gain and light smoothing
    if control_enabled:
        rx = gaze.horizontal_ratio()
        ry = gaze.vertical_ratio()
        if rx is not None and ry is not None:
            # apply linear sensitivity around 0.5, then clamp
            adj_rx = 0.5 + SENS_GAIN_X * (rx - center_rx)
            adj_ry = 0.5 + SENS_GAIN_Y * (ry - center_ry)
            if adj_rx < 0.0:
                adj_rx = 0.0
            elif adj_rx > 1.0:
                adj_rx = 1.0
            if adj_ry < 0.0:
                adj_ry = 0.0
            elif adj_ry > 1.0:
                adj_ry = 1.0

            target_x = (1.0 - adj_rx) * (screen_w - 1)
            target_y = adj_ry * (screen_h - 1)

            # pixel-space EMA smoothing
            if px_smooth is None:
                px_smooth = (target_x, target_y)
            else:
                px_smooth = (
                    PIXEL_EMA_ALPHA * target_x + (1 - PIXEL_EMA_ALPHA) * px_smooth[0],
                    PIXEL_EMA_ALPHA * target_y + (1 - PIXEL_EMA_ALPHA) * px_smooth[1],
                )

            cursor.move_to(int(px_smooth[0]), int(px_smooth[1]))

    # Show help overlay and toggle status
    status = "ON" if control_enabled else "OFF"
    cv2.putText(frame, f"Eye mouse: {status} (Space toggle)", (90, 200), cv2.FONT_HERSHEY_DUPLEX, 0.9, (0, 120, 0), 1)
    if control_enabled:
        cv2.putText(frame, f"Mode: ABSOLUTE iris  GX {SENS_GAIN_X:.1f} GY {SENS_GAIN_Y:.1f}", (90, 230), cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 120, 0), 1)
        cv2.putText(frame, f"Center rx {center_rx:.2f} ry {center_ry:.2f}  [/] Y  -/= X  C center  R reset", (90, 260), cv2.FONT_HERSHEY_DUPLEX, 0.6, (0, 120, 0), 1)

    cv2.imshow("Demo", frame)

    key = cv2.waitKey(1) & 0xFF
    now = time.time()
    if key == 27:
        break
    elif key == 32 and (now - last_toggle_time) > TOGGLE_COOLDOWN_SEC:
        control_enabled = not control_enabled
        last_toggle_time = now
    elif key == ord('['):
        SENS_GAIN_Y = max(1.0, SENS_GAIN_Y - 0.1)
    elif key == ord(']'):
        SENS_GAIN_Y = min(3.0, SENS_GAIN_Y + 0.1)
    elif key == ord('-'):
        SENS_GAIN_X = max(1.0, SENS_GAIN_X - 0.1)
    elif key == ord('='):
        SENS_GAIN_X = min(3.0, SENS_GAIN_X + 0.1)
    elif key in (ord('c'), ord('C')):
        # Set current gaze as neutral center
        rx = gaze.horizontal_ratio()
        ry = gaze.vertical_ratio()
        if rx is not None and ry is not None:
            center_rx = rx
            center_ry = ry
            # reset pixel smoother to avoid jump
            px_smooth = None
    elif key in (ord('r'), ord('R')):
        # Reset calibration and gains
        center_rx = 0.5
        center_ry = 0.5
        SENS_GAIN_X = 2.0
        SENS_GAIN_Y = 2.2
        px_smooth = None
   
webcam.release()
cv2.destroyAllWindows()
