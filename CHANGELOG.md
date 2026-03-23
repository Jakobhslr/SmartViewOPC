# CHANGELOG – SmartView OPC

Alle Versionen, Änderungen und Meilensteine des Projekts.

---

## [2.0.0] – 2026-03-23

### Optionale Ziele – vollständige Umsetzung

#### OPC UA Subscription (statt Polling)
- OPC UA Subscription ersetzt das bisherige 1-Sekunden-Polling
- Werte werden direkt bei Änderung vom OPC UA Server gepusht
- Subscription-Handler mit automatischem Reconnect bei Verbindungsabbruch
- Hintergrund-Thread überwacht Verbindung und erneuert Subscription bei Bedarf

#### SSE – Server-Sent Events
- Neuer Endpunkt `GET /api/stream` (text/event-stream)
- Browser hält eine dauerhafte Verbindung zum Server
- Daten werden serverseitig gepusht sobald sich OPC-Werte ändern
- Heartbeat alle 30 s verhindert Timeout
- `app.js` nutzt `EventSource` statt `setInterval + fetch`

#### Alarme (Grenzwerte)
- Alarm-Banner im Dashboard bei Grenzwertüberschreitung
- **Warnung** (gelb): Druck > 8,0 bar
- **Kritisch** (rot, blinkend): Druck > 9,0 bar
- Neuer Endpunkt `GET /api/alarms`
- Alarme werden bei jedem SSE-Push mitgeliefert

#### Historisierung (SQLite)
- Neues Modul `backend/db.py` mit SQLite-Datenbank
- Prozesswerte werden alle ~10 Wertänderungen gespeichert
- Tabelle `history`: Zeitstempel, Druck, Förderband, Zylinder, Lichtschranke
- Neuer Endpunkt `GET /api/history?limit=N`
- Verlauf-Tabelle im Dashboard (aufklappbar, letzte 20 Einträge)
- Datenbank unter `data/history.db` (in `.gitignore`)

#### Authentifizierung
- Login-Seite unter `/login` (Passwort-geschützt)
- Flask-Session speichert Anmeldestatus
- Alle API-Endpunkte und das Dashboard sind ohne Login nicht zugänglich
- Logout-Button in der Navbar
- Passwort konfigurierbar via Umgebungsvariable `DASHBOARD_PASSWORD`

#### Docker
- `Dockerfile` auf Basis `python:3.11-slim`
- `docker-compose.yml` mit Volume für SQLite-Datenbank, OPC-Endpoint und Passwort als Umgebungsvariablen
- Port 5000 nach außen freigegeben

---

## [1.2.0] – 2026-03-23

### Lichtschranken-Sensor & Steuerung

#### Backend
- `sensor_lichtschranke` Tag hinzugefügt (`ns=3;s="HMI_Status_DB"."Sensor_Lichtschranke"`)
- Schreib-Tags in separate `WRITE_TAGS`-Konfiguration ausgelagert
- `opc_client.py`: separater `write_nodes`-Cache für Schreib-Tags
- Taster-Impuls-Logik in `api.py`: `true → 300 ms → false` via Hintergrund-Thread

#### Frontend
- Neue Karte „Lichtschranke" – invertierte Logik: `false` (unterbrochen) = **Bauteil vorhanden**
- Steuersektion mit 3 Tasten: **Start** (grün aktiv), **Stop** (rot), **Reset** (orange)
- Card-Grid auf 4 Spalten erweitert

#### Schreib-Tags (S7-1516)
- `start` → `ns=3;s="HMI_CMD_DB"."cmd_start"`
- `stop`  → `ns=3;s="HMI_CMD_DB"."cmd_stop"`
- `reset` → `ns=3;s="HMI_CMD_DB"."cmd_reset"`

---

## [1.1.0] – 2026-03-23

### Echte SPS-Anbindung & Node ID Integration

- Echte Node IDs der Siemens S7-1516 aus TIA Portal eingetragen
- OPC UA Endpoint auf `opc.tcp://192.168.2.12:4840` gesetzt
- Deployment auf Raspberry Pi 4B (192.168.137.108)
- systemd-Dienst eingerichtet (Autostart beim Booten)
- WLAN EU141 statisch konfiguriert (192.168.164.50)

#### Lese-Tags (S7-1516)
- `druck`                → `ns=3;s="Drucksensor_DB"."PressureBar"`
- `foerderband_ein`      → `ns=3;s="HMI_Status_DB"."Band_läuft"`
- `zylinder_ausgefahren` → `ns=3;s="HMI_Status_DB"."Zyl_ausfahren"`

---

## [1.0.0] – 2026-03-23

### Initiale Version

#### Projektaufbau
- Projekt mit `uv init` erstellt
- Abhängigkeiten: `flask`, `flask-cors`, `opcua`
- Raspberry Pi 4B als Edge Device & Webserver
- Siemens S7-1516 als OPC UA Server

#### Backend
- `config.py` – Zentrale Konfiguration, OPC Endpoint, Node IDs, Simulator-Modus
- `opc_client.py` – OPC UA Client: Verbinden, Lesen, Schreiben, Auto-Reconnect
- `opc_simulator.py` – Lokaler OPC UA Simulator für Testbetrieb ohne SPS
- `api.py` – Flask REST-API
  - `GET /api/tags` – Alle Prozesswerte als JSON
  - `GET /api/tags/<name>` – Einzelwert lesen
  - `POST /api/cmd/<name>` – Steuerbefehl senden
  - `GET /api/status` – OPC UA Verbindungsstatus

#### Frontend
- Dark-Mode Dashboard mit Glassmorphism-Design
- Drucksensor (Analog, 0–10 bar) mit Balkenanzeige, Warnung ab 7 bar
- Förderband-Indikator (Läuft / Gestoppt)
- Zylinder-Indikator (Ausgefahren / Eingefahren)
- 1-Sekunden Live-Polling via Fetch/AJAX
- Rohdaten-Konsole (aufklappbar)
