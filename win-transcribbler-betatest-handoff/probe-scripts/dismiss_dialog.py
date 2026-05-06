"""Dismiss the Välj projektmapp dialog by HWND."""
import sys, ctypes
from ctypes import wintypes
user32 = ctypes.WinDLL("user32", use_last_error=True)
WM_CLOSE = 0x0010
hwnd = int(sys.argv[1])
ok = user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
print(f"PostMessage WM_CLOSE to HWND {hwnd}: {'ok' if ok else 'failed'}")
