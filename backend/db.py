"""
db.py
SQLite-Historisierung: Prozesswerte mit Zeitstempel speichern und abrufen.
SQLite ist eine einfache Datenbankdatei (kein separater Datenbankserver nötig).
Die Datenbank liegt unter data/history.db.
"""

import os
import sqlite3                  # Eingebaute Python-Bibliothek für SQLite
from datetime import datetime   # Für Zeitstempel (wann wurde der Wert gespeichert?)

# Pfad zur Datenbankdatei relativ zum Projektordner bestimmen
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "history.db")


def init_db() -> None:
    """Datenbank und Tabelle beim Start einmalig anlegen (falls noch nicht vorhanden).
    Wird in api.py beim Programmstart aufgerufen.
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)  # data/-Ordner anlegen falls nicht vorhanden
    con = sqlite3.connect(DB_PATH)  # Verbindung zur Datenbankdatei öffnen (erstellt sie bei Bedarf)
    con.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,  -- automatische ID
            ts                   TEXT    NOT NULL,                   -- Zeitstempel (ISO-Format)
            druck                REAL,                               -- Druckwert in bar
            foerderband_ein      INTEGER,                            -- 0 oder 1 (BOOL als INT gespeichert)
            zylinder_ausgefahren INTEGER,                            -- 0 oder 1
            sensor_lichtschranke INTEGER                             -- 0 oder 1
        )
    """)
    con.commit()   # Änderungen speichern
    con.close()    # Verbindung schließen


def log_values(values: dict) -> None:
    """Aktuellen Datensatz (alle Prozesswerte) in die Datenbank schreiben.
    Wird aus api.py alle ~10 OPC UA Wertänderungen aufgerufen (≈ alle 10 Sekunden).
    values: {"druck": 5.3, "foerderband_ein": True, ...}
    """
    try:
        con = sqlite3.connect(DB_PATH)
        con.execute(
            "INSERT INTO history (ts, druck, foerderband_ein, zylinder_ausgefahren, sensor_lichtschranke) VALUES (?,?,?,?,?)",
            (
                datetime.now().isoformat(timespec="seconds"),          # Zeitstempel z.B. "2026-03-23T14:05:12"
                values.get("druck"),                                    # REAL-Wert direkt übernehmen
                int(bool(values.get("foerderband_ein"))),               # True → 1, False → 0
                int(bool(values.get("zylinder_ausgefahren"))),
                int(bool(values.get("sensor_lichtschranke"))),
            ),
        )
        con.commit()
        con.close()
    except Exception as e:
        print(f"[DB] Fehler: {e}")  # Datenbankfehler dürfen die API nicht zum Absturz bringen


def get_history(limit: int = 100) -> list:
    """Letzte N Einträge aus der Datenbank lesen und als Liste zurückgeben.
    ORDER BY id DESC → neueste Einträge zuerst.
    Wird vom API-Endpunkt GET /api/history aufgerufen.
    """
    try:
        con = sqlite3.connect(DB_PATH)
        con.row_factory = sqlite3.Row  # Damit Zeilen wie Dicts ansprechbar sind (r["druck"] statt r[2])
        rows = con.execute(
            "SELECT * FROM history ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        con.close()
        return [dict(r) for r in rows]  # sqlite3.Row → normales Python-Dict für JSON-Ausgabe
    except Exception:
        return []  # Bei Fehler leere Liste zurückgeben statt Absturz
