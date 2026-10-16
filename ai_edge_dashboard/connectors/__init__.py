"""Registered data connectors. The Update data page lists everything here."""

from .base import Connector, ConnectorError
from .buffer import BufferConnector
from .manychat import ManyChatApiConnector, ManyChatSheetConnector

REGISTRY: list[Connector] = [
    BufferConnector(),
    ManyChatSheetConnector(),
    ManyChatApiConnector(),
]

__all__ = ["REGISTRY", "Connector", "ConnectorError"]
