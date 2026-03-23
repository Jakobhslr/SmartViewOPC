"""
config.py
Zentrale Konfiguration für SmartView OPC
"""

import os

# ─── Modus ─────────────────────────────────────────────────────────
# USE_SIMULATOR=1 → lokaler Simulator (localhost:4840)
# USE_SIMULATOR=0 → echte S7-1516 (192.168.2.12:4840)
USE_SIMULATOR = os.environ.get("USE_SIMULATOR", "0") == "1"

# ─── OPC UA Endpoint ───────────────────────────────────────────────
OPC_UA_ENDPOINT = os.environ.get(
    "OPC_ENDPOINT",
    "opc.tcp://localhost:4840" if USE_SIMULATOR else "opc.tcp://192.168.2.12:4840",
)

# ─── Lese-Tags (SPS → Dashboard) ───────────────────────────────────
if USE_SIMULATOR:
    TAGS = {
        "druck":                "ns=2;s=Drucksensor_DB.PressureBar",
        "foerderband_ein":      "ns=2;s=HMI_Status_DB.Band_läuft",
        "zylinder_ausgefahren": "ns=2;s=HMI_Status_DB.Zyl_ausfahren",
    }
else:
    TAGS = {
        "druck":                'ns=3;s="Drucksensor_DB"."PressureBar"',
        "foerderband_ein":      'ns=3;s="HMI_Status_DB"."Band_läuft"',
        "zylinder_ausgefahren": 'ns=3;s="HMI_Status_DB"."Zyl_ausfahren"',
    }

# ─── Schreib-Tags (Dashboard → SPS) ────────────────────────────────
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

# ─── Polling ───────────────────────────────────────────────────────
POLL_INTERVAL_MS = 1000
