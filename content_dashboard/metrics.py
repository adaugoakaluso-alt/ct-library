"""Calculations behind every number on the dashboard.

All functions take and return pandas DataFrames or plain values, with no
Streamlit code, so they can be tested on their own. Nothing here names a
platform: channels come from the brand file and are passed in.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

import pandas as pd


@dataclass
class Kpi:
    value: float | None
    change: float | None = None
    previous_label: str | None = None
    range_change: float | None = None
    as_of: pd.Timestamp | None = None
    row_label: str | None = None
    source: str | None = None


def in_range(df: pd.DataFrame, col: str, start: date, end: date) -> pd.DataFrame:
    if df.empty:
        return df
    d = df[col]
    return df[(d >= pd.Timestamp(start)) & (d <= pd.Timestamp(end))]


def overlaps(df: pd.DataFrame, start_col: str, end_col: str, start: date, end: date) -> pd.DataFrame:
    if df.empty:
        return df
    return df[(df[end_col] >= pd.Timestamp(start)) & (df[start_col] <= pd.Timestamp(end))]


def _num(v) -> float | None:
    return None if v is None or pd.isna(v) else float(v)


def _src(row) -> str | None:
    v = row.get("source") if hasattr(row, "get") else None
    return None if v is None or pd.isna(v) else str(v)


def latest_with_change(df: pd.DataFrame, date_col: str, value_col: str, start: date, end: date, label_col: str | None = None) -> Kpi:
    """Latest value in the date range, its change from the row before it, and
    its change across the range (first to last row in range)."""
    rows = df.dropna(subset=[value_col]).sort_values(date_col)
    if rows.empty:
        return Kpi(None)
    window = in_range(rows, date_col, start, end)
    if window.empty:
        return Kpi(None)
    last = window.iloc[-1]
    pos = rows.index.get_loc(last.name)
    prev = rows.iloc[pos - 1] if pos > 0 else None
    first_in_range = window.iloc[0]
    return Kpi(
        value=_num(last[value_col]),
        change=None if prev is None else _num(last[value_col]) - _num(prev[value_col]),
        previous_label=None if prev is None else (str(prev[label_col]) if label_col else prev[date_col].strftime("%b %-d")),
        range_change=_num(last[value_col]) - _num(first_in_range[value_col]) if len(window) > 1 else None,
        as_of=last[date_col],
        row_label=str(last[label_col]) if label_col else last[date_col].strftime("%b %-d, %Y"),
        source=_src(last),
    )


def audience_kpi(audience: pd.DataFrame, channel: str, metric: str, start: date, end: date) -> Kpi:
    rows = audience[(audience["channel"] == channel) & (audience["metric"] == metric)]
    return latest_with_change(rows, "date", "value", start, end)


def email_rate_kpi(email_stats: pd.DataFrame, channel: str, rate_col: str, start: date, end: date) -> Kpi:
    """Email rates live on sends or reporting periods. Use the last one that
    overlaps the date range and compare it with the one before it."""
    rows = email_stats[email_stats["channel"] == channel].dropna(subset=[rate_col]).sort_values(["end_date", "start_date"])
    if rows.empty:
        return Kpi(None)
    window = overlaps(rows, "start_date", "end_date", start, end)
    if window.empty:
        return Kpi(None)
    last = window.iloc[-1]
    pos = rows.index.get_loc(last.name)
    prev = rows.iloc[pos - 1] if pos > 0 else None
    return Kpi(
        value=_num(last[rate_col]),
        change=None if prev is None else _num(last[rate_col]) - _num(prev[rate_col]),
        previous_label=None if prev is None else str(prev["label"]),
        as_of=last["end_date"],
        row_label=str(last["label"]),
        source=_src(last),
    )


# Comment keywords, such as: Comment "AI NEWS" or Comment REGISTER
_QUOTED = re.compile(r"[Cc]omment\s*[“\"'‘]\s*([^”\"'’\n]{2,24}?)\s*[”\"'’]")
_BARE = re.compile(r"[Cc]omment\s+([A-Z][A-Z]{2,20})\b")


def extract_keyword(text) -> str | None:
    """Return the comment keyword a caption asks for, written as in the post."""
    if text is None or pd.isna(text):
        return None
    m = _QUOTED.search(str(text)) or _BARE.search(str(text))
    return m.group(1).strip().upper() if m else None


def normalize_keyword(keyword) -> str:
    return re.sub(r"\s+", "", str(keyword)).upper()


def keyword_table(posts: pd.DataFrame, cta_clicks: pd.DataFrame) -> pd.DataFrame:
    """Comment keywords used in captions, with DM automation clicks per keyword."""
    cols = ["Keyword", "Posts", "First used", "Last used", "Clicks"]
    p = posts.copy()
    p["keyword"] = p["text"].map(extract_keyword)
    p = p.dropna(subset=["keyword"])
    if p.empty:
        return pd.DataFrame(columns=cols)
    p["key"] = p["keyword"].map(normalize_keyword)
    grouped = p.groupby("key").agg(
        Keyword=("keyword", lambda s: s.mode().iloc[0]),
        Posts=("post_id", "count"),
        **{"First used": ("date", "min"), "Last used": ("date", "max")},
    )
    clicks = pd.Series(dtype="Float64")
    kw = cta_clicks.dropna(subset=["keyword"]) if not cta_clicks.empty else cta_clicks
    if not kw.empty:
        kw = kw.assign(key=kw["keyword"].map(normalize_keyword))
        clicks = kw.groupby("key")["clicks"].sum()
    grouped["Clicks"] = grouped.index.map(lambda k: clicks.get(k, pd.NA))
    return grouped.sort_values(["Posts", "Last used"], ascending=False).reset_index(drop=True)[cols]


def cta_ranking(cta_clicks: pd.DataFrame, channel_name) -> pd.DataFrame:
    """Every CTA with a click count, across channels, ranked by clicks."""
    cols = ["Rank", "CTA", "Where used", "Channel", "Date", "Clicks", "Measure", "Source"]
    rows = cta_clicks.dropna(subset=["clicks"])
    if rows.empty:
        return pd.DataFrame(columns=cols)
    out = pd.DataFrame({
        "CTA": rows["cta"],
        "Where used": rows["where_used"],
        "Channel": rows["channel"].map(channel_name),
        "Date": rows["date"],
        "Clicks": rows["clicks"],
        "Measure": rows["measure"],
        "Source": rows["source"],
    }).sort_values(["Clicks", "Date"], ascending=False).reset_index(drop=True)
    out.insert(0, "Rank", range(1, len(out) + 1))
    return out[cols]


ENGAGEMENT = {"likes": "Likes", "comments": "Comments", "shares": "Shares", "saves": "Saves"}


def format_comparison(posts: pd.DataFrame, formats: list[str]) -> pd.DataFrame:
    """Average likes, comments, shares and saves per post for each format.
    Pass one channel's posts. Posts with no metrics are left out."""
    p = posts.dropna(subset=["likes"])
    rows = []
    for fmt in formats:
        sub = p[p["format"] == fmt]
        row = {"format": fmt, "Format": fmt.capitalize(), "Posts counted": len(sub)}
        for col, name in ENGAGEMENT.items():
            row[f"Avg {name.lower()}"] = float(sub[col].astype("Float64").mean()) if sub[col].notna().any() else None
        rows.append(row)
    return pd.DataFrame(rows)


def format_takeaway(table: pd.DataFrame) -> str:
    counted = table[table["Posts counted"] > 0]
    if len(counted) < 2:
        return "Not enough posts in two or more formats in this date range to compare."
    lines = []
    for name in ENGAGEMENT.values():
        col = f"Avg {name.lower()}"
        vals = counted.dropna(subset=[col])
        if len(vals) < 2:
            continue
        best = vals.sort_values(col, ascending=False).iloc[0]
        if (vals[col] == best[col]).sum() == 1:
            lines.append(f"{best['Format']} posts average the most {name.lower()}.")
    return " ".join(lines) or "The formats average about the same."


def posts_by_clicks(posts: pd.DataFrame) -> pd.DataFrame:
    p = posts[posts["clicks"].notna() & (posts["clicks"] > 0)].copy()
    if p.empty:
        return p
    p["click_rate"] = (p["clicks"] / p["impressions"] * 100).where(p["impressions"] > 0)
    return p.sort_values(["clicks", "date"], ascending=False)
