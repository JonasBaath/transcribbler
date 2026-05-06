"""Drive Electron renderer via CDP to verify folder-picker IPC."""
import json, sys, time, urllib.request
import websocket

CDP_PORT = 9223
targets = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json").read())
page = next(t for t in targets if t["type"] == "page")
ws_url = page["webSocketDebuggerUrl"]
print(f"Attaching to {page['url']}")

ws = websocket.create_connection(ws_url, timeout=10)
mid = 0
def call(method, params=None):
    global mid
    mid += 1
    ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
    while True:
        msg = json.loads(ws.recv())
        if msg.get("id") == mid:
            return msg

call("Runtime.enable")

probes = [
    "typeof window.electronAPI",
    "typeof window.electronAPI && Object.keys(window.electronAPI)",
    "typeof window.electronAPI && typeof window.electronAPI.pickFolder",
    "typeof window.electronAPI && window.electronAPI.platform",
]
print("\n=== Preload bridge probes ===")
for expr in probes:
    r = call("Runtime.evaluate", {"expression": expr, "returnByValue": True})
    val = r.get("result", {}).get("result", {}).get("value")
    print(f"  {expr!r}\n    -> {val!r}")

# Also probe what happens via the actual conditional pickFolder pattern from app.js
print("\n=== Branch the renderer would actually take ===")
r = call("Runtime.evaluate", {
    "expression": "window.electronAPI ? 'electron-ipc-path' : 'flask-fallback-path'",
    "returnByValue": True,
})
print(f"  -> {r.get('result',{}).get('result',{}).get('value')!r}")

ws.close()
print("\nProbe done (no dialog popped — preload-only check).")
