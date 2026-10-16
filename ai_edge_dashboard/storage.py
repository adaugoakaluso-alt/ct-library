"""Load, validate and save the CSV tables.

Each table lives in one CSV file named after its schema, such as
data/followers.csv. While the data folder is empty (a fresh clone), every table
is read from sample_data/ and labeled as sample data. Once you save any real
table, sample data is switched off everywhere and tables you have not filled
yet show as empty.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from . import config, schemas
from .schemas import DATE, FLOAT, INT, RATE, TEXT, Dataset

YOUR_DATA = "your data"
SAMPLE = "sample data"
EMPTY = "no data yet"


@dataclass
class Table:
    dataset: Dataset
    df: pd.DataFrame
    origin: str  # YOUR_DATA, SAMPLE or EMPTY
    path: Path | None

    @property
    def is_sample(self) -> bool:
        return self.origin == SAMPLE


def data_path(name: str) -> Path:
    return config.DATA_DIR / f"{name}.csv"


def sample_path(name: str) -> Path:
    return config.SAMPLE_DIR / f"{name}.csv"


def empty_frame(ds: Dataset) -> pd.DataFrame:
    return coerce(pd.DataFrame(columns=ds.column_names), ds)


def coerce(df: pd.DataFrame, ds: Dataset) -> pd.DataFrame:
    """Give every schema column its type. Unknown extra columns are kept at the end."""
    out = df.copy()
    for col in ds.columns:
        if col.name not in out.columns:
            out[col.name] = pd.NA
        s = out[col.name]
        if col.kind == DATE:
            out[col.name] = pd.to_datetime(s, errors="coerce").dt.normalize()
        elif col.kind == INT:
            out[col.name] = pd.to_numeric(s, errors="coerce").round().astype("Int64")
        elif col.kind in (FLOAT, RATE):
            out[col.name] = pd.to_numeric(s, errors="coerce").astype("Float64")
        else:
            out[col.name] = s.astype("string").str.strip()
    extras = [c for c in out.columns if c not in ds.column_names]
    return out[ds.column_names + extras]


def has_own_data() -> bool:
    """True once any table has a file in the data folder."""
    return any(data_path(name).exists() for name in schemas.DATASETS)


def load(name: str, allow_sample: bool | None = None) -> Table:
    """Load one table from data/, else from sample_data/.

    Sample data is all or nothing: it is only used while the data folder has
    no tables at all, so sample numbers never sit next to real ones.
    """
    ds = schemas.get(name)
    if allow_sample is None:
        allow_sample = not has_own_data()
    candidates = [(data_path(name), YOUR_DATA)]
    if allow_sample:
        candidates.append((sample_path(name), SAMPLE))
    for path, origin in candidates:
        if path.exists():
            df = pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])
            return Table(ds, coerce(df, ds), origin, path)
    return Table(ds, empty_frame(ds), EMPTY, None)


def load_all() -> dict[str, Table]:
    allow_sample = not has_own_data()
    return {name: load(name, allow_sample) for name in schemas.DATASETS}


def validate(df: pd.DataFrame, ds: Dataset) -> tuple[pd.DataFrame, list[str]]:
    """Check an uploaded or typed-in table against its schema.

    Returns the cleaned table and a list of problems in plain words. An empty
    list means the rows are safe to save.
    """
    problems: list[str] = []
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    missing = [c.name for c in ds.columns if c.required and c.name not in df.columns]
    if missing:
        problems.append("Missing columns: " + ", ".join(missing) + ". Download the template to see the expected columns.")
        return df, problems
    if df.empty:
        problems.append("The file has no rows.")
        return df, problems

    raw = df.copy()
    clean = coerce(df, ds)
    for col in ds.columns:
        if col.name not in raw.columns:
            continue
        given = raw[col.name].astype("string").str.strip()
        has_value = given.notna() & (given != "")
        if col.required:
            blank = (~has_value).sum()
            if blank:
                problems.append(f"{col.name}: {blank} row(s) are blank. This column is required.")
        if col.kind in (DATE, INT, FLOAT, RATE):
            bad = has_value & clean[col.name].isna()
            if bad.any():
                example = given[bad].iloc[0]
                what = "a date like 2026-10-05" if col.kind == DATE else "a number"
                problems.append(f"{col.name}: {int(bad.sum())} value(s) are not {what}, for example '{example}'.")
        if col.kind == RATE:
            over = clean[col.name].notna() & (clean[col.name] > 1)
            if over.any():
                problems.append(f"{col.name}: enter rates as shares, so 17.9% is 0.179. Found {clean.loc[over, col.name].iloc[0]}.")
        if col.choices:
            vals = clean[col.name].dropna()
            wrong = vals[~vals.str.lower().isin(col.choices)]
            if len(wrong):
                problems.append(f"{col.name}: '{wrong.iloc[0]}' is not one of: {', '.join(col.choices)}.")
            clean[col.name] = clean[col.name].str.lower()

    dupes = clean.duplicated(subset=list(ds.key), keep=False)
    if dupes.any():
        problems.append(f"{int(dupes.sum())} rows share the same {' + '.join(ds.key)}. Each row needs a unique {' + '.join(ds.key)}.")
    return clean, problems


def to_csv_frame(df: pd.DataFrame, ds: Dataset) -> pd.DataFrame:
    out = df.copy()
    for col in ds.columns:
        if col.kind == DATE and col.name in out.columns:
            out[col.name] = pd.to_datetime(out[col.name], errors="coerce").dt.strftime("%Y-%m-%d")
    return out


def save(name: str, new_rows: pd.DataFrame, mode: str = "append") -> int:
    """Write rows to data/<name>.csv and return how many rows the file now has.

    mode="append" adds the rows to your existing data. A new row with the same
    key as an existing one updates it: filled-in values win, and blank values
    keep what was there, so a Buffer pull does not wipe LinkedIn clicks that
    came from an export. mode="replace" overwrites the file.
    Sample data is never written to or merged in.
    """
    ds = schemas.get(name)
    new_rows = coerce(new_rows, ds)
    path = data_path(name)
    if mode == "append" and path.exists():
        current = load(name, allow_sample=False).df
        key = list(ds.key)
        new_rows = new_rows.drop_duplicates(subset=key, keep="last").set_index(key)
        current = current.drop_duplicates(subset=key, keep="last").set_index(key)
        combined = new_rows.combine_first(current).reset_index()
        combined = coerce(combined, ds)
    else:
        combined = new_rows
    combined = combined.sort_values(ds.date_column, ascending=False, na_position="last")
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    to_csv_frame(combined, ds).to_csv(path, index=False)
    return len(combined)


def template_csv(name: str) -> str:
    """Header-only CSV for a table, for people to fill in."""
    return ",".join(schemas.get(name).column_names) + "\n"
