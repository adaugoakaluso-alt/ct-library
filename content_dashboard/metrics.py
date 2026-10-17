"""Calculations behind every number on the dashboard.

All functions take and return pandas DataFrames or plain values, with no
Streamlit code, so they can be tested on their own. Each KPI result keeps a
reference to the row it came from so the page can show it.
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


def latest_with_change(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    start: date,
    end: date,
    label_col: str | None = None,
) -> Kpi:
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
        source=None if "source" not in last or pd.isna(last["source"]) else str(last["source"]),
    )


def latest_period_rate(periods: pd.DataFrame, rate_col: str, start: date, end: date) -> Kpi:
    """Newsletter rates live on reporting periods. Use the last period that
    overlaps the date range and compare it with the period before it."""
    rows = periods.dropna(subset=[rate_col]).sort_values("end_date")
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
        source=None if pd.isna(last.get("source")) else str(last["source"]),
    )


# Instagram comment keywords, such as: Comment "AI NEWS" or Comment REGISTER
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


def keyword_table(posts: pd.DataFrame, manychat: pd.DataFrame) -> pd.DataFrame:
    """Comment keywords used in Instagram captions, with ManyChat clicks per keyword."""
    cols = ["Keyword", "Posts", "First used", "Last used", "ManyChat clicks"]
    ig = posts[posts["channel"] == "instagram"].copy()
    ig["keyword"] = ig["text"].map(extract_keyword)
    ig = ig.dropna(subset=["keyword"])
    if ig.empty:
        return pd.DataFrame(columns=cols)
    ig["key"] = ig["keyword"].map(normalize_keyword)
    grouped = ig.groupby("key").agg(
        Keyword=("keyword", lambda s: s.mode().iloc[0]),
        Posts=("post_id", "count"),
        **{"First used": ("date", "min"), "Last used": ("date", "max")},
    )
    clicks = pd.Series(dtype="Float64")
    if not manychat.empty:
        mc = manychat.dropna(subset=["keyword"]).copy()
        mc["key"] = mc["keyword"].map(normalize_keyword)
        clicks = mc.groupby("key")["clicks"].sum()
    grouped["ManyChat clicks"] = grouped.index.map(lambda k: clicks.get(k, pd.NA))
    return grouped.sort_values(["Posts", "Last used"], ascending=False).reset_index(drop=True)[cols]


def cta_ranking(links: pd.DataFrame, manychat: pd.DataFrame) -> pd.DataFrame:
    """Every CTA with a click count, newsletter links and ManyChat keywords together,
    ranked by clicks."""
    frames = []
    if not links.empty:
        nl = links.dropna(subset=["unique_clicks"])
        frames.append(pd.DataFrame({
            "CTA": [
                f'{t} ("{w}")' if isinstance(w, str) and w else t
                for t, w in zip(nl["link_text"], nl["cta_wording"].fillna(""))
            ],
            "Where used": "Email, " + nl["section"].fillna("link").astype(str) + " section",
            "Channel": "newsletter",
            "Date": nl["send_date"],
            "Clicks": nl["unique_clicks"],
            "Measure": "Unique link clicks",
            "Source": nl["source"],
        }))
    if not manychat.empty:
        mc = manychat.dropna(subset=["clicks"])
        frames.append(pd.DataFrame({
            "CTA": [t if isinstance(t, str) and t else f'Comment "{k}"' for t, k in zip(mc["cta_text"].fillna(""), mc["keyword"])],
            "Where used": "Instagram DM automation",
            "Channel": "instagram",
            "Date": mc["date"],
            "Clicks": mc["clicks"],
            "Measure": "ManyChat link clicks",
            "Source": mc["source"],
        }))
    if not frames:
        return pd.DataFrame(columns=["Rank", "CTA", "Where used", "Channel", "Date", "Clicks", "Measure", "Source"])
    out = pd.concat(frames, ignore_index=True).sort_values(["Clicks", "Date"], ascending=False).reset_index(drop=True)
    out.insert(0, "Rank", range(1, len(out) + 1))
    return out


FORMAT_METRICS = {"likes": "Likes", "comments": "Comments", "shares": "Shares", "saves": "Saves"}


def format_comparison(posts: pd.DataFrame) -> pd.DataFrame:
    """Average likes, comments, shares and saves per Instagram feed post,
    static carousels against videos. Posts with no metrics are left out."""
    ig = posts[(posts["channel"] == "instagram") & posts["format"].isin(["carousel", "video"])]
    ig = ig.dropna(subset=["likes"])
    rows = []
    for fmt, label in (("carousel", "Static carousel"), ("video", "Video (reels)")):
        sub = ig[ig["format"] == fmt]
        row = {"format": fmt, "Format": label, "Posts counted": len(sub)}
        for col, name in FORMAT_METRICS.items():
            row[f"Avg {name.lower()}"] = float(sub[col].astype("Float64").mean()) if sub[col].notna().any() else None
        rows.append(row)
    return pd.DataFrame(rows)


def format_takeaway(table: pd.DataFrame) -> str:
    if table.empty or (table["Posts counted"] == 0).any():
        return "Not enough posts of both formats in this date range to compare."
    car = table.set_index("format").loc["carousel"]
    vid = table.set_index("format").loc["video"]
    video_wins, carousel_wins = [], []
    for name in FORMAT_METRICS.values():
        c, v = car[f"Avg {name.lower()}"], vid[f"Avg {name.lower()}"]
        if c is None or v is None or pd.isna(c) or pd.isna(v):
            continue
        if v > c:
            video_wins.append(name.lower())
        elif c > v:
            carousel_wins.append(name.lower())
    parts = []
    if video_wins:
        parts.append("Videos average more " + ", ".join(video_wins) + ".")
    if carousel_wins:
        parts.append("Carousels average more " + ", ".join(carousel_wins) + ".")
    return " ".join(parts) or "Carousels and videos average the same."
