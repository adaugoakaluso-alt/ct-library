"""Page 2: Qualitative reporting. Best-performing CTAs ranked, comment keywords,
posts by clicks, and engagement by post format for any social channel."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from .. import metrics
from ..components import FORMAT_COLORS, Filters, origin_note, show_table
from ..storage import Table


def render(tables: dict[str, Table], f: Filters) -> None:
    brand = f.brand
    cta = metrics.in_range(tables["cta_clicks"].df, "date", f.start, f.end)
    cta = cta[cta["channel"].isin(f.channels)]
    posts = metrics.in_range(tables["posts"].df, "date", f.start, f.end)
    posts = posts[posts["channel"].isin(f.channels)]

    st.title("Qualitative reporting")
    st.caption(f"{f.start:%b %-d, %Y} to {f.end:%b %-d, %Y}.")
    origin_note(tables["cta_clicks"], tables["posts"])

    # Best-performing CTAs
    st.header("Best-performing CTAs")
    st.caption("Ranked by clicks. The Measure column says what each count is, such as unique link clicks or DM link clicks.")
    ranking = metrics.cta_ranking(cta, brand.channel_name)
    if ranking.empty:
        st.caption("No CTAs with clicks in this date range and channel selection.")
    else:
        show_table(ranking, column_config={"Clicks": st.column_config.NumberColumn(format="%d")})

    social = [c for c in f.visible(brand.social) if (posts["channel"] == c.id).any()]

    # Comment keywords
    with_keywords = [c for c in social if posts[posts["channel"] == c.id]["text"].map(metrics.extract_keyword).notna().any()]
    if with_keywords:
        st.subheader("Comment keywords")
        st.caption('Keywords found in captions, such as Comment "AI NEWS", with DM automation clicks for each keyword once they are logged.')
        ch = st.selectbox("Channel", with_keywords, format_func=lambda c: c.name, key="kw-channel") if len(with_keywords) > 1 else with_keywords[0]
        kw = metrics.keyword_table(posts[posts["channel"] == ch.id], cta[cta["channel"] == ch.id])
        show_table(kw, column_config={"Clicks": st.column_config.NumberColumn(format="%d")})

    # Posts by clicks
    clicked = metrics.posts_by_clicks(posts)
    if not clicked.empty:
        st.subheader("Posts by clicks")
        st.caption("Clicks as each platform counts them. LinkedIn, for example, counts any click on a post, including "
                   "opening it, so these are not the same measure as link clicks.")
        table = clicked.assign(Channel=clicked["channel"].map(brand.channel_name)).rename(columns={
            "date": "Date", "text": "Post", "clicks": "Clicks", "impressions": "Impressions",
            "click_rate": "Click-through rate", "source": "Source"})
        show_table(table[["Date", "Channel", "Post", "Clicks", "Impressions", "Click-through rate", "Source"]], column_config={
            "Click-through rate": st.column_config.NumberColumn(format="%.1f%%"),
            "Post": st.column_config.TextColumn(width="large"),
        })

    # Engagement by format
    if not social:
        return
    st.header("Engagement by post format")
    c1, c2 = st.columns([1, 2])
    ch = c1.selectbox("Channel", social, format_func=lambda c: c.name, key="fmt-channel")
    ch_posts = posts[(posts["channel"] == ch.id) & (posts["format"] != "story")]
    present = [x for x in ch_posts.dropna(subset=["likes"])["format"].value_counts().index]
    default = [x for x in ("carousel", "video") if x in present] or present[:2]
    formats = c2.multiselect("Formats to compare", present, default=default, key="fmt-formats")
    if not formats:
        st.caption("Pick at least one format.")
        return
    table = metrics.format_comparison(ch_posts, formats)
    st.write(metrics.format_takeaway(table))
    fig = go.Figure()
    names = list(metrics.ENGAGEMENT.values())
    for i, (_, row) in enumerate(table.iterrows()):
        if row["Posts counted"] == 0:
            continue
        values = [row[f"Avg {n.lower()}"] for n in names]
        fig.add_trace(go.Bar(
            x=names, y=values, name=f"{row['Format']} ({row['Posts counted']} posts)",
            marker_color=FORMAT_COLORS[i % len(FORMAT_COLORS)],
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
    show_table(table.drop(columns=["format"]), column_config={
        c: st.column_config.NumberColumn(format="%.1f") for c in table.columns if c.startswith("Avg")
    })
    st.caption("Stories and posts with no metrics are left out. Averages can be moved a lot by one post that travels far, "
               "so check the posts below.")
    with st.expander("Posts behind this comparison"):
        show_table(ch_posts[ch_posts["format"].isin(formats)][
            ["date", "format", "likes", "comments", "shares", "saves", "views", "reach", "text", "source"]
        ].sort_values("date", ascending=False))
