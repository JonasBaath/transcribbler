"""Trigger Electron pickFolder() and inspect resulting dialog window."""
import json, threading, time, urllib.request, ctypes
from ctypes import wintypes
import websocket

CDP_PORT = 9223

# --- Win32 helpers ---
user32 = ctypes.WinDLL("user32", use_last_error=True)
EnumWindows = user32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
GetWindowTextW = user32.GetWindowTextW
GetWindowTextLengthW = user32.GetWindowTextLengthW
IsWindowVisible = user32.IsWindowVisible
GetClassNameW = user32.GetClassNameW
GetWindowThreadProcessId = user32.GetWindowThreadProcessId
PostMessageW = user32.PostMessageW
WM_CLOSE = 0x0010

def enum_top_windows():
    out = []
    def cb(hwnd, _l):
        if not IsWindowVisible(hwnd):
            return True
        n = GetWindowTextLengthW(hwnd)
        if n == 0:
            return True
        buf = ctypes.create_unicode_buffer(n + 1)
        GetWindowTextW(hwnd, buf, n + 1)
        title = buf.value
        cls = ctypes.create_unicode_buffer(256)
        GetClassNameW(hwnd, cls, 256)
        pid = wintypes.DWORD()
        GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        out.append((hwnd, title, cls.value, pid.value))
        return True
    EnumWindows(EnumWindowsProc(cb), 0)
    return out

import psutil  # may not be installed; fallback to wmic if needed
def proc_name(pid):
    try:
        return psutil.Process(pid).name()
    except Exception:
        return "?"

# --- CDP setup ---
targets = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json").read())
page = next(t for t in targets if t["type"] == "page")
ws = websocket.create_connection(page["webSocketDebuggerUrl"], timeout=10)
mid = 0
def call(method, params=None, await_promise=False):
    global mid
    mid += 1
    p = params or {}
    if await_promise:
        p["awaitPromise"] = True
    ws.send(json.dumps({"id": mid, "method": method, "params": p}))
    while True:
        msg = json.loads(ws.recv())
        if msg.get("id") == mid:
            return msg

call("Runtime.enable")

# Baseline windows
before = enum_top_windows()
before_set = {hwnd for hwnd, *_ in before}
print(f"Baseline visible top-level windows: {len(before)}")

# Fire pickFolder() in renderer — non-blocking from our side
result_holder = {}
def fire():
    r = call("Runtime.evaluate", {
        "expression": "window.electronAPI.pickFolder()",
        "returnByValue": True,
    }, await_promise=True)
    result_holder["resp"] = r

t = threading.Thread(target=fire, daemon=True)
t.start()

# Poll for new dialog (up to 5s)
new_dialog = None
deadline = time.time() + 5.0
while time.time() < deadline:
    time.sleep(0.3)
    cur = enum_top_windows()
    diff = [w for w in cur if w[0] not in before_set]
    # Filter to plausible dialog windows (skip electron's own main window which we already had)
    if diff:
        new_dialog = diff
        break

if not new_dialog:
    print("No new top-level window appeared within 5s.")
else:
    print(f"\n=== New top-level window(s) after pickFolder() ===")
    for hwnd, title, cls, pid in new_dialog:
        pname = proc_name(pid)
        print(f"  HWND={hwnd}  pid={pid} ({pname})")
        print(f"    title: {title!r}")
        print(f"    class: {cls!r}")

    # Dismiss the dialog by posting WM_CLOSE to each new window
    for hwnd, *_ in new_dialog:
        PostMessageW(hwnd, WM_CLOSE, 0, 0)

# Wait for the CDP call to return
t.join(timeout=10)
resp = result_holder.get("resp")
if resp:
    val = resp.get("result", {}).get("result", {}).get("value")
    print(f"\npickFolder() resolved to: {val!r}  (empty string = canceled)")
else:
    print("\npickFolder() did not resolve within 10s after dismiss.")

ws.close()
