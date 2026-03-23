# SmartView OPC – Mini-SCADA-System

> Industrielles SCADA-Dashboard für die **Siemens S7-1516**.
> Liest Prozessdaten live via **OPC UA**, stellt sie per **REST-API** (Flask) bereit
> und zeigt sie in einem modernen **Web-Dashboard** an — läuft auf einem **Raspberry Pi 4B**.

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
2. Raspberry Pi verbindet sich als OPC UA Client und liest Prozessdaten
3. Flask REST-API gibt die Daten als JSON aus
4. Browser pollt alle 1 s und zeigt Werte live im Dashboard an
5. Steuerbefehle (Start/Stop/Reset) werden als Taster-Impuls über OPC UA zurück an die SPS gesendet

---

## Dashboard

| Anzeige | Typ | Beschreibung |
|---|---|---|
| Drucksensor | Analog | Druckanzeige 0–10 bar mit Balken, Warnung ab 7 bar |
| Förderband | Digital | Läuft / Gestoppt |
| Zylinder | Digital | Ausgefahren / Eingefahren |
| Lichtschranke | Digital | Bauteil vorhanden / Frei (invertiert: false = unterbrochen) |
| Start | Taster | Startet Anlage, leuchtet grün solange aktiv |
| Stop | Taster | Stoppt Anlage |
| Reset | Taster | Setzt Anlage zurück |

Alle Taster senden einen **echten Impuls** (`true → 300 ms → false`), genau wie ein physischer Taster an der Anlage.

---

## Schnellstart (3 Befehle)

```bash
# 1. Abhängigkeiten installieren
uv sync

# 2a. Mit echter SPS starten
uv run python backend/api.py

# 2b. Oder mit Simulator (kein S7 nötig)
USE_SIMULATOR=1 uv run python backend/opc_simulator.py &
USE_SIMULATOR=1 uv run python backend/api.py
```

Dashboard öffnen: **http://192.168.137.108:5000**

---

## Setup auf dem Raspberry Pi

### Voraussetzungen

- Raspberry Pi 4B mit Raspberry Pi OS (64-bit)
- Python 3.11+

### Installation

```bash
# uv installieren
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# Repo klonen
git clone https://github.com/Jakobhslr/SmartViewOPC.git
cd SmartViewOPC

# Abhängigkeiten installieren
uv sync

# Starten
uv run python backend/api.py
```

---

## Konfiguration

Datei: [`backend/config.py`](backend/config.py)

### OPC UA Endpoint

```python
OPC_UA_ENDPOINT = "opc.tcp://192.168.2.12:4840"   # Siemens S7-1516
```

### Lese-Tags (SPS → Dashboard)

```python
TAGS = {
    "druck":                'ns=3;s="Drucksensor_DB"."PressureBar"',
    "foerderband_ein":      'ns=3;s="HMI_Status_DB"."Band_läuft"',
    "zylinder_ausgefahren": 'ns=3;s="HMI_Status_DB"."Zyl_ausfahren"',
    "sensor_lichtschranke": 'ns=3;s="HMI_Status_DB"."Sensor_Lichtschranke"',
}
```

### Schreib-Tags (Dashboard → SPS)

```python
WRITE_TAGS = {
    "start": 'ns=3;s="HMI_CMD_DB"."cmd_start"',
    "stop":  'ns=3;s="HMI_CMD_DB"."cmd_stop"',
    "reset": 'ns=3;s="HMI_CMD_DB"."cmd_reset"',
}
```

### Simulator-Modus (ohne SPS)

```bash
export USE_SIMULATOR=1   # Schaltet auf localhost:4840 und Simulator-NodeIDs
```

---

## REST-API Endpunkte

| Methode | Endpunkt | Beschreibung |
|---------|----------|--------------|
| GET | `/api/tags` | Alle Prozesswerte als JSON |
| GET | `/api/tags/<name>` | Einzelnen Wert lesen |
| POST | `/api/cmd/<name>` | Taster-Impuls senden (true → 300ms → false) |
| GET | `/api/status` | OPC UA Verbindungsstatus |
| GET | `/` | Web-Dashboard |

### Beispiele

```bash
# Alle Tags lesen
curl http://192.168.137.108:5000/api/tags

# Drucksensor lesen
curl http://192.168.137.108:5000/api/tags/druck

# Start-Befehl senden
curl -X POST http://192.168.137.108:5000/api/cmd/start

# Verbindungsstatus
curl http://192.168.137.108:5000/api/status
```

---

## Projektstruktur

```
SmartViewOPC/
├── backend/
│   ├── api.py            # Flask REST-API
│   ├── opc_client.py     # OPC UA Client (Lesen & Schreiben, Auto-Reconnect)
│   ├── opc_simulator.py  # OPC UA Simulator (Testbetrieb ohne SPS)
│   └── config.py         # Endpoint, Node IDs, Simulator-Modus
├── frontend/
│   ├── index.html        # Dashboard
│   ├── css/style.css     # Dark-Mode Glassmorphism Design
│   └── js/app.js         # Live-Polling & Steuerungslogik
├── docs/
│   └── SCADA.md          # Recherche: SCADA, OPC UA, Industrie 4.0, ISA-95
├── pyproject.toml
├── CHANGELOG.md
└── README.md
```

---

## Team & Lizenz

Schulprojekt – SFE-Schulaufgabe
Lizenz: MIT
