"""Page 1: General reporting. Subscriber growth, follower count, open rate and
click-through rate, as KPI cards and trend lines."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import metrics
from ..components import (
    Filters, fmt_int, fmt_pct, fmt_signed_int, fmt_signed_pts, kpi_card, line_chart, origin_note, show_table,
)
from ..storage import Table


def _series(df: pd.DataFrame, date_col: str, value_col: str, label) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["date", "value", "label"])
    df = df.dropna(subset=[value_col])
    return pd.DataFrame({
        "date": df[date_col],
        "value": df[value_col].astype(float),
        "label": df.apply(label, axis=1) if len(df) else [],
    })


def render(tables: dict[str, Table], f: Filters) -> None:
    sends = tables["newsletter_sends"].df
    periods = tables["newsletter_periods"].df
    followers = tables["followers"].df
    substack = tables["substack"].df

    st.title("General reporting")
    st.caption(
        f"{f.start:%b %-d, %Y} to {f.end:%b %-d, %Y}. Each card shows the latest number in this date range "
        "and its change from the entry before it."
    )
    origin_note(tables["newsletter_sends"], tables["newsletter_periods"], tables["followers"], tables["substack"])

    ig = followers[followers["channel"] == "instagram"]
    li = followers[followers["channel"] == "linkedin"]

    cards = [
        ("newsletter", "Subscribers · Newsletter",
         metrics.latest_with_change(sends.assign(label=sends["send_date"].dt.strftime("%b %-d send")), "send_date", "delivered", f.start, f.end, "label"),
         fmt_int, fmt_signed_int, "No newsletter sends in this date range."),
        ("substack", "Subscribers · Substack",
         metrics.latest_with_change(substack, "date", "subscribers", f.start, f.end),
         fmt_int, fmt_signed_int, "No Substack numbers in this date range. Add them on the Update data page."),
        ("instagram", "Followers · Instagram",
         metrics.latest_with_change(ig, "date", "followers", f.start, f.end),
         fmt_int, fmt_signed_int, "No Instagram follower count in this date range. Add one on the Update data page."),
        ("linkedin", "Followers · LinkedIn",
         metrics.latest_with_change(li, "date", "followers", f.start, f.end),
         fmt_int, fmt_signed_int, "No LinkedIn follower count in this date range. Add one on the Update data page."),
        ("newsletter", "Open rate · Newsletter",
         metrics.latest_period_rate(periods, "open_rate_filtered", f.start, f.end),
         fmt_pct, fmt_signed_pts, "No newsletter reporting period in this date range."),
        ("substack", "Open rate · Substack",
         metrics.latest_with_change(substack, "date", "open_rate", f.start, f.end),
         fmt_pct, fmt_signed_pts, "No Substack open rate in this date range."),
        ("newsletter", "Click-through rate · Newsletter",
         metrics.latest_period_rate(periods, "click_rate_filtered", f.start, f.end),
         lambda v: fmt_pct(v, 2), fmt_signed_pts, "No newsletter reporting period in this date range."),
        ("substack", "Click-through rate · Substack",
         metrics.latest_with_change(substack, "date", "click_rate", f.start, f.end),
         lambda v: fmt_pct(v, 2), fmt_signed_pts, "No Substack click-through rate in this date range."),
    ]
    shown = [c for c in cards if f.shows(c[0])]
    if not shown:
        st.info("Pick at least one channel in the sidebar.")
        return
    for i in range(0, len(shown), 4):
        cols = st.columns(4)
        for col, (_, label, k, vfmt, cfmt, waiting) in zip(cols, shown[i:i + 4]):
            with col:
                kpi_card(label, k, vfmt, cfmt, waiting)
    st.caption(
        "Newsletter subscribers is the delivered count on each send. Newsletter open rate filters out Apple Mail "
        "Privacy Protection opens. Click-through rate is filtered unique clicks divided by delivered. "
        "Instagram click-through comes from ManyChat and is on the Qualitative reporting page."
    )

    st.header("Trends")
    sends_r = metrics.in_range(sends, "send_date", f.start, f.end)
    periods_r = metrics.overlaps(periods, "start_date", "end_date", f.start, f.end)
    sub_r = metrics.in_range(substack, "date", f.start, f.end)
    fol_r = metrics.in_range(followers, "date", f.start, f.end)
    by_date = lambda r: r["date"].strftime("%b %-d, %Y")  # noqa: E731

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Subscribers")
        line_chart([s for s in [
            ("newsletter", _series(sends_r, "send_date", "delivered", lambda r: r["send_date"].strftime("%b %-d send"))),
            ("substack", _series(sub_r, "date", "subscribers", by_date)),
        ] if f.shows(s[0])], ",d", "Subscribers")
    with c2:
        st.subheader("Followers")
        line_chart([s for s in [
            ("instagram", _series(fol_r[fol_r["channel"] == "instagram"], "date", "followers", by_date)),
            ("linkedin", _series(fol_r[fol_r["channel"] == "linkedin"], "date", "followers", by_date)),
        ] if f.shows(s[0])], ",d", "Followers")
    c3, c4 = st.columns(2)
    with c3:
        st.subheader("Open rate")
        line_chart([s for s in [
            ("newsletter", _series(periods_r, "end_date", "open_rate_filtered", lambda r: r["label"])),
            ("substack", _series(sub_r, "date", "open_rate", by_date)),
        ] if f.shows(s[0])], ".1%", "Open rate")
    with c4:
        st.subheader("Click-through rate")
        line_chart([s for s in [
            ("newsletter", _series(periods_r, "end_date", "click_rate_filtered", lambda r: r["label"])),
            ("substack", _series(sub_r, "date", "click_rate", by_date)),
        ] if f.shows(s[0])], ".2%", "Click-through rate")
    st.caption("Newsletter rate points are reporting periods, placed on the last day of each period.")

    with st.expander("Rows behind these numbers"):
        if f.shows("newsletter"):
            st.markdown("**Newsletter sends**")
            show_table(sends_r)
            st.markdown("**Newsletter reporting periods**")
            show_table(periods_r)
        if f.shows("instagram", "linkedin"):
            st.markdown("**Followers**")
            show_table(fol_r[fol_r["channel"].isin(f.channels)])
        if f.shows("substack"):
            st.markdown("**Substack**")
            show_table(sub_r)
