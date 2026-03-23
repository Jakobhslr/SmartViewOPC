# CHANGELOG – SmartView OPC

Alle Änderungen und Meilensteine des Projekts.

---

## [1.2.0] – 2026-03-23

### Lichtschranken-Sensor

**Backend:**
- `config.py` – `sensor_lichtschranke` Tag hinzugefügt (`ns=3;s="HMI_Status_DB"."Sensor_Lichtschranke"`)

**Frontend:**
- Neue Karte „Lichtschranke" im Dashboard
- Invertierte Logik: `false` (unterbrochen) = **Bauteil vorhanden**, `true` = Frei
- Card-Grid auf 4 Spalten erweitert

---

## [1.1.0] – 2026-03-23

### Steuerung & Taster-Logik

**Backend:**
- `config.py` – Schreib-Tags (`WRITE_TAGS`) getrennt von Lese-Tags (`TAGS`)
- `opc_client.py` – separater `write_nodes`-Cache für Schreib-Tags
- `api.py` – Taster-Impuls-Logik: `true → 300 ms → false` via Hintergrund-Thread
  (SPS sieht steigende + fallende Flanke, wie ein echter Taster)

**Frontend:**
- Steuersektion mit 3 Tasten: **Start** (grün aktiv), **Stop** (rot), **Reset** (orange)
- Start-Button leuchtet grün solange aktiv, erlischt bei Stop/Reset
- Feedback-Text nach jedem Tastendruck

**Schreib-Tags (S7-1516):**
- `start` → `ns=3;s="HMI_CMD_DB"."cmd_start"`
- `stop`  → `ns=3;s="HMI_CMD_DB"."cmd_stop"`
- `reset` → `ns=3;s="HMI_CMD_DB"."cmd_reset"`

---

## [1.0.0] – 2026-03-23

### Initiale Version

**Projektaufbau:**
- Projekt mit `uv init` erstellt, Abhängigkeiten: `flask`, `flask-cors`, `opcua`
- Raspberry Pi 4B (192.168.137.108) als Edge Device & Webserver
- Siemens S7-1516 (192.168.2.12:4840) als OPC UA Server

**Backend:**
- `config.py` – Zentrale Konfiguration, Endpoint & Node IDs, Simulator-Modus (`USE_SIMULATOR=1`)
- `opc_client.py` – OPC UA Client mit Auto-Reconnect, Lesen & Schreiben
- `opc_simulator.py` – Lokaler OPC UA Simulator für Testbetrieb ohne SPS
- `api.py` – Flask REST API
  - `GET /api/tags` – Alle Prozesswerte als JSON
  - `GET /api/tags/<name>` – Einzelwert lesen
  - `POST /api/cmd/<name>` – Steuerbefehl senden
  - `GET /api/status` – OPC UA Verbindungsstatus

**Frontend:**
- Dark-Mode Dashboard (Glassmorphism-Design)
- Drucksensor (Analog, 0–10 bar) mit Balkenanzeige, Warnung ab 7 bar
- Förderband-Indikator (Läuft / Gestoppt)
- Zylinder-Indikator (Ausgefahren / Eingefahren)
- 1-Sekunden Live-Polling via Fetch/AJAX
- Rohdaten-Konsole (aufklappbar)

**Lese-Tags (S7-1516):**
- `druck`                → `ns=3;s="Drucksensor_DB"."PressureBar"`
- `foerderband_ein`      → `ns=3;s="HMI_Status_DB"."Band_läuft"`
- `zylinder_ausgefahren` → `ns=3;s="HMI_Status_DB"."Zyl_ausfahren"`
