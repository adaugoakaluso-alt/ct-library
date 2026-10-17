"""Page 2: Qualitative reporting. Best-performing CTAs ranked, and Instagram
static carousels against videos."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from .. import config, metrics
from ..components import Filters, origin_note, show_table
from ..storage import Table


def render(tables: dict[str, Table], f: Filters) -> None:
    links = metrics.in_range(tables["newsletter_links"].df, "send_date", f.start, f.end)
    manychat = metrics.in_range(tables["manychat_clicks"].df, "date", f.start, f.end)
    posts = metrics.in_range(tables["social_posts"].df, "date", f.start, f.end)

    st.title("Qualitative reporting")
    st.caption(f"{f.start:%b %-d, %Y} to {f.end:%b %-d, %Y}.")
    origin_note(tables["newsletter_links"], tables["manychat_clicks"], tables["social_posts"])

    # Best-performing CTAs
    st.header("Best-performing CTAs")
    st.caption(
        "Ranked by clicks. Newsletter clicks are unique link clicks from Iterable. "
        "Instagram clicks come from ManyChat, the source of truth for Instagram click-through."
    )
    ranking = metrics.cta_ranking(
        links if f.shows("newsletter") else links.iloc[0:0],
        manychat if f.shows("instagram") else manychat.iloc[0:0],
    )
    if ranking.empty:
        st.caption("No CTAs with clicks in this date range and channel selection.")
    else:
        ranking["Channel"] = ranking["Channel"].map(config.CHANNELS)
        show_table(ranking, column_config={
            "Date": st.column_config.DateColumn(format="MMM D, YYYY"),
            "Clicks": st.column_config.NumberColumn(format="%d"),
        })

    if f.shows("instagram"):
        st.subheader("Instagram comment keywords")
        st.caption("Keywords found in Instagram captions, such as Comment \"AI NEWS\", with ManyChat clicks for each keyword once they are logged.")
        kw = metrics.keyword_table(posts, manychat)
        if kw.empty:
            st.caption("No comment keywords found in Instagram captions in this date range.")
        else:
            show_table(kw, column_config={
                "First used": st.column_config.DateColumn(format="MMM D, YYYY"),
                "Last used": st.column_config.DateColumn(format="MMM D, YYYY"),
                "ManyChat clicks": st.column_config.NumberColumn(format="%d"),
            })

    if f.shows("linkedin"):
        st.subheader("LinkedIn posts by clicks")
        st.caption(
            "From the LinkedIn content export. LinkedIn counts any click on a post, including opening it or "
            "seeing more text, so these are not the same measure as link clicks above."
        )
        li = posts[(posts["channel"] == "linkedin") & posts["clicks"].notna() & (posts["clicks"] > 0)]
        if li.empty:
            st.caption("No LinkedIn clicks in this date range. Upload a LinkedIn content export on the Update data page.")
        else:
            li_table = li.assign(
                **{"Click-through rate": (li["clicks"] / li["impressions"] * 100).where(li["impressions"] > 0)}
            ).sort_values(["clicks", "date"], ascending=False)
            li_table = li_table.rename(columns={"date": "Date", "text": "Post", "clicks": "Clicks", "impressions": "Impressions", "source": "Source"})
            show_table(li_table[["Date", "Post", "Clicks", "Impressions", "Click-through rate", "Source"]], column_config={
                "Click-through rate": st.column_config.NumberColumn(format="%.1f%%"),
                "Post": st.column_config.TextColumn(width="large"),
            })

    # Carousels vs videos
    if not f.shows("instagram"):
        return
    st.header("Instagram: static carousels vs videos")
    table = metrics.format_comparison(posts)
    st.write(metrics.format_takeaway(table))
    fig = go.Figure()
    names = list(metrics.FORMAT_METRICS.values())
    for _, row in table.iterrows():
        if row["Posts counted"] == 0:
            continue
        values = [row[f"Avg {n.lower()}"] for n in names]
        fig.add_trace(go.Bar(
            x=names, y=values, name=f"{row['Format']} ({row['Posts counted']} posts)",
            marker_color=config.FORMAT_COLORS[row["format"]],
            text=[None if v is None else f"{v:.1f}" for v in values], textposition="outside",
            hovertemplate="%{x}: %{y:.1f} per post<extra>" + row["Format"] + "</extra>",
        ))
    if fig.data:
        fig.update_layout(
            barmode="group", height=340, margin=dict(l=8, r=8, t=8, b=8),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
            yaxis=dict(title="Average per post", rangemode="tozero"),
        )
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    else:
        st.caption("No Instagram carousels or videos with metrics in this date range.")
    show_table(table.drop(columns=["format"]), column_config={
        c: st.column_config.NumberColumn(format="%.1f") for c in table.columns if c.startswith("Avg")
    })
    st.caption(
        "Feed posts only. Stories and single-image posts are left out. Averages can be moved a lot by one post "
        "that travels far, so check the post list below."
    )
    with st.expander("Posts behind this comparison"):
        ig = posts[(posts["channel"] == "instagram") & posts["format"].isin(["carousel", "video"])]
        show_table(ig[["date", "format", "likes", "comments", "shares", "saves", "views", "reach", "text", "source"]].sort_values("date", ascending=False))
