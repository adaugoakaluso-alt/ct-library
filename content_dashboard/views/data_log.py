"""Page 3: Data log. Every table behind the dashboard, with the source of each row."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import storage
from ..components import Filters, show_table
from ..storage import EMPTY, SAMPLE, Table


def render(tables: dict[str, Table], f: Filters) -> None:
    brand = f.brand
    st.title("Data log")
    st.caption("Every number on the other pages comes from one of these tables. The source column says where each row came from.")
    use_filters = st.toggle("Apply the sidebar date range and channels", value=True)

    kinds = {c.kind for c in brand.channels}
    for name, table in tables.items():
        ds = table.dataset
        if not kinds.intersection(ds.kinds):
            continue  # for example, no email table for a brand with no email channels
        st.header(ds.title)
        badge = {SAMPLE: "Sample data", EMPTY: "No data yet"}.get(table.origin, "Your data")
        st.caption(f"{badge}. {ds.description} Where to get it: {ds.where_to_get_it}")
        df = table.df
        if use_filters and not df.empty:
            df = df[(df[ds.date_column] >= pd.Timestamp(f.start)) & (df[ds.date_column] <= pd.Timestamp(f.end))]
            df = df[df["channel"].isin(f.channels)]
        if df.empty:
            st.caption("No rows" + (" in this date range." if use_filters else " yet."))
        else:
            show_table(df.assign(channel=df["channel"].map(brand.channel_name)).sort_values(ds.date_column, ascending=False))
        st.download_button(
            f"Download {ds.title} as CSV",
            storage.to_csv_frame(table.df, ds).to_csv(index=False),
            file_name=f"{brand.id}-{name}.csv", mime="text/csv", key=f"dl-{name}",
            disabled=table.df.empty,
        )
