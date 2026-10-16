"""AI Edge content reporting dashboard.

Run with:  streamlit run app.py
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from ai_edge_dashboard import config, storage
from ai_edge_dashboard.components import Filters
from ai_edge_dashboard.views import data_log, general, qualitative, update_data

st.set_page_config(page_title=config.APP_TITLE, layout="wide")

tables = storage.load_all()


def _earliest_date() -> date:
    dates = [
        t.df[t.dataset.date_column].min()
        for t in tables.values()
        if not t.df.empty and t.df[t.dataset.date_column].notna().any()
    ]
    return min(dates).date() if dates else date.today().replace(day=1)


with st.sidebar:
    st.markdown(f"### {config.APP_TITLE}")
    picked = st.date_input("Date range", value=(_earliest_date(), date.today()), format="YYYY-MM-DD")
    # While someone is mid-way through picking a range, only the start date is set.
    if isinstance(picked, (tuple, list)):
        start, end = (picked[0], picked[-1]) if picked else (_earliest_date(), date.today())
    else:
        start = end = picked
    channels = st.multiselect(
        "Channels", list(config.CHANNELS), default=list(config.CHANNELS), format_func=config.CHANNELS.get
    )
    if any(t.is_sample for t in tables.values()):
        st.caption("Some tables are showing sample data. See the Data log.")

filters = Filters(start=pd.Timestamp(start).date(), end=pd.Timestamp(end).date(), channels=channels)


def general_page():
    general.render(tables, filters)


def qualitative_page():
    qualitative.render(tables, filters)


def data_log_page():
    data_log.render(tables, filters)


def update_data_page():
    update_data.render(tables, filters)


nav = st.navigation([
    st.Page(general_page, title="General reporting", default=True),
    st.Page(qualitative_page, title="Qualitative reporting", url_path="qualitative"),
    st.Page(data_log_page, title="Data log", url_path="data-log"),
    st.Page(update_data_page, title="Update data", url_path="update-data"),
])
nav.run()
