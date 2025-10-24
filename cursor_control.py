import ctypes


class CursorController:
	"""Simple Windows cursor controller using ctypes."""

	def __init__(self):
		self._user32 = ctypes.windll.user32
		self._screen_width = self._user32.GetSystemMetrics(0)
		self._screen_height = self._user32.GetSystemMetrics(1)

	def get_screen_size(self):
		return self._screen_width, self._screen_height

	def get_position(self):
		point = ctypes.wintypes.POINT()
		ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
		return point.x, point.y

	def move_to(self, x: int, y: int) -> None:
		# Clamp within screen bounds
		if x < 0:
			x = 0
		elif x >= self._screen_width:
			x = self._screen_width - 1
		if y < 0:
			y = 0
		elif y >= self._screen_height:
			y = self._screen_height - 1
		self._user32.SetCursorPos(int(x), int(y))

	def left_click(self) -> None:
		self._mouse_event(0x0002)  # MOUSEEVENTF_LEFTDOWN
		self._mouse_event(0x0004)  # MOUSEEVENTF_LEFTUP

	def right_click(self) -> None:
		self._mouse_event(0x0008)  # MOUSEEVENTF_RIGHTDOWN
		self._mouse_event(0x0010)  # MOUSEEVENTF_RIGHTUP

	def _mouse_event(self, event_flag: int) -> None:
		ctypes.windll.user32.mouse_event(event_flag, 0, 0, 0, 0)


