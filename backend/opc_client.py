"""
opc_client.py
OPC UA Client — liest und schreibt Werte über Node IDs.
"""

from __future__ import annotations

import time
from typing import Any, Dict

from opcua import Client, ua
from config import OPC_UA_ENDPOINT, TAGS, WRITE_TAGS


class OPCUAClient:
    """Verbindet sich mit einem OPC UA Server und liest/schreibt Tags."""

    def __init__(self) -> None:
        self.endpoint = OPC_UA_ENDPOINT
        self.client: Client | None = None
        self.nodes: Dict[str, Any] = {}
        self.write_nodes: Dict[str, Any] = {}
        self.connected = False

    # ── Verbindung ─────────────────────────────────────────────
    def connect(self) -> bool:
        """Verbindung zum OPC UA Server herstellen."""
        self.disconnect()
        try:
            self.client = Client(self.endpoint)
            self.client.connect()
            # Lese-Tags cachen
            self.nodes = {
                name: self.client.get_node(node_id)
                for name, node_id in TAGS.items()
            }
            # Schreib-Tags cachen
            self.write_nodes = {
                name: self.client.get_node(node_id)
                for name, node_id in WRITE_TAGS.items()
            }
            self.connected = True
            print(f"[OPC] Verbunden mit {self.endpoint}")
            return True
        except Exception as e:
            self.connected = False
            self.nodes = {}
            print(f"[OPC] Verbindung fehlgeschlagen: {e}")
            return False

    def disconnect(self) -> None:
        """Verbindung trennen."""
        try:
            if self.client is not None:
                self.client.disconnect()
        except Exception:
            pass
        self.client = None
        self.connected = False
        self.nodes = {}
        self.write_nodes = {}

    def ensure_connection(self, max_tries: int = 1, delay: float = 1.0) -> bool:
        """Sicherstellen, dass eine Verbindung besteht."""
        if self.connected:
            return True
        for _ in range(max_tries):
            if self.connect():
                return True
            time.sleep(delay)
        return False

    # ── Lesen ──────────────────────────────────────────────────
    def read_all(self) -> Dict[str, Any]:
        """Alle Tags lesen und als Dict zurückgeben."""
        if not self.connected or not self.nodes:
            return {name: None for name in TAGS}
        try:
            return {
                name: node.get_value()
                for name, node in self.nodes.items()
            }
        except Exception as e:
            print(f"[OPC] Lesefehler: {e}")
            self.connected = False
            self.nodes = {}
            return {name: None for name in TAGS}

    # ── Schreiben ──────────────────────────────────────────────
    def write_value(self, name: str, value: Any) -> bool:
        """Einen Wert auf einen Schreib-Tag schreiben."""
        if not self.ensure_connection():
            return False
        if name not in self.write_nodes:
            print(f"[OPC] Unbekannter Schreib-Tag: {name}")
            return False
        try:
            node = self.write_nodes[name]
            # Datentyp vom Server lesen und Wert konvertieren
            dv = node.get_data_value()
            variant_type = dv.Value.VariantType
            if variant_type == ua.VariantType.Boolean:
                value = bool(value)
            elif variant_type == ua.VariantType.Float:
                value = float(value)
            elif variant_type == ua.VariantType.Int16:
                value = int(value)

            node.set_value(ua.DataValue(ua.Variant(value, variant_type)))
            print(f"[OPC] Geschrieben: {name} = {value}")
            return True
        except Exception as e:
            print(f"[OPC] Schreibfehler: {e}")
            self.connected = False
            self.nodes = {}
            self.write_nodes = {}
            return False
