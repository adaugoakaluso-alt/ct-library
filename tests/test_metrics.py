from datetime import date

import pandas as pd

from content_dashboard import metrics, schemas, storage


def frame(name, rows):
    return storage.coerce(pd.DataFrame(rows), schemas.get(name))


def test_extract_keyword_variants():
    assert metrics.extract_keyword('Comment "AI NEWS" and we will DM you') == "AI NEWS"
    assert metrics.extract_keyword("Comment “REGISTER” to save your seat") == "REGISTER"
    assert metrics.extract_keyword("Comment 'AINEWS' to get it") == "AINEWS"
    assert metrics.extract_keyword("Comment COPILOT for the guide") == "COPILOT"
    assert metrics.extract_keyword("Let us know in the comments below") is None
    assert metrics.extract_keyword(None) is None


def test_keyword_table_merges_spellings_and_dm_clicks():
    p = frame("posts", [
        {"post_id": "1", "date": "2026-10-01", "channel": "instagram", "format": "video", "text": 'Comment "AI NEWS"'},
        {"post_id": "2", "date": "2026-10-03", "channel": "instagram", "format": "carousel", "text": "Comment 'AINEWS' now"},
    ])
    clicks = frame("cta_clicks", [{"cta_id": "m1", "date": "2026-10-05", "channel": "instagram", "cta": "x", "keyword": "ai news", "clicks": "7"}])
    table = metrics.keyword_table(p, clicks)
    assert len(table) == 1
    assert table.iloc[0]["Posts"] == 2
    assert table.iloc[0]["Clicks"] == 7


def test_format_comparison_averages_and_skips_rows_without_metrics():
    p = frame("posts", [
        {"post_id": "1", "date": "2026-10-01", "channel": "tiktok", "format": "carousel", "likes": "4", "comments": "2", "shares": "0", "saves": "2"},
        {"post_id": "2", "date": "2026-10-02", "channel": "tiktok", "format": "carousel", "likes": "6", "comments": "0", "shares": "0", "saves": "0"},
        {"post_id": "3", "date": "2026-10-02", "channel": "tiktok", "format": "carousel"},
        {"post_id": "4", "date": "2026-10-03", "channel": "tiktok", "format": "video", "likes": "10", "comments": "1", "shares": "3", "saves": "1"},
    ])
    t = metrics.format_comparison(p, ["carousel", "video"]).set_index("format")
    assert t.loc["carousel", "Posts counted"] == 2
    assert t.loc["carousel", "Avg likes"] == 5
    assert t.loc["video", "Avg shares"] == 3
    assert "Video posts average the most likes" in metrics.format_takeaway(t.reset_index())


def test_audience_kpi_uses_the_row_before_the_range_and_one_channel_only():
    a = frame("audience", [
        {"date": "2026-09-01", "channel": "instagram", "metric": "followers", "value": "100"},
        {"date": "2026-10-01", "channel": "instagram", "metric": "followers", "value": "130"},
        {"date": "2026-10-08", "channel": "instagram", "metric": "followers", "value": "150"},
        {"date": "2026-10-09", "channel": "tn-plus-instagram", "metric": "followers", "value": "9000"},
    ])
    k = metrics.audience_kpi(a, "instagram", "followers", date(2026, 10, 1), date(2026, 10, 31))
    assert k.value == 150
    assert k.change == 20
    assert k.range_change == 20
    assert metrics.audience_kpi(a, "instagram", "followers", date(2026, 11, 1), date(2026, 11, 30)).value is None


def test_email_rate_kpi_reads_one_channel():
    s = frame("email_stats", [
        {"channel": "newsletter", "period_id": "sep", "label": "September", "start_date": "2026-09-01", "end_date": "2026-09-30", "open_rate": "0.11"},
        {"channel": "newsletter", "period_id": "oct", "label": "October", "start_date": "2026-10-01", "end_date": "2026-10-31", "open_rate": "0.18"},
        {"channel": "substack", "period_id": "p", "label": "Post", "start_date": "2026-10-05", "end_date": "2026-10-05", "open_rate": "0.6"},
    ])
    k = metrics.email_rate_kpi(s, "newsletter", "open_rate", date(2026, 9, 1), date(2026, 10, 31))
    assert round(k.value, 2) == 0.18


def test_cta_ranking_orders_by_clicks_across_channels():
    c = frame("cta_clicks", [
        {"cta_id": "a", "date": "2026-10-05", "channel": "newsletter", "cta": "Keep reading", "clicks": "6", "source": "Iterable"},
        {"cta_id": "b", "date": "2026-10-05", "channel": "instagram", "cta": 'Comment "AI NEWS"', "clicks": "9", "source": "ManyChat"},
    ])
    r = metrics.cta_ranking(c, {"newsletter": "Newsletter", "instagram": "Instagram"}.get)
    assert list(r["Rank"]) == [1, 2]
    assert list(r["Channel"]) == ["Instagram", "Newsletter"]
