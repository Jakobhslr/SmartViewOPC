"""
opc_simulator.py
OPC UA Server-Simulator für virtuelles Testen.
Simuliert: Drucksensor (analog), Förderband (digital), Taster Start (digital).
Startet auf localhost:4840.
"""

import sys
import time
import math
import random
from opcua import Server, ua


def main():
    server = Server()
    server.set_endpoint("opc.tcp://0.0.0.0:4840")
    server.set_server_name("SmartView OPC Simulator")

    # Namespace
    uri = "urn:smartview:simulator"
    idx = server.register_namespace(uri)

    # ─── Variablen anlegen ──────────────────────────────────────
    objects = server.get_objects_node()
    folder = objects.add_folder(idx, "PLC_Sim")

    # Drucksensor (REAL, 0–10 bar) — ns=3;s="Drucksensor_DB"."PressureBar"
    pressure = folder.add_variable(
        ua.NodeId("Drucksensor_DB.PressureBar", idx),
        "PressureBar",
        0.0,
        varianttype=ua.VariantType.Float,
    )
    pressure.set_writable()

    # Förderband läuft (BOOL) — ns=3;s="HMI_Status_DB"."Band_läuft"
    foerderband = folder.add_variable(
        ua.NodeId("HMI_Status_DB.Band_läuft", idx),
        "Band_läuft",
        False,
        varianttype=ua.VariantType.Boolean,
    )
    foerderband.set_writable()

    # Zylinder ausgefahren (BOOL) — ns=3;s="HMI_Status_DB"."Zyl_ausfahren"
    zylinder = folder.add_variable(
        ua.NodeId("HMI_Status_DB.Zyl_ausfahren", idx),
        "Zyl_ausfahren",
        False,
        varianttype=ua.VariantType.Boolean,
    )
    zylinder.set_writable()

    # ─── Server starten ────────────────────────────────────────
    server.start()
    print("[SIMULATOR] OPC UA Server gestartet auf opc.tcp://0.0.0.0:4840")
    print("[SIMULATOR] Drücke Ctrl+C zum Beenden.\n")

    t = 0
    try:
        while True:
            # --- Drucksensor simulieren: Sinuswelle + Rauschen (2–8 bar) ---
            p = 5.0 + 3.0 * math.sin(t * 0.1) + random.uniform(-0.3, 0.3)
            p = max(0.0, min(10.0, p))
            pressure.set_value(round(p, 2))

            # --- Förderband: alle 5 s umschalten ---
            band_on = (t // 5) % 2 == 0
            foerderband.set_value(band_on)

            # --- Zylinder: versetzt zum Förderband umschalten ---
            zyl_aus = (t // 7) % 2 == 0
            zylinder.set_value(zyl_aus)

            print(
                f"\r[SIM] Druck={p:5.2f} bar | "
                f"Förderband={'EIN' if band_on else 'AUS'} | "
                f"Zylinder={'AUSGEFAHREN' if zyl_aus else 'EINGEFAHREN'}   ",
                end="",
                flush=True,
            )

            t += 1
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[SIMULATOR] Wird beendet...")
    finally:
        server.stop()


if __name__ == "__main__":
    main()
