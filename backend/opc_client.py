"""
opc_client.py
OPC UA Client — verbindet sich mit der S7-1516, liest Prozesswerte
und schreibt Steuerbefehle über Node IDs.
"""

from __future__ import annotations  # Ermöglicht Typ-Hints wie "OPCUAClient | None"

import time
from typing import Any, Dict

from opcua import Client, ua          # opcua ist die Python-Bibliothek für OPC UA
from config import OPC_UA_ENDPOINT, TAGS, WRITE_TAGS  # Unsere Konfiguration


class OPCUAClient:
    """Verbindet sich mit einem OPC UA Server und liest/schreibt Tags."""

    def __init__(self) -> None:
        # Beim Erstellen des Objekts sind noch keine Verbindungen aktiv
        self.endpoint = OPC_UA_ENDPOINT   # Adresse des OPC UA Servers (z.B. opc.tcp://192.168.2.12:4840)
        self.client: Client | None = None  # Das eigentliche Verbindungsobjekt zur SPS
        self.nodes: Dict[str, Any] = {}    # Zwischenspeicher für Lese-Nodes (Name → Node-Objekt)
        self.write_nodes: Dict[str, Any] = {}  # Zwischenspeicher für Schreib-Nodes
        self.connected = False             # Aktueller Verbindungsstatus (True/False)

    # ── Verbindung ──────────────────────────────────────────────────────────────

    def connect(self) -> bool:
        """Verbindung zum OPC UA Server herstellen.
        Gibt True zurück wenn erfolgreich, False bei Fehler.
        """
        self.disconnect()  # Vorherige Verbindung sauber trennen, bevor eine neue aufgebaut wird
        try:
            self.client = Client(self.endpoint)  # OPC UA Client-Objekt mit der Server-Adresse erstellen
            self.client.connect()                 # Tatsächliche TCP-Verbindung zur SPS herstellen

            # Lese-Tags cachen: Einmalig die Node-Objekte holen und speichern.
            # So muss die Node-ID nicht bei jedem Lesen erneut aufgelöst werden.
            self.nodes = {
                name: self.client.get_node(node_id)
                for name, node_id in TAGS.items()
            }

            # Schreib-Tags cachen (gleiche Logik, aber für Steuerbefehle)
            self.write_nodes = {
                name: self.client.get_node(node_id)
                for name, node_id in WRITE_TAGS.items()
            }

            self.connected = True
            print(f"[OPC] Verbunden mit {self.endpoint}")
            return True
        except Exception as e:
            # Verbindung fehlgeschlagen (z.B. SPS aus, falscher Endpoint)
            self.connected = False
            self.nodes = {}
            print(f"[OPC] Verbindung fehlgeschlagen: {e}")
            return False

    def disconnect(self) -> None:
        """Verbindung zur SPS sauber trennen und alle Zustände zurücksetzen."""
        try:
            if self.client is not None:
                self.client.disconnect()  # TCP-Verbindung schließen
        except Exception:
            pass  # Fehler beim Trennen ignorieren (z.B. wenn Verbindung schon weg ist)
        self.client = None
        self.connected = False
        self.nodes = {}
        self.write_nodes = {}

    def ensure_connection(self, max_tries: int = 1, delay: float = 1.0) -> bool:
        """Stellt sicher, dass eine Verbindung besteht.
        Versucht ggf. erneut zu verbinden (max_tries Mal).
        Wird vor Schreibbefehlen aufgerufen, damit kein Befehl verloren geht.
        """
        if self.connected:
            return True  # Schon verbunden — nichts zu tun
        for _ in range(max_tries):
            if self.connect():
                return True
            time.sleep(delay)
        return False  # Verbindung konnte nicht hergestellt werden

    # ── Lesen ───────────────────────────────────────────────────────────────────

    def read_all(self) -> Dict[str, Any]:
        """Alle konfigurierten Tags auf einmal lesen.
        Gibt ein Dict zurück: {"druck": 5.3, "foerderband_ein": True, ...}
        Wird im Polling-Modus genutzt (nicht bei Subscription).
        """
        if not self.connected or not self.nodes:
            # Keine Verbindung → None-Werte für alle Tags zurückgeben
            return {name: None for name in TAGS}
        try:
            return {
                name: node.get_value()   # get_value() liest den aktuellen Wert von der SPS
                for name, node in self.nodes.items()
            }
        except Exception as e:
            print(f"[OPC] Lesefehler: {e}")
            # Nach Lesefehler als getrennt markieren → Reconnect-Loop greift ein
            self.connected = False
            self.nodes = {}
            return {name: None for name in TAGS}

    # ── Schreiben ───────────────────────────────────────────────────────────────

    def write_value(self, name: str, value: Any) -> bool:
        """Einen Wert auf einen Schreib-Tag in der SPS schreiben.
        Gibt True zurück wenn erfolgreich, False bei Fehler.
        Beispiel: write_value("start", True) setzt cmd_start auf True.
        """
        if not self.ensure_connection():
            return False

        if name not in self.write_nodes:
            print(f"[OPC] Unbekannter Schreib-Tag: {name}")
            return False

        try:
            node = self.write_nodes[name]

            # Datentyp des Tags von der SPS lesen, damit wir den richtigen Typ schreiben.
            # Die SPS akzeptiert nur den exakt passenden Typ (BOOL, FLOAT, INT...).
            dv = node.get_data_value()
            variant_type = dv.Value.VariantType

            # Wert in den korrekten Python-Typ konvertieren
            if variant_type == ua.VariantType.Boolean:
                value = bool(value)
            elif variant_type == ua.VariantType.Float:
                value = float(value)
            elif variant_type == ua.VariantType.Int16:
                value = int(value)

            # Wert als OPC UA DataValue an die SPS schreiben
            node.set_value(ua.DataValue(ua.Variant(value, variant_type)))
            print(f"[OPC] Geschrieben: {name} = {value}")
            return True
        except Exception as e:
            print(f"[OPC] Schreibfehler: {e}")
            # Nach Schreibfehler Verbindung als unterbrochen markieren
            self.connected = False
            self.nodes = {}
            self.write_nodes = {}
            return False
