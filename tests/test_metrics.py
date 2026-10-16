from datetime import date

import pandas as pd

from ai_edge_dashboard import metrics, schemas, storage


def posts(rows):
    return storage.coerce(pd.DataFrame(rows), schemas.get("social_posts"))


def test_extract_keyword_variants():
    assert metrics.extract_keyword('Comment "AI NEWS" and we will DM you') == "AI NEWS"
    assert metrics.extract_keyword("Comment “REGISTER” to save your seat") == "REGISTER"
    assert metrics.extract_keyword("Comment 'AINEWS' to get it") == "AINEWS"
    assert metrics.extract_keyword("Comment COPILOT for the guide") == "COPILOT"
    assert metrics.extract_keyword("Let us know in the comments below") is None
    assert metrics.extract_keyword(None) is None


def test_keyword_table_merges_spellings_and_manychat_clicks():
    p = posts([
        {"post_id": "1", "date": "2026-10-01", "channel": "instagram", "format": "video", "text": 'Comment "AI NEWS"'},
        {"post_id": "2", "date": "2026-10-03", "channel": "instagram", "format": "carousel", "text": "Comment 'AINEWS' now"},
        {"post_id": "3", "date": "2026-10-04", "channel": "linkedin", "format": "text", "text": 'Comment "AI NEWS"'},
    ])
    mc = storage.coerce(pd.DataFrame([{"date": "2026-10-05", "keyword": "ai news", "clicks": "7"}]), schemas.get("manychat_clicks"))
    table = metrics.keyword_table(p, mc)
    assert len(table) == 1
    assert table.iloc[0]["Posts"] == 2
    assert table.iloc[0]["ManyChat clicks"] == 7


def test_format_comparison_averages_and_skips_rows_without_metrics():
    p = posts([
        {"post_id": "1", "date": "2026-10-01", "channel": "instagram", "format": "carousel", "likes": "4", "comments": "2", "shares": "0", "saves": "2"},
        {"post_id": "2", "date": "2026-10-02", "channel": "instagram", "format": "carousel", "likes": "6", "comments": "0", "shares": "0", "saves": "0"},
        {"post_id": "3", "date": "2026-10-02", "channel": "instagram", "format": "carousel"},
        {"post_id": "4", "date": "2026-10-03", "channel": "instagram", "format": "video", "likes": "10", "comments": "1", "shares": "3", "saves": "1"},
        {"post_id": "5", "date": "2026-10-03", "channel": "instagram", "format": "story", "likes": "99"},
    ])
    t = metrics.format_comparison(p).set_index("format")
    assert t.loc["carousel", "Posts counted"] == 2
    assert t.loc["carousel", "Avg likes"] == 5
    assert t.loc["video", "Avg shares"] == 3
    assert "Videos average more likes" in metrics.format_takeaway(t.reset_index())


def test_latest_with_change_uses_row_before_even_outside_range():
    df = storage.coerce(pd.DataFrame([
        {"date": "2026-09-01", "channel": "instagram", "followers": "100"},
        {"date": "2026-10-01", "channel": "instagram", "followers": "130"},
        {"date": "2026-10-08", "channel": "instagram", "followers": "150"},
    ]), schemas.get("followers"))
    k = metrics.latest_with_change(df, "date", "followers", date(2026, 10, 1), date(2026, 10, 31))
    assert k.value == 150
    assert k.change == 20
    assert k.range_change == 20
    none = metrics.latest_with_change(df, "date", "followers", date(2026, 11, 1), date(2026, 11, 30))
    assert none.value is None


def test_cta_ranking_orders_by_clicks_across_channels():
    links = storage.coerce(pd.DataFrame([
        {"link_id": "a", "send_date": "2026-10-05", "link_text": "Gemini", "cta_wording": "Keep reading", "section": "Story", "unique_clicks": "6", "source": "Iterable"},
    ]), schemas.get("newsletter_links"))
    mc = storage.coerce(pd.DataFrame([
        {"date": "2026-10-05", "keyword": "AI NEWS", "clicks": "9", "source": "ManyChat"},
    ]), schemas.get("manychat_clicks"))
    r = metrics.cta_ranking(links, mc)
    assert list(r["Rank"]) == [1, 2]
    assert r.iloc[0]["Channel"] == "instagram"
    assert r.iloc[1]["CTA"] == 'Gemini ("Keep reading")'
