"""Buffer connector: response mapping and paging, with the network call mocked.

The node shapes below follow a real Buffer GraphQL response for this query,
with ids and text replaced.
"""

from datetime import date

import pandas as pd

from content_dashboard import brands, schemas, storage
from content_dashboard.connectors import buffer


def node(i, service, post_type, assets, metrics, text=""):
    return {"node": {
        "id": f"post-{i}", "channelId": "li" if service == "linkedin" else "ig", "channelService": service, "status": "sent", "via": "buffer", "text": text,
        "dueAt": "2026-10-14T23:00:00.000Z", "sentAt": "2026-10-14T23:01:17.153Z", "metricsUpdatedAt": "2026-10-16T14:07:07.422Z",
        "assets": [{"type": a} for a in assets], "metadata": {"type": post_type},
        "metrics": [{"type": k, "value": v} for k, v in metrics.items()],
    }}


PAGE_1 = {"pageInfo": {"hasNextPage": True, "endCursor": "abc"}, "edges": [
    node(1, "instagram", "post", ["image"] * 5, {"reactions": 3, "comments": 0, "shares": 1, "saves": 1, "views": 84, "reach": 50},
         'Comment "AI NEWS" and we will DM you the link'),
    node(2, "instagram", "story", ["image"], {"views": 5, "reach": 5, "comments": 0, "reactions": 0}),
]}
PAGE_2 = {"pageInfo": {"hasNextPage": False, "endCursor": None}, "edges": [
    node(3, "linkedin", "post", ["video"], {"reactions": 1, "comments": 0, "impressions": 3, "reach": 2, "shares": 0, "views": 3}),
    node(4, "instagram", "reel", ["video"], {"reactions": 10, "comments": 4, "shares": 2, "saves": 2, "views": 1664, "reach": 1178}),
]}


def test_post_format():
    assert buffer.post_format(PAGE_1["edges"][0]["node"]) == "carousel"
    assert buffer.post_format(PAGE_1["edges"][1]["node"]) == "story"
    assert buffer.post_format(PAGE_2["edges"][0]["node"]) == "video"
    assert buffer.post_format(PAGE_2["edges"][1]["node"]) == "video"
    assert buffer.post_format({"assets": [], "metadata": {"type": "post"}}) == "text"


def test_fetch_pages_and_fits_the_schema(monkeypatch, example):
    for k, v in {"BUFFER_API_KEY": "test-key", "BUFFER_ORGANIZATION_ID": "org", "BUFFER_CHANNEL_IDS": "ig,li"}.items():
        monkeypatch.setenv(k, v)
    calls = []

    class Resp:
        status_code = 200

        def __init__(self, page):
            self.page = page

        def json(self):
            return {"data": {"posts": self.page}}

    def fake_post(url, json, headers, timeout):
        calls.append(json["variables"])
        assert headers["Authorization"] == "Bearer test-key"
        return Resp(PAGE_1 if len(calls) == 1 else PAGE_2)

    monkeypatch.setattr(buffer.requests, "post", fake_post)
    conn = buffer.BufferConnector()
    assert conn.is_configured(example)
    rows = conn.fetch(date(2026, 10, 1), date(2026, 10, 16), example)
    assert len(calls) == 2 and calls[1]["after"] == "abc"
    assert calls[0]["input"]["filter"]["channelIds"] == ["ig", "li"]
    assert calls[0]["input"]["filter"]["dueAt"]["start"].startswith("2026-10-01T00:00:00")
    clean, problems = storage.validate(rows, schemas.get("posts"), example)
    assert problems == []
    first = clean.set_index("post_id").loc["post-1"]
    assert first["likes"] == 3 and first["saves"] == 1 and first["format"] == "carousel"
    assert first["date"] == pd.Timestamp("2026-10-14")
    assert set(clean["channel"]) == {"instagram", "linkedin"}


def test_channel_ids_can_name_the_brand_channel(monkeypatch, make_brand):
    b = make_brand("tn", '[[channels]]\nid = "instagram"\nplatform = "instagram"\n[[channels]]\nid = "tn-plus"\nplatform = "instagram"')
    monkeypatch.setenv("BUFFER_CHANNEL_IDS", "ig1, ig2:tn-plus")
    assert buffer.BufferConnector.channel_map(b) == {"ig1": None, "ig2": "tn-plus"}
    monkeypatch.setenv("BUFFER_CHANNEL_IDS", "ig2:nope")
    try:
        buffer.BufferConnector.channel_map(b)
    except buffer.ConnectorError as exc:
        assert "brands/tn.toml" in str(exc)
    else:
        raise AssertionError("expected ConnectorError")


def test_a_brand_setting_wins_over_the_shared_one(monkeypatch, example):
    from content_dashboard import config
    monkeypatch.setenv("BUFFER_API_KEY", "shared")
    monkeypatch.setenv("TRAVEL_NOIRE_BUFFER_API_KEY", "tn-only")
    assert config.env("BUFFER_API_KEY", brand="travel-noire") == "tn-only"
    assert config.env("BUFFER_API_KEY", brand="ai-edge") == "shared"
    monkeypatch.delenv("BUFFER_API_KEY")
    assert buffer.BufferConnector().missing_settings(example)[0] == "BUFFER_API_KEY"
