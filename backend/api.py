"""
api.py
SmartView OPC – REST-API mit SSE, OPC UA Subscription, Auth, Alarmen & Historisierung.

Zentrale Datei des Backends. Hier laufen alle Teile zusammen:
  - Flask stellt die Web-API und das Dashboard bereit
  - Ein Hintergrund-Thread hält die OPC UA Verbindung und richtet eine Subscription ein
  - Wertänderungen werden per SSE (Server-Sent Events) sofort an den Browser gepusht
  - Alarme werden bei jedem neuen Wert geprüft
  - Alle ~10 Wertänderungen wird ein Snapshot in SQLite gespeichert
"""

import json
import os
import queue       # Thread-sichere Warteschlange für SSE-Nachrichten
import sys
import time
import threading   # Für parallele Ausführung (OPC-Worker, Reset-Timer)
from functools import wraps  # Für den Login-Decorator

from flask import (Flask, Response, jsonify, redirect, request,
                   send_from_directory, session, stream_with_context)
from flask_cors import CORS  # Erlaubt Cross-Origin Requests (z.B. beim lokalen Testen)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from opc_client import OPCUAClient          # Unser OPC UA Client
from db import init_db, log_values, get_history  # SQLite-Historisierung

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")  # Pfad zum HTML/CSS/JS-Ordner

# ─── Flask App ────────────────────────────────────────────────────────────────
app = Flask(__name__)
# Secret Key wird für die Verschlüsselung der Session-Cookies gebraucht.
# Aus Umgebungsvariable lesen (sicherer als hardcoded Wert).
app.secret_key = os.environ.get("SECRET_KEY", "smartview-opc-2026")
CORS(app)  # CORS-Header setzen damit Browser API-Anfragen erlaubt sind

# Passwort aus Umgebungsvariable oder Standard-Fallback
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "smartview2026")

# ─── OPC UA Client Instanz ────────────────────────────────────────────────────
opc = OPCUAClient()  # Einmalig erstellen, wird vom Hintergrund-Thread genutzt

# ─── Shared State (thread-sicher) ─────────────────────────────────────────────
# _state speichert die aktuellsten Prozesswerte aller Tags
_state: dict = {}
# _alarms speichert die aktuell aktiven Alarme
_alarms: list = []
# Lock verhindert, dass zwei Threads gleichzeitig auf _state/_alarms schreiben
_state_lock = threading.Lock()
# Liste aller aktiven SSE-Queues (eine pro verbundenem Browser-Tab)
_sse_queues: list[queue.Queue] = []
_sse_lock = threading.Lock()
# Zähler: nach je 10 OPC-Ereignissen wird ein DB-Snapshot geschrieben
_log_counter = 0

# ─── Alarm-Schwellwerte ───────────────────────────────────────────────────────
# Jeder Eintrag definiert eine Regel: Wenn tag op threshold → Alarm mit level und msg
ALARM_CONFIG = [
    {"tag": "druck", "op": ">", "threshold": 9.0, "level": "critical", "msg": "Druck kritisch (> 9 bar)"},
    {"tag": "druck", "op": ">", "threshold": 8.0, "level": "warning",  "msg": "Druck hoch (> 8 bar)"},
    {"tag": "druck", "op": "<", "threshold": 1.0, "level": "warning",  "msg": "Druck zu niedrig (< 1 bar)"},
]


def check_alarms(values: dict) -> list:
    """Alle Alarm-Regeln gegen die aktuellen Prozesswerte prüfen.
    Gibt eine Liste der aktiven Alarme zurück (leer wenn kein Alarm aktiv).
    """
    active = []
    for cfg in ALARM_CONFIG:
        v = values.get(cfg["tag"])  # Aktuellen Wert des Tags holen
        if v is None:
            continue  # Kein Wert vorhanden → Regel überspringen
        if cfg["op"] == ">" and v > cfg["threshold"]:
            active.append({"level": cfg["level"], "msg": cfg["msg"]})
        elif cfg["op"] == "<" and v < cfg["threshold"]:
            active.append({"level": cfg["level"], "msg": cfg["msg"]})
    return active


def _push_sse(payload: dict) -> None:
    """Nachricht an alle verbundenen Browser-Tabs senden.
    Jeder Tab hat eine eigene Queue — wir schreiben in alle gleichzeitig.
    Das SSE-Format erfordert "data: ...\n\n" als Trennzeichen.
    """
    msg = f"data: {json.dumps(payload)}\n\n"
    with _sse_lock:
        for q in _sse_queues:
            try:
                q.put_nowait(msg)   # Nachricht in Queue schreiben (nicht blockierend)
            except queue.Full:
                pass  # Queue voll (z.B. Browser reagiert nicht) → Nachricht verwerfen


# ─── OPC UA Subscription Handler ──────────────────────────────────────────────
class _SubHandler:
    """Wird von der OPC UA Bibliothek aufgerufen, wenn sich ein Wert ändert.
    Das ist das Herzstück der Subscription: Statt wir fragen → SPS meldet sich.
    """

    def __init__(self, node_map: dict):
        # node_map: NodeId → Tag-Name (z.B. NodeId("...PressureBar") → "druck")
        self._map = node_map

    def datachange_notification(self, node, val, data):
        """Wird automatisch aufgerufen, wenn die SPS einen neuen Wert meldet.
        node: das OPC UA Node-Objekt
        val:  der neue Wert (z.B. 5.3 für Druck)
        """
        global _log_counter
        # Tag-Namen aus der NodeId bestimmen
        tag = self._map.get(node.nodeid, str(node.nodeid))

        # Neuen Wert thread-sicher in _state schreiben
        with _state_lock:
            _state[tag] = val
            snapshot = dict(_state)  # Vollständige Kopie für Alarm-Check

        # Alarme mit dem aktuellen Stand aller Werte prüfen
        alarms = check_alarms(snapshot)
        with _state_lock:
            _alarms.clear()
            _alarms.extend(alarms)

        # Alle 10 Wertänderungen in die SQLite-DB schreiben (~10 Sekunden Intervall)
        _log_counter += 1
        if _log_counter % 10 == 0:
            log_values(snapshot)

        # Alle Browser-Tabs sofort per SSE benachrichtigen
        _push_sse({"tags": snapshot, "alarms": alarms, "connected": True})


# ─── OPC Worker Thread ────────────────────────────────────────────────────────
def _opc_worker() -> None:
    """Läuft dauerhaft im Hintergrund als separater Thread.
    Aufgaben:
    1. Verbindung zur SPS herstellen
    2. OPC UA Subscription einrichten (SPS meldet sich bei Wertänderung)
    3. Verbindung alle 5s prüfen und bei Abbruch automatisch neu verbinden
    """
    while True:
        if not opc.connected:
            ok = opc.connect()  # Verbindung zur SPS aufbauen
            if not ok:
                # Verbindung fehlgeschlagen → Browser informieren, 5s warten, erneut versuchen
                _push_sse({"tags": {}, "alarms": [], "connected": False})
                time.sleep(5)
                continue

            try:
                # Node-Map erstellen: NodeId → Tag-Name (für den Subscription-Handler)
                node_map = {n.nodeid: name for name, n in opc.nodes.items()}
                handler = _SubHandler(node_map)

                # OPC UA Subscription erstellen: 1000ms Publish-Intervall
                # Das bedeutet: SPS prüft alle 1000ms ob sich Werte geändert haben
                sub = opc.client.create_subscription(1000, handler)

                # Alle konfigurierten Lese-Tags abonnieren
                sub.subscribe_data_change(list(opc.nodes.values()))
                print("[OPC] Subscription aktiv")
            except Exception as e:
                print(f"[OPC] Subscription fehlgeschlagen: {e}")
                opc.disconnect()
                time.sleep(5)
                continue

        # Verbindung alle 5s mit einem Lese-Test prüfen
        time.sleep(5)
        try:
            list(opc.nodes.values())[0].get_value()  # Einen Wert lesen als Verbindungstest
        except Exception:
            print("[OPC] Verbindung verloren – reconnect...")
            opc.disconnect()
            _push_sse({"tags": {}, "alarms": [], "connected": False})


# ─── Authentifizierung ────────────────────────────────────────────────────────
def login_required(f):
    """Decorator: Schützt Routen vor unbefugtem Zugriff.
    Prüft ob der Benutzer angemeldet ist (session["logged_in"] == True).
    API-Endpunkte → HTTP 401, normale Seiten → Redirect zur Login-Seite.
    Verwendung: @login_required über einer Route-Funktion.
    """
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
    """Login-Seite: GET zeigt das Formular, POST prüft das Passwort.
    Bei korrektem Passwort wird session["logged_in"] = True gesetzt
    und der Browser zum Dashboard weitergeleitet.
    """
    error = ""
    if request.method == "POST":
        if request.form.get("password", "") == DASHBOARD_PASSWORD:
            session["logged_in"] = True
            return redirect("/")
        error = "Falsches Passwort"

    # Login-HTML direkt als String zurückgeben (kein Template-System)
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
    """Session löschen → Benutzer ist abgemeldet, Redirect zur Login-Seite."""
    session.clear()
    return redirect("/login")


# ─── Statische Dateien ────────────────────────────────────────────────────────
@app.route("/")
@login_required  # Nur für angemeldete Benutzer
def index():
    """Dashboard-Startseite: Liefert frontend/index.html aus."""
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/css/<path:filename>")
def css_files(filename):
    """CSS-Dateien aus frontend/css/ ausliefern."""
    return send_from_directory(os.path.join(FRONTEND_DIR, "css"), filename)


@app.route("/js/<path:filename>")
def js_files(filename):
    """JavaScript-Dateien aus frontend/js/ ausliefern."""
    return send_from_directory(os.path.join(FRONTEND_DIR, "js"), filename)


# ─── SSE Stream ───────────────────────────────────────────────────────────────
@app.route("/api/stream")
@login_required
def sse_stream():
    """Server-Sent Events Endpunkt — hält eine dauerhaft offene HTTP-Verbindung.
    Der Browser öffnet diese Verbindung einmalig (EventSource in app.js).
    Danach schickt der Server Nachrichten wann immer sich OPC-Werte ändern.
    Vorteil gegenüber Polling: kein wiederholtes Anfragen, sofortige Updates.
    """
    # Neue Queue für diesen Browser-Tab erstellen
    q: queue.Queue = queue.Queue(maxsize=20)
    with _sse_lock:
        _sse_queues.append(q)  # In globale Liste eintragen

    # Sofort den aktuellen Stand schicken (damit das Dashboard nicht leer startet)
    with _state_lock:
        snapshot = dict(_state)
        alarms = list(_alarms)
    q.put_nowait(f"data: {json.dumps({'tags': snapshot, 'alarms': alarms, 'connected': opc.connected})}\n\n")

    def generate():
        """Generator-Funktion: Liefert Nachrichten aus der Queue an den Browser.
        Läuft solange der Browser-Tab offen ist.
        """
        try:
            while True:
                try:
                    yield q.get(timeout=30)  # Auf Nachricht warten (max. 30s)
                except queue.Empty:
                    # Alle 30s einen Heartbeat schicken damit die Verbindung offen bleibt
                    yield ": heartbeat\n\n"
        finally:
            # Tab geschlossen → Queue aus der globalen Liste entfernen
            with _sse_lock:
                if q in _sse_queues:
                    _sse_queues.remove(q)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",  # Spezieller MIME-Typ für SSE
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ─── API: Tags ────────────────────────────────────────────────────────────────
@app.route("/api/tags")
@login_required
def get_tags():
    """GET /api/tags — Alle aktuellen Prozesswerte als JSON zurückgeben.
    Fallback falls SSE nicht funktioniert oder manuell abgefragt wird.
    Beispiel-Antwort: {"druck": 5.3, "foerderband_ein": true, ...}
    """
    with _state_lock:
        return jsonify(dict(_state))


@app.route("/api/tags/<name>")
@login_required
def get_tag(name):
    """GET /api/tags/<name> — Einzelnen Tag abfragen.
    Beispiel: GET /api/tags/druck → {"druck": 5.3}
    404 wenn der Tag nicht bekannt ist.
    """
    with _state_lock:
        if name in _state:
            return jsonify({name: _state[name]})
    return jsonify({"error": f"Tag '{name}' nicht gefunden"}), 404


# ─── API: Steuerbefehl ────────────────────────────────────────────────────────
def _reset_after(name: str, delay: float = 0.3) -> None:
    """Hilfsfunktion für Taster-Impuls: Setzt den Tag nach 'delay' Sekunden zurück auf False.
    Läuft als separater Daemon-Thread, damit die API-Antwort nicht wartet.
    """
    time.sleep(delay)
    opc.write_value(name, False)


@app.route("/api/cmd/<name>", methods=["POST"])
@login_required
def send_cmd(name):
    """POST /api/cmd/<name> — Steuerbefehl als Taster-Impuls an die SPS senden.
    Ablauf: Tag auf True setzen → 300ms warten → Tag zurück auf False.
    Das simuliert einen echten physischen Taster.
    Beispiel: POST /api/cmd/start
    """
    opc.ensure_connection(max_tries=2)  # Verbindung sicherstellen bevor wir schreiben
    ok = opc.write_value(name, True)    # Tag auf True setzen (Taster gedrückt)
    if ok:
        # Reset-Timer in separatem Thread starten (nicht blockierend)
        threading.Thread(target=_reset_after, args=(name,), daemon=True).start()
        return jsonify({"ok": True, "tag": name})
    return jsonify({"ok": False, "error": "Schreiben fehlgeschlagen"}), 500


# ─── API: Status ──────────────────────────────────────────────────────────────
@app.route("/api/status")
@login_required
def get_status():
    """GET /api/status — OPC UA Verbindungsstatus und aktive Alarme.
    Beispiel-Antwort: {"connected": true, "endpoint": "opc.tcp://...", "alarms": [...]}
    """
    with _state_lock:
        alarms = list(_alarms)
    return jsonify({"connected": opc.connected, "endpoint": opc.endpoint, "alarms": alarms})


# ─── API: Historie ────────────────────────────────────────────────────────────
@app.route("/api/history")
@login_required
def get_history_api():
    """GET /api/history?limit=N — Letzte N Datenbankeinträge als JSON.
    Maximum: 500 Einträge. Standard: 50.
    Das Frontend fragt immer limit=20 ab (letzte 20 Einträge).
    """
    limit = min(int(request.args.get("limit", 50)), 500)
    return jsonify(get_history(limit))


# ─── API: Alarme ──────────────────────────────────────────────────────────────
@app.route("/api/alarms")
@login_required
def get_alarms():
    """GET /api/alarms — Aktuell aktive Alarme als JSON-Liste.
    Leer ([]) wenn kein Alarm aktiv. Wird auch per SSE mitgeliefert.
    """
    with _state_lock:
        return jsonify(list(_alarms))


# ─── Programmstart ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()  # SQLite-Datenbank und Tabelle anlegen (falls noch nicht vorhanden)
    print("[API] SmartView OPC API startet...")

    # OPC-Worker als Daemon-Thread starten:
    # Daemon = Thread wird automatisch beendet wenn das Hauptprogramm endet
    threading.Thread(target=_opc_worker, daemon=True).start()

    # Flask-Server starten
    host = os.environ.get("SMARTVIEW_HOST", "0.0.0.0")   # 0.0.0.0 = auf allen Interfaces lauschen
    port = int(os.environ.get("SMARTVIEW_PORT", "5000"))
    debug = os.environ.get("SMARTVIEW_DEBUG", "0").lower() in ("1", "true", "yes")
    app.run(host=host, port=port, debug=debug, threaded=True)  # threaded=True für SSE nötig
