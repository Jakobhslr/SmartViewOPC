"""
api.py
SmartView OPC – REST-API mit SSE, OPC UA Subscription, Auth, Alarmen & Historisierung.
"""

import json
import os
import queue
import sys
import time
import threading
from functools import wraps

from flask import (Flask, Response, jsonify, redirect, request,
                   send_from_directory, session, stream_with_context)
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from opc_client import OPCUAClient
from db import init_db, log_values, get_history

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# ─── Flask ──────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "smartview-opc-2026")
CORS(app)

DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "smartview2026")

# ─── OPC Client ─────────────────────────────────────────────────
opc = OPCUAClient()

# ─── Shared State (thread-safe) ──────────────────────────────────
_state: dict = {}
_alarms: list = []
_state_lock = threading.Lock()
_sse_queues: list[queue.Queue] = []
_sse_lock = threading.Lock()
_log_counter = 0

# ─── Alarm-Schwellwerte ──────────────────────────────────────────
ALARM_CONFIG = [
    {"tag": "druck", "op": ">", "threshold": 9.0, "level": "critical", "msg": "Druck kritisch (> 9 bar)"},
    {"tag": "druck", "op": ">", "threshold": 8.0, "level": "warning",  "msg": "Druck hoch (> 8 bar)"},
]


def check_alarms(values: dict) -> list:
    active = []
    for cfg in ALARM_CONFIG:
        v = values.get(cfg["tag"])
        if v is None:
            continue
        if cfg["op"] == ">" and v > cfg["threshold"]:
            active.append({"level": cfg["level"], "msg": cfg["msg"]})
        elif cfg["op"] == "<" and v < cfg["threshold"]:
            active.append({"level": cfg["level"], "msg": cfg["msg"]})
    return active


def _push_sse(payload: dict) -> None:
    msg = f"data: {json.dumps(payload)}\n\n"
    with _sse_lock:
        for q in _sse_queues:
            try:
                q.put_nowait(msg)
            except queue.Full:
                pass


# ─── OPC UA Subscription Handler ────────────────────────────────
class _SubHandler:
    def __init__(self, node_map: dict):
        self._map = node_map  # NodeId → tag_name
        self._counter = 0

    def datachange_notification(self, node, val, data):
        global _log_counter
        tag = self._map.get(node.nodeid, str(node.nodeid))
        with _state_lock:
            _state[tag] = val
            snapshot = dict(_state)

        alarms = check_alarms(snapshot)
        with _state_lock:
            _alarms.clear()
            _alarms.extend(alarms)

        # Alle 10 Änderungen in DB schreiben (~10s)
        _log_counter += 1
        if _log_counter % 10 == 0:
            log_values(snapshot)

        _push_sse({"tags": snapshot, "alarms": alarms, "connected": True})


# ─── OPC Worker (Subscription + Reconnect) ──────────────────────
def _opc_worker() -> None:
    while True:
        if not opc.connected:
            ok = opc.connect()
            if not ok:
                _push_sse({"tags": {}, "alarms": [], "connected": False})
                time.sleep(5)
                continue

            try:
                node_map = {n.nodeid: name for name, n in opc.nodes.items()}
                handler = _SubHandler(node_map)
                sub = opc.client.create_subscription(1000, handler)
                sub.subscribe_data_change(list(opc.nodes.values()))
                print("[OPC] Subscription aktiv")
            except Exception as e:
                print(f"[OPC] Subscription fehlgeschlagen: {e}")
                opc.disconnect()
                time.sleep(5)
                continue

        # Verbindung alle 5s prüfen
        time.sleep(5)
        try:
            list(opc.nodes.values())[0].get_value()
        except Exception:
            print("[OPC] Verbindung verloren – reconnect...")
            opc.disconnect()
            _push_sse({"tags": {}, "alarms": [], "connected": False})


# ─── Auth ────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Nicht angemeldet"}), 401
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated


@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        if request.form.get("password", "") == DASHBOARD_PASSWORD:
            session["logged_in"] = True
            return redirect("/")
        error = "Falsches Passwort"

    return f"""<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SmartView OPC – Login</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/css/style.css">
  <style>
    .login-wrap{{display:flex;align-items:center;justify-content:center;min-height:100vh;position:relative;z-index:1}}
    .login-box{{background:rgba(17,24,39,.9);border:1px solid rgba(255,255,255,.08);border-radius:20px;padding:2.5rem;width:100%;max-width:380px;box-shadow:0 8px 40px rgba(0,0,0,.6)}}
    .login-brand{{font-size:1.1rem;font-weight:800;color:#f1f5f9;margin-bottom:2rem}}
    .login-accent{{color:#06b6d4}}
    .login-title{{font-size:1.5rem;font-weight:800;margin-bottom:.4rem}}
    .login-sub{{font-size:.85rem;color:#64748b;margin-bottom:2rem}}
    .login-label{{font-size:.75rem;font-weight:700;color:#94a3b8;letter-spacing:1px;text-transform:uppercase;margin-bottom:.5rem;display:block}}
    .login-input{{width:100%;padding:.8rem 1rem;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);border-radius:10px;color:#f1f5f9;font-size:1rem;font-family:Inter,sans-serif;margin-bottom:1.25rem;outline:none;box-sizing:border-box}}
    .login-input:focus{{border-color:#06b6d4;box-shadow:0 0 0 3px rgba(6,182,212,.15)}}
    .login-btn{{width:100%;padding:.85rem;background:linear-gradient(135deg,#0891b2,#06b6d4);border:none;border-radius:10px;color:#fff;font-size:1rem;font-weight:700;cursor:pointer;font-family:Inter,sans-serif}}
    .login-error{{color:#ef4444;font-size:.85rem;margin-bottom:1rem}}
  </style>
</head>
<body>
  <div class="login-wrap">
    <div class="login-box">
      <div class="login-brand">SmartView <span class="login-accent">OPC</span></div>
      <div class="login-title">Anmelden</div>
      <div class="login-sub">SCADA Dashboard · S7-1516</div>
      {"<div class='login-error'>✗ " + error + "</div>" if error else ""}
      <form method="post">
        <label class="login-label">Passwort</label>
        <input class="login-input" type="password" name="password" placeholder="Passwort eingeben" autofocus>
        <button class="login-btn" type="submit">Anmelden →</button>
      </form>
    </div>
  </div>
</body>
</html>"""


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ─── Statische Dateien ───────────────────────────────────────────
@app.route("/")
@login_required
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/css/<path:filename>")
def css_files(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, "css"), filename)


@app.route("/js/<path:filename>")
def js_files(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, "js"), filename)


# ─── SSE Stream ──────────────────────────────────────────────────
@app.route("/api/stream")
@login_required
def sse_stream():
    q: queue.Queue = queue.Queue(maxsize=20)
    with _sse_lock:
        _sse_queues.append(q)

    # Sofortiger erster Push mit aktuellem Stand
    with _state_lock:
        snapshot = dict(_state)
        alarms = list(_alarms)
    q.put_nowait(f"data: {json.dumps({'tags': snapshot, 'alarms': alarms, 'connected': opc.connected})}\n\n")

    def generate():
        try:
            while True:
                try:
                    yield q.get(timeout=30)
                except queue.Empty:
                    yield ": heartbeat\n\n"
        finally:
            with _sse_lock:
                if q in _sse_queues:
                    _sse_queues.remove(q)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ─── API: Tags (Fallback) ────────────────────────────────────────
@app.route("/api/tags")
@login_required
def get_tags():
    with _state_lock:
        return jsonify(dict(_state))


@app.route("/api/tags/<name>")
@login_required
def get_tag(name):
    with _state_lock:
        if name in _state:
            return jsonify({name: _state[name]})
    return jsonify({"error": f"Tag '{name}' nicht gefunden"}), 404


# ─── API: Steuerbefehl ───────────────────────────────────────────
def _reset_after(name: str, delay: float = 0.3) -> None:
    time.sleep(delay)
    opc.write_value(name, False)


@app.route("/api/cmd/<name>", methods=["POST"])
@login_required
def send_cmd(name):
    opc.ensure_connection(max_tries=2)
    ok = opc.write_value(name, True)
    if ok:
        threading.Thread(target=_reset_after, args=(name,), daemon=True).start()
        return jsonify({"ok": True, "tag": name})
    return jsonify({"ok": False, "error": "Schreiben fehlgeschlagen"}), 500


# ─── API: Status ─────────────────────────────────────────────────
@app.route("/api/status")
@login_required
def get_status():
    with _state_lock:
        alarms = list(_alarms)
    return jsonify({"connected": opc.connected, "endpoint": opc.endpoint, "alarms": alarms})


# ─── API: Historie ───────────────────────────────────────────────
@app.route("/api/history")
@login_required
def get_history_api():
    limit = min(int(request.args.get("limit", 50)), 500)
    return jsonify(get_history(limit))


# ─── API: Alarme ─────────────────────────────────────────────────
@app.route("/api/alarms")
@login_required
def get_alarms():
    with _state_lock:
        return jsonify(list(_alarms))


# ─── Start ───────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    print("[API] SmartView OPC API startet...")
    threading.Thread(target=_opc_worker, daemon=True).start()
    host = os.environ.get("SMARTVIEW_HOST", "0.0.0.0")
    port = int(os.environ.get("SMARTVIEW_PORT", "5000"))
    debug = os.environ.get("SMARTVIEW_DEBUG", "0").lower() in ("1", "true", "yes")
    app.run(host=host, port=port, debug=debug, threaded=True)
