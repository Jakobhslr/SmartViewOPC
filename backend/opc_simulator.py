"""
opc_simulator.py
OPC UA Server-Simulator für virtuelles Testen ohne echte SPS.
Startet einen lokalen OPC UA Server auf localhost:4840 und simuliert:
  - Drucksensor (REAL, 0–10 bar) als Sinuswelle mit Rauschen
  - Förderband (BOOL) wechselt alle 5 Sekunden
  - Zylinder (BOOL) wechselt alle 7 Sekunden versetzt
Start: USE_SIMULATOR=1 python backend/opc_simulator.py
"""

import sys
import time
import math      # Für Sinuswelle (math.sin)
import random    # Für Rauschen auf dem Drucksignal
from opcua import Server, ua  # Server-Seite der opcua-Bibliothek


def main():
    # ── OPC UA Server konfigurieren ────────────────────────────────────────────
    server = Server()
    server.set_endpoint("opc.tcp://0.0.0.0:4840")   # Auf allen Netzwerkschnittstellen lauschen
    server.set_server_name("SmartView OPC Simulator")

    # Namespace registrieren — jeder OPC UA Server hat mindestens einen eigenen Namespace
    # Der Index (idx) wird für die Node IDs verwendet (ns=2;s=...)
    uri = "urn:smartview:simulator"
    idx = server.register_namespace(uri)

    # ── OPC UA Nodes (Variablen) anlegen ───────────────────────────────────────
    objects = server.get_objects_node()              # Einstiegspunkt des OPC UA Adressraums
    folder = objects.add_folder(idx, "PLC_Sim")     # Ordner "PLC_Sim" als logische Gruppe

    # Drucksensor: REAL-Wert (Fließkomma), 0–10 bar
    # Node ID entspricht dem was config.py im Simulator-Modus erwartet
    pressure = folder.add_variable(
        ua.NodeId("Drucksensor_DB.PressureBar", idx),
        "PressureBar",
        0.0,                                  # Startwert
        varianttype=ua.VariantType.Float,     # Datentyp: Float (entspricht REAL in der SPS)
    )
    pressure.set_writable()  # Erlaubt Schreibzugriff von außen (z.B. für Tests)

    # Förderband: BOOL — läuft oder gestoppt
    foerderband = folder.add_variable(
        ua.NodeId("HMI_Status_DB.Band_läuft", idx),
        "Band_läuft",
        False,
        varianttype=ua.VariantType.Boolean,
    )
    foerderband.set_writable()

    # Zylinder: BOOL — ausgefahren oder eingefahren
    zylinder = folder.add_variable(
        ua.NodeId("HMI_Status_DB.Zyl_ausfahren", idx),
        "Zyl_ausfahren",
        False,
        varianttype=ua.VariantType.Boolean,
    )
    zylinder.set_writable()

    # ── Server starten ─────────────────────────────────────────────────────────
    server.start()
    print("[SIMULATOR] OPC UA Server gestartet auf opc.tcp://0.0.0.0:4840")
    print("[SIMULATOR] Drücke Ctrl+C zum Beenden.\n")

    t = 0  # Zeitschritt-Zähler für Sinus und Takt-Wechsel
    try:
        while True:
            # Drucksensor: Sinuswelle zwischen 2–8 bar + zufälliges Rauschen ±0.3
            # Formel: Mittelwert 5.0 bar, Amplitude 3.0 bar → 2.0 bis 8.0 bar
            p = 5.0 + 3.0 * math.sin(t * 0.1) + random.uniform(-0.3, 0.3)
            p = max(0.0, min(10.0, p))   # Auf 0–10 bar begrenzen (Clipping)
            pressure.set_value(round(p, 2))

            # Förderband: wechselt alle 5 Sekunden (t//5 ist gerade → True)
            band_on = (t // 5) % 2 == 0
            foerderband.set_value(band_on)

            # Zylinder: wechselt alle 7 Sekunden (versetzt gegenüber Förderband)
            zyl_aus = (t // 7) % 2 == 0
            zylinder.set_value(zyl_aus)

            # Status-Ausgabe in der Konsole (überschreibt die gleiche Zeile mit \r)
            print(
                f"\r[SIM] Druck={p:5.2f} bar | "
                f"Förderband={'EIN' if band_on else 'AUS'} | "
                f"Zylinder={'AUSGEFAHREN' if zyl_aus else 'EINGEFAHREN'}   ",
                end="",
                flush=True,
            )

            t += 1
            time.sleep(1)  # 1 Sekunde warten → Werte ändern sich jede Sekunde

    except KeyboardInterrupt:
        print("\n[SIMULATOR] Wird beendet...")
    finally:
        server.stop()  # OPC UA Server sauber herunterfahren


if __name__ == "__main__":
    main()
