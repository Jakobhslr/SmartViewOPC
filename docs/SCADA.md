# SCADA & Industrie 4.0 – Recherche-Dokumentation

## Was ist ein SCADA-System?

**SCADA** steht für *Supervisory Control and Data Acquisition* – auf Deutsch: Überwachungssteuerung und Datenerfassung.

Ein SCADA-System ist eine Software-Infrastruktur, die industrielle Prozesse **überwacht, steuert und Daten sammelt**. Es verbindet Sensoren, Aktoren und Steuerungen (wie eine SPS) mit einer zentralen Leitstelle, die dem Bediener einen Überblick über den gesamten Prozess gibt.

### Kernfunktionen eines SCADA-Systems

| Funktion | Beschreibung |
|----------|-------------|
| **Datenerfassung** | Lesen von Sensor- und Prozesswerten in Echtzeit |
| **Visualisierung** | Darstellung der Prozessdaten auf einem HMI/Dashboard |
| **Steuerung** | Senden von Befehlen an Aktoren und Steuerungen |
| **Alarmierung** | Meldung bei Grenzwertüberschreitungen |
| **Historisierung** | Speicherung von Messwerten für spätere Auswertung |

---

## Aufgaben in der Industrie

SCADA-Systeme kommen in vielen Branchen zum Einsatz:

- **Fertigung** – Überwachung von Produktionslinien, Förderbändern, Robotern
- **Energieversorgung** – Steuerung von Kraftwerken, Stromnetzen, Windparks
- **Wasserversorgung** – Pumpstationen, Kläranlagen, Drucküberwachung
- **Öl & Gas** – Pipelines, Ventilsteuerung, Leckage-Erkennung
- **Gebäudeautomation** – Klimatisierung, Beleuchtung, Zugangskontrolle

**Wichtig:** SCADA-Systeme laufen oft 24/7 und dürfen nicht ausfallen. Fehlertoleranz und Redundanz sind daher zentrale Anforderungen.

---

## Warum sind SCADA und OPC UA für Industrie 4.0 wichtig?

**Industrie 4.0** bezeichnet die vierte industrielle Revolution: die Vernetzung von Maschinen, Anlagen und IT-Systemen über das Internet (IIoT – Industrial Internet of Things).

### Rolle von SCADA in Industrie 4.0

- **Transparenz:** Echtzeitdaten aus der Produktion werden sichtbar und auswertbar
- **Entscheidungsgrundlage:** Präzise Daten ermöglichen bessere Entscheidungen (z.B. vorausschauende Wartung)
- **Automatisierung:** Prozesse können selbstständig reagieren (Closed-Loop-Control)
- **Integration:** SCADA verbindet OT (Operational Technology) mit IT-Systemen wie ERP oder Cloud

### Rolle von OPC UA

**OPC UA** (*Open Platform Communications Unified Architecture*) ist der führende offene Standard für industrielle Kommunikation:

- **Herstellerunabhängig:** Siemens, Beckhoff, ABB, Schneider – alle sprechen OPC UA
- **Sicher:** Verschlüsselung (TLS), Authentifizierung und Zugriffskontrolle eingebaut
- **Plattformunabhängig:** Läuft auf Windows, Linux, Raspberry Pi, embedded Systemen
- **Semantisch:** Nicht nur Daten, sondern auch deren Bedeutung wird übertragen (Informationsmodell)

Ohne einen einheitlichen Standard wie OPC UA müsste jede Maschine mit einem proprietären Protokoll angebunden werden – das wäre in einer vernetzten Fabrik nicht skalierbar.

---

## Nachteile klassischer HMI gegenüber unserem System

| Kriterium | Klassisches HMI | SmartView OPC (unser System) |
|-----------|----------------|------------------------------|
| **Hardware** | Teures Spezialgerät (Touchpanel) | Raspberry Pi 4B (~80 €) |
| **Software** | Proprietär (z.B. WinCC, FactoryTalk) | Open Source (Python, Flask) |
| **Erweiterbarkeit** | Eingeschränkt, Lizenzkosten | Beliebig erweiterbar |
| **Fernzugriff** | Oft nur im Netzwerk | Browser-basiert, überall erreichbar |
| **Updates** | Aufwändig, oft durch Integrator | Git pull + Neustart |
| **Lernkurve** | Spezialisierte Software nötig | Standardtechnologien (HTML, Python) |

**Kritisch:** Klassische HMIs sind oft nicht für IT-Integration ausgelegt – Anbindung an Datenbanken, Cloud oder ERP ist aufwändig oder unmöglich. Unser System nutzt REST-APIs, die sich leicht in andere IT-Systeme integrieren lassen.

---

## Wo endet ein System – und wo beginnt ein echtes SCADA?

Unser System ist technisch ein **kleines SCADA** im Sinne der Grundfunktionen (Datenerfassung, Visualisierung, Steuerung). Ein vollständiges SCADA-System umfasst zusätzlich:

| Funktion | Unser System | Echtes SCADA |
|----------|-------------|-------------|
| Datenerfassung | ✅ OPC UA Subscription (Push) | ✅ OPC UA / Subscription |
| Visualisierung | ✅ Web-Dashboard (SSE, Echtzeit) | ✅ + Trends, Grafiken |
| Steuerung | ✅ REST POST (Taster-Impuls) | ✅ + Interlock-Logik |
| **Alarmierung** | ✅ Grenzwert-Alarme (Warnung / Kritisch) | ✅ Grenzwerte, Eskalation |
| **Historisierung** | ✅ SQLite-Datenbank (`data/history.db`) | ✅ Zeitreihendatenbank |
| **Redundanz** | ❌ (Single Server) | ✅ Hot-Standby |
| **Benutzerverwaltung** | ✅ Login-Seite, Session, Passwortschutz | ✅ Rollen & Berechtigungen |

Ein echtes SCADA geht dort über unser System hinaus, wo Redundanz, rollenbasierte Benutzerverwaltung und erweiterte Trendanalysen benötigt werden.

---

## Rolle unseres Projekts im ISA-95-Modell

Das **ISA-95-Modell** (auch Purdue-Modell) beschreibt die Hierarchie der Automatisierungspyramide:

```
Level 4 │ ERP-Systeme (SAP, Planung)
─────────┼────────────────────────────────────
Level 3  │ MES, SCADA, Historian
─────────┼────────────────────────────────────
Level 2  │ HMI, Supervisory Control  ← Unser System
─────────┼────────────────────────────────────
Level 1  │ SPS, PLC, Steuerungen (S7-1516)
─────────┼────────────────────────────────────
Level 0  │ Sensoren, Aktoren, Feldgeräte
```

**Unser System (SmartView OPC) ist auf Level 2** angesiedelt:
- Es liest Daten von Level 1 (S7-1516) via OPC UA
- Es visualisiert und ermöglicht Steuerung (Supervisory Control)
- Es reicht durch die SQLite-Historisierung und den Alarm-Handler bereits in Level 3 hinein

Der **Raspberry Pi als Edge Device** ist dabei ein typisches Beispiel für Industrie 4.0: Er bringt IT-Intelligenz direkt in die Fertigungsebene, ohne aufwändige Infrastruktur.
