# SmartView OPC – Mini-SCADA-System

> Industrielles SCADA-Dashboard für die **Siemens S7-1516**.
> Liest Prozessdaten in Echtzeit via **OPC UA**, stellt sie per **REST-API** bereit
> und zeigt sie in einem modernen, responsiven **Web-Dashboard** an.
> Läuft auf einem **Raspberry Pi 4B** als Edge Device.

---

## Übersicht

| | |
|---|---|
| **SPS** | Siemens S7-1516 · `192.168.2.12:4840` |
| **Edge Device** | Raspberry Pi 4B · `192.168.164.50` |
| **Dashboard** | http://192.168.164.50:5000 |
| **Passwort** | `smartview2026` |
| **Protokoll** | OPC UA (opcua-Bibliothek) |
| **Datenübertragung** | SSE – Server-Sent Events |

---

## Architekturdiagramm

```
┌──────────────────────┐         OPC UA          ┌──────────────────────────┐
│   Siemens S7-1516    │ ◄─────────────────────► │     Raspberry Pi 4B      │
│   192.168.2.12:4840  │   opc.tcp (Subscription) │     192.168.164.50       │
└──────────────────────┘                          │                          │
                                                  │  ┌──────────────────┐   │
                                                  │  │  opc_client.py   │   │
                                                  │  │  Subscription    │   │
                                                  │  └────────┬─────────┘   │
                                                  │           │             │
                                                  │  ┌────────▼─────────┐   │
                                                  │  │    api.py        │   │
                                                  │  │  Flask :5000     │   │
                                                  │  │  SSE / REST      │   │
                                                  │  └────────┬─────────┘   │
                                                  │           │             │
                                                  │  ┌────────▼─────────┐   │
                                                  │  │    db.py         │   │
                                                  │  │  SQLite History  │   │
                                                  │  └──────────────────┘   │
                                                  └──────────┬───────────────┘
                                                             │ SSE / HTTP
                                                  ┌──────────▼───────────────┐
                                                  │    Browser / Dashboard    │
                                                  │    EventSource (SSE)      │
                                                  └──────────────────────────┘
```

**Datenfluss:**
1. S7-1516 stellt OPC UA Server bereit (Port 4840)
2. Raspberry Pi verbindet sich als OPC UA Client und richtet eine **Subscription** ein
3. Bei Wertänderung schickt die S7 den neuen Wert automatisch (Push)
4. Flask-API leitet die Daten per **SSE** an den Browser weiter
5. Browser empfängt Daten in Echtzeit — kein Polling nötig
6. Steuerbefehle (Start/Stop/Reset) laufen als Taster-Impuls zurück zur S7

---

## Dashboard

### Prozesswerte

| Karte | Typ | Beschreibung |
|---|---|---|
| Drucksensor | Analog | 0–10 bar mit Balkenanzeige · Warnung ab 8 bar |
| Förderband | Digital | Läuft / Gestoppt |
| Zylinder | Digital | Ausgefahren / Eingefahren |
| Lichtschranke | Digital | Bauteil vorhanden / Frei (invertiert: `false` = unterbrochen) |

### Steuerung

| Taste | Aktion |
|---|---|
| Start | Anlage starten · leuchtet grün solange aktiv |
| Stop | Anlage stoppen |
| Reset | Anlage zurücksetzen |

> Alle Tasten senden einen echten **Taster-Impuls** (`true → 300 ms → false`) — genau wie ein physischer Taster.

### Weitere Funktionen

- **Alarm-Banner** — erscheint automatisch bei Grenzwertüberschreitung
- **Verlauf** — aufklappbare Tabelle mit den letzten 20 gespeicherten Messwerten
- **Rohdaten-Konsole** — aktueller JSON-Stand aller Tags
- **Login / Logout** — Passwortschutz für das gesamte Dashboard

---

## Alarme

| Alarm | Schwellwert | Stufe |
|---|---|---|
| Druck hoch | > 8,0 bar | ⚠ Warnung (gelb) |
| Druck kritisch | > 9,0 bar | 🔴 Kritisch (rot, blinkend) |

---

## Schnellstart (3 Befehle)

```bash
# 1. Abhängigkeiten installieren
uv sync

# 2a. Mit echter SPS starten
uv run python backend/api.py

# 2b. Mit Simulator (kein S7 nötig)
USE_SIMULATOR=1 uv run python backend/opc_simulator.py &
USE_SIMULATOR=1 uv run python backend/api.py
```

Dashboard öffnen: **http://192.168.164.50:5000**
Passwort: `smartview2026`

---

## Setup auf dem Raspberry Pi

### Voraussetzungen
- Raspberry Pi 4B mit Raspberry Pi OS (64-bit)
- Python 3.11+
- LAN-Kabel in X2-Port der S7-1516

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
```

### Als Dienst einrichten (Autostart)

```bash
sudo nano /etc/systemd/system/smartview.service
```

```ini
[Unit]
Description=SmartView OPC Dashboard
After=network.target

[Service]
User=projekt_sfe
WorkingDirectory=/home/projekt_sfe/SmartViewOPC
ExecStart=/home/projekt_sfe/.local/bin/uv run python backend/api.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable smartview
sudo systemctl start smartview
```

### Mit Docker starten

```bash
docker compose up -d
```

---

## Konfiguration

Datei: [`backend/config.py`](backend/config.py)

### OPC UA Endpoint

```python
OPC_UA_ENDPOINT = "opc.tcp://192.168.2.12:4840"
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

### Umgebungsvariablen

| Variable | Standard | Beschreibung |
|---|---|---|
| `OPC_ENDPOINT` | `opc.tcp://192.168.2.12:4840` | OPC UA Server |
| `DASHBOARD_PASSWORD` | `smartview2026` | Login-Passwort |
| `SECRET_KEY` | `smartview-opc-2026` | Flask Session Key |
| `USE_SIMULATOR` | `0` | `1` = Simulator-Modus |
| `SMARTVIEW_PORT` | `5000` | HTTP-Port |

---

## REST-API Endpunkte

| Methode | Endpunkt | Beschreibung |
|---|---|---|
| `GET` | `/` | Web-Dashboard |
| `GET` | `/login` | Login-Seite |
| `GET` | `/logout` | Abmelden |
| `GET` | `/api/stream` | SSE-Stream (Live-Daten) |
| `GET` | `/api/tags` | Alle Prozesswerte als JSON |
| `GET` | `/api/tags/<name>` | Einzelwert lesen |
| `POST` | `/api/cmd/<name>` | Taster-Impuls senden |
| `GET` | `/api/status` | OPC UA Verbindungsstatus + Alarme |
| `GET` | `/api/alarms` | Aktive Alarme |
| `GET` | `/api/history?limit=N` | Historisierte Messwerte (SQLite) |

---

## Projektstruktur

```
SmartViewOPC/
├── backend/
│   ├── api.py            # Flask REST-API · SSE · Auth · Alarme
│   ├── opc_client.py     # OPC UA Client (Lesen, Schreiben, Subscription)
│   ├── opc_simulator.py  # OPC UA Simulator für Testbetrieb ohne SPS
│   ├── db.py             # SQLite Historisierung
│   └── config.py         # OPC Endpoint, Node IDs, Simulator-Modus
├── frontend/
│   ├── index.html        # Dashboard (Karten, Steuerung, Alarme, Verlauf)
│   ├── css/style.css     # Dark-Mode Glassmorphism Design
│   └── js/app.js         # SSE EventSource, Alarme, Historie, Steuerung
├── docs/
│   └── SCADA.md          # Recherche: SCADA, OPC UA, Industrie 4.0, ISA-95
├── data/                 # SQLite-Datenbank (lokal, nicht im Git)
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── CHANGELOG.md
└── README.md
```

---

## Optionale Ziele – Umsetzung

| Ziel | Punkte | Status |
|---|---|---|
| OPC UA Subscription statt Polling | 4 | ✅ Push bei Wertänderung |
| WebSocket / SSE | 5 | ✅ Server-Sent Events |
| Alarme (Grenzwert) | 1 | ✅ Warnung + Kritisch |
| Historisierung (SQLite) | 2 | ✅ SQLite + Verlauf-Tabelle |
| Authentifizierung | 3 | ✅ Login-Seite + Session |
| Docker | 6 | ✅ Dockerfile + Compose |

---

## Alten Stand wiederherstellen

```bash
# Auf dem Raspberry Pi
cd ~/SmartViewOPC
git fetch --tags
git checkout fertig        # Stabiler Stand v1.2.0
sudo systemctl restart smartview

# Zurück zur aktuellen Version
git checkout main
git pull
sudo systemctl restart smartview
```

---

## Team & Lizenz

Schulprojekt – SFE-Schulaufgabe
Lizenz: MIT
