"""The shape every data connector follows.

A connector fetches rows for exactly one table (a schema in schemas.py) and
returns them as a DataFrame with that table's columns, including a `source`
column that says where each row came from. The Update data page lists every
registered connector, shows whether its settings are present, and saves what
fetch() returns through storage.save(), the same path CSV uploads take.

To add a connector: subclass Connector, fill in the class attributes, write
fetch(), and add an instance to REGISTRY in connectors/__init__.py.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

import pandas as pd

from .. import config


class ConnectorError(Exception):
    """A problem the person can fix, written in plain words."""


class Connector(ABC):
    # Short name shown in the app.
    name: str = ""
    # Table this connector fills. Must be a key of schemas.DATASETS.
    dataset: str = ""
    # Environment variables that must be set before fetch() can run.
    required_env: tuple[str, ...] = ()
    # One sentence on what it pulls.
    description: str = ""
    # False for a connector that is documented but not built yet.
    implemented: bool = True

    def missing_settings(self) -> list[str]:
        return [v for v in self.required_env if not config.env(v)]

    def is_configured(self) -> bool:
        return self.implemented and not self.missing_settings()

    @abstractmethod
    def fetch(self, start: date, end: date) -> pd.DataFrame:
        """Return rows dated between start and end, in the dataset's columns."""
