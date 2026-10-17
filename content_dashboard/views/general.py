"""Page 1: General reporting. Audience growth, open rate and click-through rate
for every channel in the brand file, as KPI cards and trend lines."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import metrics
from ..components import (
    Filters, card_grid, fmt_int, fmt_pct, fmt_signed_int, fmt_signed_pts, line_chart, origin_note, show_table,
)
from ..storage import Table


def _series(df: pd.DataFrame, date_col: str, value_col: str, label_col: str | None = None) -> pd.DataFrame:
    df = df.dropna(subset=[value_col])
    if df.empty:
        return pd.DataFrame(columns=["date", "value", "label"])
    return pd.DataFrame({
        "date": df[date_col],
        "value": df[value_col].astype(float),
        "label": df[label_col].astype(str) if label_col else df[date_col].dt.strftime("%b %-d, %Y"),
    })


def render(tables: dict[str, Table], f: Filters) -> None:
    brand = f.brand
    audience = tables["audience"].df
    email = tables["email_stats"].df

    st.title("General reporting")
    st.caption(
        f"{f.start:%b %-d, %Y} to {f.end:%b %-d, %Y}. Each card shows the latest number in this date range "
        "and its change from the entry before it."
    )
    origin_note(tables["audience"], *([tables["email_stats"]] if brand.email else []))
    channels = f.visible(brand.channels)
    if not channels:
        st.info("Pick at least one channel in the sidebar.")
        return

    # Audience: followers for social channels, subscribers for the rest.
    st.header("Audience")
    card_grid([
        (f"{c.audience_metric.capitalize()} · {c.name}",
         metrics.audience_kpi(audience, c.id, c.audience_metric, f.start, f.end),
         fmt_int, fmt_signed_int,
         f"No {c.audience_metric} count for {c.name} in this date range. Add one on the Update data page.")
        for c in channels
    ])

    email_channels = [c for c in channels if c.kind == "email"]
    if email_channels:
        st.header("Email")
        cards = []
        for c in email_channels:
            cards.append((f"Open rate · {c.name}", metrics.email_rate_kpi(email, c.id, "open_rate", f.start, f.end),
                          fmt_pct, fmt_signed_pts, f"No open rate for {c.name} in this date range."))
            cards.append((f"Click-through rate · {c.name}", metrics.email_rate_kpi(email, c.id, "click_rate", f.start, f.end),
                          lambda v: fmt_pct(v, 2), fmt_signed_pts, f"No click-through rate for {c.name} in this date range."))
        card_grid(cards)
        st.caption("Open rate is opens divided by delivered; use your platform's privacy-filtered rate where it has one. "
                   "Click-through rate is unique clicks divided by delivered.")

    st.header("Trends")
    aud_r = metrics.in_range(audience, "date", f.start, f.end)
    email_r = metrics.overlaps(email, "start_date", "end_date", f.start, f.end)
    charts = []
    for metric_name in ("followers", "subscribers"):
        chs = [c for c in channels if c.audience_metric == metric_name]
        if chs:
            charts.append((metric_name.capitalize(), [
                (c, _series(aud_r[(aud_r["channel"] == c.id) & (aud_r["metric"] == metric_name)], "date", "value")) for c in chs
            ], ",d"))
    if email_channels:
        charts.append(("Open rate", [(c, _series(email_r[email_r["channel"] == c.id], "end_date", "open_rate", "label")) for c in email_channels], ".1%"))
        charts.append(("Click-through rate", [(c, _series(email_r[email_r["channel"] == c.id], "end_date", "click_rate", "label")) for c in email_channels], ".2%"))
    for i in range(0, len(charts), 2):
        cols = st.columns(2)
        for col, (title, series, fmt) in zip(cols, charts[i:i + 2]):
            with col:
                st.subheader(title)
                line_chart(series, fmt, title)
    if email_channels:
        st.caption("Email rate points are sends or reporting periods, placed on their last day.")

    with st.expander("Rows behind these numbers"):
        st.markdown("**Audience**")
        show_table(aud_r[aud_r["channel"].isin(f.channels)])
        if email_channels:
            st.markdown("**Email stats**")
            show_table(email_r[email_r["channel"].isin(f.channels)])
