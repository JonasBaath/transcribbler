"""Enumerate all visible top-level windows."""
import ctypes
from ctypes import wintypes
import psutil

user32 = ctypes.WinDLL("user32", use_last_error=True)
EnumWindows = user32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
GetWindowTextW = user32.GetWindowTextW
GetWindowTextLengthW = user32.GetWindowTextLengthW
IsWindowVisible = user32.IsWindowVisible
GetClassNameW = user32.GetClassNameW
GetWindowThreadProcessId = user32.GetWindowThreadProcessId
GetWindow = user32.GetWindow
GW_OWNER = 4

out = []
def cb(hwnd, _l):
    if not IsWindowVisible(hwnd):
        return True
    n = GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(max(n,1) + 1)
    GetWindowTextW(hwnd, buf, max(n,1) + 1)
    title = buf.value
    cls = ctypes.create_unicode_buffer(256)
    GetClassNameW(hwnd, cls, 256)
    pid = wintypes.DWORD()
    GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    owner = GetWindow(hwnd, GW_OWNER)
    out.append((hwnd, title, cls.value, pid.value, owner))
    return True
EnumWindows(EnumWindowsProc(cb), 0)
out.sort(key=lambda x: (x[3], x[0]))
print(f"{'HWND':>8} {'PID':>6} {'PROC':<25} {'OWNER':>8} {'CLASS':<35} TITLE")
for hwnd, title, cls, pid, owner in out:
    try: pname = psutil.Process(pid).name()
    except Exception: pname = "?"
    print(f"{hwnd:>8} {pid:>6} {pname:<25} {owner:>8} {cls[:34]:<35} {title!r}")
