"""
config.py
Zentrale Konfiguration für SmartView OPC.
Alle wichtigen Einstellungen (OPC-Adresse, Tag-Namen, Modus) stehen hier —
so muss man für Änderungen nur diese eine Datei anpassen.
"""

import os  # os.environ liest Umgebungsvariablen aus dem Betriebssystem

# ─── Modus ─────────────────────────────────────────────────────────────────────
# Umgebungsvariable USE_SIMULATOR entscheidet, ob wir mit echter SPS oder
# lokalem Simulator arbeiten. Nützlich für Tests ohne physische Hardware.
# Aufruf: USE_SIMULATOR=1 python backend/api.py
USE_SIMULATOR = os.environ.get("USE_SIMULATOR", "0") == "1"

# ─── OPC UA Endpoint ───────────────────────────────────────────────────────────
# Die Adresse des OPC UA Servers (auf der SPS oder dem Simulator).
# opc.tcp:// ist das Protokoll von OPC UA — ähnlich wie http:// beim Web.
# Port 4840 ist der Standard-Port für OPC UA.
OPC_UA_ENDPOINT = os.environ.get(
    "OPC_ENDPOINT",
    "opc.tcp://localhost:4840" if USE_SIMULATOR else "opc.tcp://192.168.2.12:4840",
)

# ─── Lese-Tags (SPS → Dashboard) ───────────────────────────────────────────────
# Tags sind die "Adressen" von Variablen in der SPS.
# ns=3 ist der Namespace (Siemens-spezifisch, TIA Portal).
# s="..." ist der symbolische Name aus dem TIA Portal Datenbaustein.
# Der Simulator benutzt andere Adressen (ns=2), da es kein TIA Portal ist.
if USE_SIMULATOR:
    TAGS = {
        "druck":                "ns=2;s=Drucksensor_DB.PressureBar",
        "foerderband_ein":      "ns=2;s=HMI_Status_DB.Band_läuft",
        "zylinder_ausgefahren": "ns=2;s=HMI_Status_DB.Zyl_ausfahren",
    }
else:
    # Echte Node IDs aus dem TIA Portal der Siemens S7-1516
    TAGS = {
        "druck":                'ns=3;s="Drucksensor_DB"."PressureBar"',        # REAL, 0–10 bar
        "foerderband_ein":      'ns=3;s="HMI_Status_DB"."Band_läuft"',          # BOOL
        "zylinder_ausgefahren": 'ns=3;s="HMI_Status_DB"."Zyl_ausfahren"',       # BOOL
        "sensor_lichtschranke": 'ns=3;s="HMI_Status_DB"."Sensor_Lichtschranke"', # BOOL (invertiert)
    }

# ─── Schreib-Tags (Dashboard → SPS) ────────────────────────────────────────────
# Diese Tags werden von uns beschrieben — die SPS liest sie und führt Aktionen aus.
# cmd_start/stop/reset sind BOOL-Variablen im Datenbaustein HMI_CMD_DB der S7.
if USE_SIMULATOR:
    WRITE_TAGS = {
        "start": "ns=2;s=HMI_CMD_DB.cmd_start",
        "stop":  "ns=2;s=HMI_CMD_DB.cmd_stop",
        "reset": "ns=2;s=HMI_CMD_DB.cmd_reset",
    }
else:
    WRITE_TAGS = {
        "start": 'ns=3;s="HMI_CMD_DB"."cmd_start"',
        "stop":  'ns=3;s="HMI_CMD_DB"."cmd_stop"',
        "reset": 'ns=3;s="HMI_CMD_DB"."cmd_reset"',
    }

# ─── Polling-Intervall ──────────────────────────────────────────────────────────
# Nur relevant wenn Polling genutzt wird (nicht bei Subscription).
# Gibt an, wie oft (in ms) Werte abgefragt werden sollen.
POLL_INTERVAL_MS = 1000
