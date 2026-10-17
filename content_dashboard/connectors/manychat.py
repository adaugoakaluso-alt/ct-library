"""ManyChat link clicks.

Two connectors live here:

ManyChatSheetConnector (works today)
  Reads a Google Sheet that your ManyChat flows write to. In each keyword
  flow, add a Google Sheets "Add row" action right after the link click,
  writing: date, keyword, cta_text, link, clicks (put 1 in clicks). Then in
  Google Sheets use File > Share > Publish to web > CSV and put that link in
  MANYCHAT_SHEET_CSV_URL. Each pull adds up the clicks per day and keyword.

ManyChatApiConnector (not built yet)
  A placeholder for pulling from the ManyChat API directly with
  MANYCHAT_API_KEY. See "Adding the ManyChat API connector" in the README.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from .. import config
from .base import Connector, ConnectorError


class ManyChatSheetConnector(Connector):
    name = "ManyChat (Google Sheet)"
    dataset = "manychat_clicks"
    required_env = ("MANYCHAT_SHEET_CSV_URL",)
    description = "Reads the Google Sheet your ManyChat flows log link clicks to, and totals clicks per day and keyword."

    def fetch(self, start: date, end: date) -> pd.DataFrame:
        url = config.env("MANYCHAT_SHEET_CSV_URL")
        try:
            raw = pd.read_csv(url, dtype=str)
        except Exception as exc:  # network errors, a sheet that is not published, bad CSV
            raise ConnectorError(f"Could not read the ManyChat sheet. Check that it is published as CSV. ({exc})") from exc
        raw.columns = [c.strip().lower() for c in raw.columns]
        if not {"date", "keyword"}.issubset(raw.columns):
            raise ConnectorError("The ManyChat sheet needs at least a date column and a keyword column.")
        raw["date"] = pd.to_datetime(raw["date"], errors="coerce").dt.normalize()
        raw = raw.dropna(subset=["date", "keyword"])
        raw = raw[(raw["date"] >= pd.Timestamp(start)) & (raw["date"] <= pd.Timestamp(end))]
        raw["keyword"] = raw["keyword"].str.strip().str.upper()
        raw["clicks"] = pd.to_numeric(raw["clicks"], errors="coerce").fillna(1) if "clicks" in raw else 1
        for col in ("cta_text", "link"):
            if col not in raw:
                raw[col] = ""
        out = (
            raw.groupby(["date", "keyword"], as_index=False)
            .agg(cta_text=("cta_text", "first"), link=("link", "first"), clicks=("clicks", "sum"))
        )
        out["source"] = f"ManyChat Google Sheet, pulled {date.today().isoformat()}"
        return out


class ManyChatApiConnector(Connector):
    name = "ManyChat API"
    dataset = "manychat_clicks"
    required_env = ("MANYCHAT_API_KEY",)
    description = "Not built yet. Would pull link clicks straight from ManyChat. See the README."
    implemented = False

    def fetch(self, start: date, end: date) -> pd.DataFrame:
        raise ConnectorError("The ManyChat API connector is not built yet. Use the Google Sheet connector or CSV upload for now.")
