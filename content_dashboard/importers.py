"""Readers for exports downloaded from the platforms themselves.

LinkedIn content export
  LinkedIn page > Analytics > Content > Export gives an .xls file with an
  "All posts" sheet: one row per post with impressions, clicks, likes,
  comments and reposts. Buffer does not report LinkedIn clicks, so this
  export fills that gap. The "Posted by" column (people's names) is not kept.
"""

from __future__ import annotations

import re
from datetime import date

import pandas as pd

LINKEDIN_SHEET = "All posts"

# LinkedIn column -> social_posts column
LINKEDIN_COLUMNS = {
    "Impressions": "impressions",
    "Views": "views",
    "Clicks": "clicks",
    "Likes": "likes",
    "Comments": "comments",
    "Reposts": "shares",
}
METRIC_COLUMNS = list(LINKEDIN_COLUMNS.values())


class ImportProblem(Exception):
    """The file is not the export we expected. The message says what to do."""


def _match_key(text) -> str:
    """First 40 letters and digits of a post, lowercased. Used to pair an export
    row with the same post pulled from Buffer."""
    return re.sub(r"[^a-z0-9]", "", str(text or "").lower())[:40]


def read_linkedin_content_export(file) -> pd.DataFrame:
    """Read the "All posts" sheet of a LinkedIn content export into social_posts rows."""
    try:
        sheets = pd.read_excel(file, sheet_name=None, header=None, dtype=str)
    except Exception as exc:  # not an Excel file, or a damaged one
        raise ImportProblem(f"Could not open that file as an Excel export: {exc}") from exc
    if LINKEDIN_SHEET not in sheets:
        raise ImportProblem(
            f"This file has no '{LINKEDIN_SHEET}' sheet. Use the content export from your LinkedIn page: "
            "Analytics > Content > Export."
        )
    raw = sheets[LINKEDIN_SHEET]
    # The first row is a note from LinkedIn. The header row is the one that starts with "Post title".
    header_rows = raw.index[raw.iloc[:, 0].astype(str).str.strip() == "Post title"]
    if not len(header_rows):
        raise ImportProblem("Could not find the header row (starting with 'Post title') in the 'All posts' sheet.")
    h = header_rows[0]
    df = raw.iloc[h + 1:].copy()
    df.columns = [str(c).strip() for c in raw.iloc[h]]
    df = df.dropna(subset=["Post title"])
    missing = [c for c in ["Post title", "Post link", "Created date", *LINKEDIN_COLUMNS] if c not in df.columns]
    if missing:
        raise ImportProblem("The 'All posts' sheet is missing columns: " + ", ".join(missing) + ".")

    pulled = date.today().isoformat()
    out = pd.DataFrame({
        "post_id": "li-" + df["Post link"].astype(str).str.extract(r"(\d{10,})", expand=False).fillna(df["Post link"].astype(str)),
        "date": pd.to_datetime(df["Created date"], format="%m/%d/%Y", errors="coerce").dt.strftime("%Y-%m-%d"),
        "channel": "linkedin",
        "format": df.get("Content Type", pd.Series("", index=df.index)).fillna("").str.strip().str.lower()
        .map(lambda t: "video" if t == "video" else "other"),
        "text": df["Post title"],
        "source": f"LinkedIn content export, {pulled}",
    })
    for src, col in LINKEDIN_COLUMNS.items():
        out[col] = pd.to_numeric(df[src], errors="coerce").round()
    return out.reset_index(drop=True)


def merge_linkedin_export(existing: pd.DataFrame, export: pd.DataFrame) -> tuple[pd.DataFrame, int, int]:
    """Fold LinkedIn export rows into the existing posts table.

    A post already in the table (same text start, created within a day) keeps
    its id and format and takes LinkedIn's numbers. Posts not in the table yet
    are added. Returns the merged table, how many posts were updated and how
    many were added.
    """
    merged = existing.copy()
    if "clicks" not in merged.columns:
        merged["clicks"] = pd.NA
    li = merged[merged["channel"] == "linkedin"]
    keys = li["text"].map(_match_key)
    dates = pd.to_datetime(li["date"])
    updated, new_rows = 0, []
    for _, row in export.iterrows():
        key = _match_key(row["text"])
        when = pd.to_datetime(row["date"])
        hits = li.index[(keys == key) & ((dates - when).abs() <= pd.Timedelta(days=1))] if key else []
        if len(hits):
            i = hits[0]
            for col in METRIC_COLUMNS:
                if pd.notna(row[col]):
                    merged.loc[i, col] = row[col]
            prev = merged.loc[i, "source"]
            prev = "" if pd.isna(prev) else str(prev).split("; numbers from ")[0]
            merged.loc[i, "source"] = f"{prev}; numbers from {row['source']}" if prev else row["source"]
            updated += 1
        else:
            new_rows.append(row)
    if new_rows:
        merged = pd.concat([merged, pd.DataFrame(new_rows)], ignore_index=True)
    return merged, updated, len(new_rows)
