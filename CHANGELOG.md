# CHANGELOG – SmartView OPC

Alle Änderungen und Meilensteine des Projekts.

---

## [1.0.0] – 2026-03-23

### 🎯 Meilenstein: Initiale Version

**Projektaufbau (komplett neu):**
- Projekt mit `uv init` erstellt, `.venv` via `uv sync`
- Abhängigkeiten: `flask`, `flask-cors`, `opcua`

**Backend:**
- `config.py` – Zentrale Konfiguration mit Platzhalter-Node IDs (werden später durch echte SPS Node IDs ersetzt)
- `opc_simulator.py` – OPC UA Server-Simulator für virtuelles Testen
  - Drucksensor (REAL, 0–10 bar, Sinuswelle + Rauschen)
  - Förderband ein/aus (BOOL)
  - Taster Start (BOOL)
  - Reagiert auf Start-Befehl: Förderband geht an
- `opc_client.py` – OPC UA Client mit Lesen + Schreiben, Auto-Reconnect
- `api.py` – Flask REST API
  - `GET /api/tags` – Alle Prozesswerte lesen
  - `GET /api/tags/<name>` – Einzelwert lesen
  - `POST /api/cmd/<name>` – Steuerbefehl senden
  - `GET /api/status` – Verbindungsstatus

**Frontend:**
- Premium Dark-Mode Dashboard mit Glassmorphism-Design
- Drucksensor-Anzeige mit Balken (0–10 bar, Warnung ab 7 bar)
- Förderband Status-Indikator (Läuft / Gestoppt)
- Taster Start Status-Indikator (Aktiv / Inaktiv)
- **Start-Button** → Sendet `cmd_start = true` über OPC UA an SPS
- **Stop-Button** → Sendet `cmd_start = false`
- Rohdaten / Entwicklerkonsole (aufklappbar)
- 1-Sekunden Live-Polling

---

## Geplant

### Node ID Integration
- [ ] Echte SPS Node IDs vom User erhalten
- [ ] `config.py` Node IDs ersetzen
- [ ] Test mit echter SPS (S7-1500)
