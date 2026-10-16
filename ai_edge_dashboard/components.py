"""Shared UI pieces: filters, KPI cards, charts and table helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from . import config
from .metrics import Kpi
from .storage import EMPTY, SAMPLE, Table


@dataclass
class Filters:
    start: date
    end: date
    channels: list[str]

    def shows(self, *channels: str) -> bool:
        return any(c in self.channels for c in channels)


def fmt_int(v) -> str:
    return "-" if v is None or pd.isna(v) else f"{int(round(v)):,}"


def fmt_pct(v, digits: int = 1) -> str:
    return "-" if v is None or pd.isna(v) else f"{v * 100:.{digits}f}%"


def fmt_signed_int(v) -> str:
    return f"{'+' if v > 0 else ''}{int(round(v)):,}"


def fmt_signed_pts(v) -> str:
    return f"{'+' if v > 0 else ''}{v * 100:.1f} pts"


def origin_note(*tables: Table) -> None:
    """Say plainly when a page is showing sample data or has nothing to show."""
    sample = [t.dataset.title for t in tables if t.origin == SAMPLE]
    empty = [t.dataset.title for t in tables if t.origin == EMPTY]
    if sample:
        st.info("Showing sample data, not real AI Edge numbers. Save your first real numbers on the Update data page and sample data turns off.")
    if empty:
        st.warning("No data yet for: " + ", ".join(empty) + ". Add it on the Update data page.")


def kpi_card(label: str, k: Kpi, value_fmt, change_fmt, waiting: str, range_label: str = "in this date range") -> None:
    """One KPI: the latest value, its change from the entry before it, and the row it came from."""
    with st.container(border=True):
        if k.value is None:
            st.metric(label, "-")
            st.caption(waiting)
            return
        delta = None
        if k.change is not None:
            delta = f"{change_fmt(k.change)} vs {k.previous_label}"
        st.metric(label, value_fmt(k.value), delta=delta)
        lines = [f"From: {k.row_label}"]
        if k.range_change is not None:
            lines.append(f"Change {range_label}: {change_fmt(k.range_change)}")
        if k.source:
            lines.append(f"Source: {k.source}")
        st.caption("  \n".join(lines))


def line_chart(series: list[tuple[str, pd.DataFrame]], y_format: str, y_title: str) -> None:
    """series: (channel, DataFrame with columns date, value, label). Empty series are listed as waiting."""
    fig = go.Figure()
    waiting = []
    for channel, df in series:
        name = config.CHANNELS[channel]
        if df.empty:
            waiting.append(name)
            continue
        df = df.sort_values("date")
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["value"], name=name, mode="lines+markers",
            line=dict(color=config.CHANNEL_COLORS[channel], width=2),
            marker=dict(size=7),
            customdata=df[["label"]],
            hovertemplate=f"<b>{name}</b><br>%{{customdata[0]}}<br>%{{y:{y_format}}}<extra></extra>",
        ))
    if not fig.data:
        st.caption("No numbers in this date range yet." + (" Waiting on: " + ", ".join(waiting) + "." if waiting else ""))
        return
    fig.update_layout(
        height=280, margin=dict(l=8, r=8, t=8, b=8),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        yaxis=dict(title=y_title, tickformat=y_format, rangemode="tozero"),
        xaxis=dict(title=None),
        hovermode="closest",
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    if waiting:
        st.caption("No numbers yet for: " + ", ".join(waiting) + ".")


def show_table(df: pd.DataFrame, column_config: dict | None = None, **kwargs) -> None:
    """A full-width table. Date columns show as dates, without a time."""
    cfg = {
        c: st.column_config.DateColumn(c, format="YYYY-MM-DD")
        for c in df.columns
        if pd.api.types.is_datetime64_any_dtype(df[c])
    }
    cfg.update(column_config or {})
    st.dataframe(df, width="stretch", hide_index=True, column_config=cfg, **kwargs)
