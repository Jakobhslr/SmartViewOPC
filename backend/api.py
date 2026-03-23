"""
api.py
Flask REST API für SmartView OPC.
Stellt OPC UA-Daten per REST bereit und nimmt Steuerbefehle entgegen.
"""

import os
import sys
import time
import threading

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

# Backend-Ordner zum Pfad hinzufügen (für config/opc_client Imports)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from opc_client import OPCUAClient

# ─── Pfade ─────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# ─── Flask-App ─────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)
opc = OPCUAClient()


# ── Statische Dateien (Frontend) ───────────────────────────────
@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/css/<path:filename>")
def css_files(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, "css"), filename)


@app.route("/js/<path:filename>")
def js_files(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, "js"), filename)


# ── API: Werte lesen ──────────────────────────────────────────
@app.route("/api/tags")
def get_tags():
    """Alle Prozesswerte als JSON zurückgeben."""
    opc.ensure_connection(max_tries=1)
    return jsonify(opc.read_all())


@app.route("/api/tags/<name>")
def get_tag(name):
    """Einzelnen Prozesswert lesen."""
    opc.ensure_connection(max_tries=1)
    values = opc.read_all()
    if name in values:
        return jsonify({name: values[name]})
    return jsonify({"error": f"Tag '{name}' nicht gefunden"}), 404


# ── API: Steuerbefehl senden ───────────────────────────────────
def _reset_after(name: str, delay: float = 0.3) -> None:
    """Taster-Impuls: nach kurzer Verzögerung wieder auf False setzen."""
    time.sleep(delay)
    opc.write_value(name, False)


@app.route("/api/cmd/<name>", methods=["POST"])
def send_cmd(name):
    """Taster-Impuls an die SPS senden: true → kurze Pause → false."""
    opc.ensure_connection(max_tries=2)
    ok = opc.write_value(name, True)

    if ok:
        # Impuls in Hintergrund-Thread zurücksetzen (SPS sieht steigende + fallende Flanke)
        threading.Thread(target=_reset_after, args=(name,), daemon=True).start()
        return jsonify({"ok": True, "tag": name})
    return jsonify({"ok": False, "error": "Schreiben fehlgeschlagen"}), 500


# ── API: Verbindungsstatus ─────────────────────────────────────
@app.route("/api/status")
def get_status():
    """OPC UA Verbindungsstatus zurückgeben."""
    return jsonify({
        "connected": opc.connected,
        "endpoint": opc.endpoint,
    })


# ── Start ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print("[API] SmartView OPC API startet...")
    host = os.environ.get("SMARTVIEW_HOST", "0.0.0.0")
    port = int(os.environ.get("SMARTVIEW_PORT", "5000"))
    debug = os.environ.get("SMARTVIEW_DEBUG", "0").lower() in ("1", "true", "yes")
    app.run(host=host, port=port, debug=debug)
