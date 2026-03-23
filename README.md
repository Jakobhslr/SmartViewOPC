# SmartView OPC – Mini-SCADA-System

Industrielles SCADA-Dashboard für die Siemens S7-1516.
Liest Prozessdaten via **OPC UA**, stellt sie per **REST-API** (Flask) bereit
und zeigt sie in einem **responsiven Web-Dashboard** an.

---

## Architekturdiagramm

```
┌─────────────────────┐        OPC UA         ┌──────────────────────┐
│  Siemens S7-1516    │◄─────────────────────►│  Raspberry Pi 4B     │
│  192.168.2.12:4840  │    opc.tcp://...       │  192.168.137.108     │
└─────────────────────┘                        │                      │
                                               │  ┌────────────────┐  │
                                               │  │  opc_client.py │  │
                                               │  └───────┬────────┘  │
                                               │          │           │
                                               │  ┌───────▼────────┐  │
                                               │  │   api.py       │  │
                                               │  │  Flask :5000   │  │
                                               │  └───────┬────────┘  │
                                               └──────────┼───────────┘
                                                          │ HTTP/REST
                                               ┌──────────▼───────────┐
                                               │   Browser / Dashboard │
                                               │   index.html (JS)     │
                                               └──────────────────────┘
```

**Datenfluss:**
1. S7-1516 stellt OPC UA Server bereit (Port 4840)
2. Raspberry Pi verbindet sich als OPC UA Client
3. Flask REST-API (`/api/tags`) gibt Prozessdaten als JSON aus
4. Browser pollt alle 1 s und zeigt Werte live an

---

## Schnellstart (3 Befehle)

```bash
# 1. Abhängigkeiten installieren
uv sync

# 2a. Mit echter SPS starten
uv run python backend/api.py

# 2b. Oder mit Simulator (kein S7 nötig)
uv run python backend/opc_simulator.py &
uv run python backend/api.py
```

Dashboard öffnen: **http://192.168.137.108:5000**

---

## Setup auf dem Raspberry Pi

### Voraussetzungen

- Raspberry Pi 4B mit Raspberry Pi OS (64-bit)
- Python 3.11+
- `uv` installiert

### Installation

```bash
# uv installieren (falls nicht vorhanden)
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# Repo klonen
git clone <repo-url> SmartViewOPC
cd SmartViewOPC

# Abhängigkeiten installieren
uv sync
```

### Starten

```bash
# Mit echter SPS (S7-1516 muss erreichbar sein)
uv run python backend/api.py

# Mit Simulator (zum Testen ohne SPS)
uv run python backend/opc_simulator.py &
uv run python backend/api.py
```

---

## Konfiguration

### OPC UA Endpoint

Datei: [backend/config.py](backend/config.py)

```python
OPC_UA_ENDPOINT = "opc.tcp://192.168.2.12:4840"   # Siemens S7-1516
```

Alternativ per Umgebungsvariable:

```bash
export OPC_ENDPOINT="opc.tcp://192.168.2.12:4840"
```

### Node IDs (Tags)

Die Node IDs der SPS-Variablen aus TIA Portal eintragen:

```python
TAGS = {
    "pressure":    'ns=3;s="DB_Prozess"."Drucksensor"',
    "foerderband": 'ns=3;s="DB_Prozess"."Foerderband"',
    "taster_start":'ns=3;s="DB_Prozess"."Taster_Start"',
    "cmd_start":   'ns=3;s="DB_Prozess"."CMD_Start"',
}
```

### Port / Host

```bash
export SMARTVIEW_HOST=0.0.0.0   # Standard
export SMARTVIEW_PORT=5000       # Standard
export SMARTVIEW_DEBUG=0         # 1 für Entwicklung
```

---

## REST-API Endpunkte

| Methode | Endpunkt | Beschreibung |
|---------|----------|--------------|
| GET | `/api/tags` | Alle Prozesswerte als JSON |
| GET | `/api/tags/<name>` | Einzelnen Wert lesen |
| POST | `/api/cmd/<name>` | Steuerbefehl senden (`{"value": true}`) |
| GET | `/api/status` | OPC UA Verbindungsstatus |
| GET | `/` | Web-Dashboard |

### Beispiele

```bash
# Alle Tags lesen
curl http://192.168.137.108:5000/api/tags

# Drucksensor lesen
curl http://192.168.137.108:5000/api/tags/pressure

# Start-Befehl senden
curl -X POST http://192.168.137.108:5000/api/cmd/cmd_start \
     -H "Content-Type: application/json" \
     -d '{"value": true}'

# Verbindungsstatus
curl http://192.168.137.108:5000/api/status
```

---

## Projektstruktur

```
SmartViewOPC/
├── backend/
│   ├── api.py            # Flask REST-API
│   ├── opc_client.py     # OPC UA Client
│   ├── opc_simulator.py  # OPC UA Simulator (Testbetrieb)
│   └── config.py         # Endpoint & Node IDs
├── frontend/
│   ├── index.html        # Dashboard
│   ├── css/style.css     # Styles
│   └── js/app.js         # Polling & UI-Logik
├── docs/
│   └── SCADA.md          # Recherche-Dokumentation
├── pyproject.toml
└── README.md
```

---

## Team & Lizenz

Schulprojekt – SFE-Schulaufgabe
Lizenz: MIT
