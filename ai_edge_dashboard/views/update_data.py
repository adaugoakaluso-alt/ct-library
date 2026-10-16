"""Update data: CSV upload, one-row entry forms and connector pulls.

Everything saves through storage.save(), which writes to data/<table>.csv.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from .. import config, schemas, storage
from ..components import Filters, show_table
from ..connectors import REGISTRY, ConnectorError
from ..schemas import DATE, FLOAT, INT, RATE, Dataset
from ..storage import Table

FLASH = "update_data_flash"


def _flash(msg: str) -> None:
    st.session_state[FLASH] = msg
    st.rerun()


def _schema_table(ds: Dataset) -> pd.DataFrame:
    kinds = {DATE: "date (YYYY-MM-DD)", INT: "whole number", FLOAT: "number", RATE: "rate as a share (0.179 = 17.9%)"}
    return pd.DataFrame([{
        "Column": c.name,
        "Type": kinds.get(c.kind, "text") + (f": {', '.join(c.choices)}" if c.choices else ""),
        "Required": "Yes" if c.required else "No",
        "What it is": c.help,
    } for c in ds.columns])


def _upload(ds: Dataset, table: Table) -> None:
    file = st.file_uploader(f"CSV file for {ds.title}", type=["csv"], key=f"up-{ds.name}")
    if not file:
        st.caption("The first row must hold the column names. Download the template below if you need one.")
        return
    try:
        raw = pd.read_csv(file, dtype=str, keep_default_na=False, na_values=[""])
    except Exception as exc:  # unreadable file
        st.error(f"Could not read that file as CSV: {exc}")
        return
    if "source" not in raw.columns or raw["source"].isna().all():
        raw["source"] = f"CSV upload, {date.today().isoformat()}"
    clean, problems = storage.validate(raw, ds)
    if problems:
        st.error("Fix these and upload again:\n\n" + "\n".join(f"- {p}" for p in problems))
        return
    st.success(f"{len(clean)} rows look good.")
    show_table(clean.head(50))
    has_own = table.origin == storage.YOUR_DATA
    mode = st.radio(
        "How to save",
        ["Add to my data", "Replace all my data for this table"] if has_own else ["Save as my data"],
        key=f"mode-{ds.name}",
        help="Adding keeps your existing rows. A new row with the same " + " + ".join(ds.key) + " replaces the old one.",
    )
    if st.button("Save rows", key=f"save-up-{ds.name}", type="primary"):
        total = storage.save(ds.name, clean, "replace" if mode.startswith("Replace") else "append")
        _flash(f"Saved. {ds.title} now has {total} rows.")


def _form(ds: Dataset) -> None:
    with st.form(f"form-{ds.name}", clear_on_submit=True):
        values: dict = {}
        cols = st.columns(2)
        for i, c in enumerate(col for col in ds.columns if col.name != "source"):
            label = c.name + ("" if c.required else " (optional)")
            with cols[i % 2]:
                if c.kind == DATE:
                    values[c.name] = st.date_input(label, value=date.today(), help=c.help, format="YYYY-MM-DD")
                elif c.choices:
                    values[c.name] = st.selectbox(label, c.choices, help=c.help)
                elif c.kind == INT:
                    values[c.name] = st.number_input(label, min_value=0, step=1, value=None, help=c.help)
                elif c.kind == RATE:
                    pct = st.number_input(label + ", in %", min_value=0.0, max_value=100.0, step=0.1, value=None, format="%.2f", help=c.help)
                    values[c.name] = None if pct is None else pct / 100
                elif c.kind == FLOAT:
                    values[c.name] = st.number_input(label, value=None, help=c.help)
                elif c.name == "text":
                    values[c.name] = st.text_area(label, help=c.help)
                else:
                    values[c.name] = st.text_input(label, help=c.help)
        values["source"] = st.text_input("source", value="Manual entry", help=schemas.SOURCE.help)
        if st.form_submit_button("Save row", type="primary"):
            row = pd.DataFrame([{k: ("" if v is None else str(v)) for k, v in values.items()}])
            clean, problems = storage.validate(row, ds)
            if problems:
                st.error("Not saved:\n\n" + "\n".join(f"- {p}" for p in problems))
            else:
                total = storage.save(ds.name, clean, "append")
                _flash(f"Saved. {ds.title} now has {total} rows.")


def _connectors(tables: dict[str, Table], f: Filters) -> None:
    st.header("Pull from a connected source")
    st.caption("Connectors fill a table automatically. Their settings come from environment variables, described in .env.example.")
    for conn in REGISTRY:
        ds = schemas.get(conn.dataset)
        with st.container(border=True):
            st.markdown(f"**{conn.name}** fills **{ds.title}**")
            st.caption(conn.description)
            if not conn.implemented:
                st.caption("Status: not built yet.")
                continue
            missing = conn.missing_settings()
            if missing:
                st.caption("Status: not set up. Missing settings: " + ", ".join(missing) + ".")
                continue
            c1, c2 = st.columns(2)
            start = c1.date_input("From", value=max(f.start, date.today() - timedelta(days=90)), key=f"cs-{conn.name}")
            end = c2.date_input("To", value=date.today(), key=f"ce-{conn.name}")
            if st.button(f"Pull from {conn.name}", key=f"pull-{conn.name}", type="primary"):
                try:
                    with st.spinner(f"Pulling from {conn.name}"):
                        rows = conn.fetch(start, end)
                except ConnectorError as exc:
                    st.error(str(exc))
                    continue
                if rows.empty:
                    st.info("Nothing came back for those dates.")
                    continue
                clean, problems = storage.validate(rows, ds)
                if problems:
                    st.error(f"{conn.name} sent rows that do not fit the {ds.title} table:\n\n" + "\n".join(f"- {p}" for p in problems))
                    continue
                total = storage.save(ds.name, clean, "append")
                _flash(f"Pulled {len(clean)} rows from {conn.name}. {ds.title} now has {total} rows.")


def render(tables: dict[str, Table], f: Filters) -> None:
    st.title("Update data")
    if msg := st.session_state.pop(FLASH, None):
        st.success(msg)
    st.caption(
        "Add numbers each reporting period. Saved rows go to the data folder in this repo, "
        f"which git ignores, so your numbers stay off GitHub. Data folder: {config.DATA_DIR.relative_to(config.REPO_ROOT) if config.DATA_DIR.is_relative_to(config.REPO_ROOT) else config.DATA_DIR}"
    )

    names = list(schemas.DATASETS)
    name = st.selectbox("Table", names, format_func=lambda n: schemas.get(n).title)
    ds = schemas.get(name)
    table = tables[name]
    status = {storage.SAMPLE: "showing sample data until you add your own", storage.EMPTY: "empty"}.get(table.origin, f"{len(table.df)} rows of your data")
    st.caption(f"{ds.description} Where to get it: {ds.where_to_get_it} Right now: {status}.")

    tab_upload, tab_form, tab_schema = st.tabs(["Upload a CSV", "Enter one row", "Columns and template"])
    with tab_upload:
        _upload(ds, table)
    with tab_form:
        _form(ds)
    with tab_schema:
        show_table(_schema_table(ds))
        st.caption("Each row is unique by: " + " + ".join(ds.key) + ".")
        st.download_button(
            "Download empty template", storage.template_csv(name), file_name=f"{name}.csv", mime="text/csv", key=f"tpl-{name}"
        )

    _connectors(tables, f)
