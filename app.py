"""Content reporting dashboard.

Run with:  streamlit run app.py
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from content_dashboard import brands, storage
from content_dashboard.components import Filters
from content_dashboard.views import data_log, general, qualitative, update_data

try:
    all_brands = brands.list_brands()
except brands.BrandError as exc:
    st.set_page_config(page_title="Content reporting", layout="wide")
    st.error(f"A brand file needs fixing: {exc}")
    st.stop()

ids = list(all_brands)
default = brands.default_brand_id(all_brands)
brand_id = st.session_state.get("brand", default)
brand = all_brands.get(brand_id, all_brands[default])

st.set_page_config(page_title=brand.title, layout="wide")
tables = storage.load_all(brand)


def _earliest_date() -> date:
    dates = [
        t.df[t.dataset.date_column].min()
        for t in tables.values()
        if not t.df.empty and t.df[t.dataset.date_column].notna().any()
    ]
    return min(dates).date() if dates else date.today().replace(day=1)


with st.sidebar:
    if len(ids) > 1:
        st.selectbox("Brand", ids, index=ids.index(brand.id), format_func=lambda b: all_brands[b].name, key="brand")
    st.markdown(f"### {brand.title}")
    picked = st.date_input("Date range", value=(_earliest_date(), date.today()), format="YYYY-MM-DD", key=f"range-{brand.id}")
    # While someone is mid-way through picking a range, only the start date is set.
    if isinstance(picked, (tuple, list)):
        start, end = (picked[0], picked[-1]) if picked else (_earliest_date(), date.today())
    else:
        start = end = picked
    channels = st.multiselect(
        "Channels", brand.channel_ids, default=brand.channel_ids,
        format_func=brand.channel_name, key=f"channels-{brand.id}",
    )
    if any(t.is_sample for t in tables.values()):
        st.caption("This brand is showing sample data. See the Data log.")

filters = Filters(brand=brand, start=pd.Timestamp(start).date(), end=pd.Timestamp(end).date(), channels=channels)


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
