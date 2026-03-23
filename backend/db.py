"""
db.py
SQLite-Historisierung: Prozesswerte zeitgestempelt speichern und abrufen.
"""

import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "history.db")


def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            ts                   TEXT    NOT NULL,
            druck                REAL,
            foerderband_ein      INTEGER,
            zylinder_ausgefahren INTEGER,
            sensor_lichtschranke INTEGER
        )
    """)
    con.commit()
    con.close()


def log_values(values: dict) -> None:
    try:
        con = sqlite3.connect(DB_PATH)
        con.execute(
            "INSERT INTO history (ts, druck, foerderband_ein, zylinder_ausgefahren, sensor_lichtschranke) VALUES (?,?,?,?,?)",
            (
                datetime.now().isoformat(timespec="seconds"),
                values.get("druck"),
                int(bool(values.get("foerderband_ein"))),
                int(bool(values.get("zylinder_ausgefahren"))),
                int(bool(values.get("sensor_lichtschranke"))),
            ),
        )
        con.commit()
        con.close()
    except Exception as e:
        print(f"[DB] Fehler: {e}")


def get_history(limit: int = 100) -> list:
    try:
        con = sqlite3.connect(DB_PATH)
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT * FROM history ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        con.close()
        return [dict(r) for r in rows]
    except Exception:
        return []
