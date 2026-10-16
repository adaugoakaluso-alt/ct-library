import io

import pandas as pd

from ai_edge_dashboard import config, importers, schemas, storage


def linkedin_export(rows) -> io.BytesIO:
    """An .xlsx shaped like LinkedIn's content export: a note row, a header row, then posts."""
    header = ["Post title", "Post link", "Post type", "Posted by", "Created date", "Impressions", "Views",
              "Clicks", "Likes", "Comments", "Reposts", "Content Type"]
    note = ["Engagement metrics for individual posts."] + [None] * (len(header) - 1)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xl:
        pd.DataFrame([["Aggregated metrics"]]).to_excel(xl, sheet_name="Metrics", header=False, index=False)
        pd.DataFrame([note, header, *rows]).to_excel(xl, sheet_name="All posts", header=False, index=False)
    buf.seek(0)
    return buf


ROWS = [
    ["Anthropic just released Claude Opus 5.5. It is designed", "https://www.linkedin.com/feed/update/urn:li:activity:7509999999999999999",
     "Organic", "Someone", "09/23/2026", 65, None, 42, 1, 0, 1, None],
    ["Fathom sits in your calls and writes the follow-up for you.", "https://www.linkedin.com/feed/update/urn:li:activity:7515969000000000000",
     "Organic", "Someone", "10/14/2026", 11, 5, 1, 0, 0, 0, "Video"],
]


def test_read_linkedin_export_maps_columns_and_drops_names():
    df = importers.read_linkedin_content_export(linkedin_export(ROWS))
    assert len(df) == 2
    assert "Posted by" not in df.columns
    first = df.iloc[0]
    assert first["post_id"] == "li-7509999999999999999"
    assert first["date"] == "2026-09-23"
    assert first["clicks"] == 42 and first["shares"] == 1
    assert df.iloc[1]["format"] == "video" and first["format"] == "other"
    _, problems = storage.validate(df, schemas.get("social_posts"))
    assert problems == []


def test_read_rejects_other_files():
    buf = io.BytesIO()
    pd.DataFrame([[1]]).to_excel(buf, sheet_name="Sheet1", index=False)
    buf.seek(0)
    try:
        importers.read_linkedin_content_export(buf)
    except importers.ImportProblem as exc:
        assert "All posts" in str(exc)
    else:
        raise AssertionError("expected ImportProblem")


def test_merge_updates_buffer_posts_and_adds_new_ones():
    existing = storage.coerce(pd.DataFrame([
        # Buffer dates in UTC can land a day apart from LinkedIn's created date.
        {"post_id": "buf-1", "date": "2026-09-24", "channel": "linkedin", "format": "single image",
         "likes": "1", "impressions": "29", "text": "Anthropic just released Claude Opus 5.5. It is designed to be...", "source": "Buffer"},
        {"post_id": "buf-2", "date": "2026-09-24", "channel": "instagram", "format": "carousel", "likes": "5", "text": "Anthropic just released", "source": "Buffer"},
    ]), schemas.get("social_posts"))
    export = importers.read_linkedin_content_export(linkedin_export(ROWS))
    merged, updated, added = importers.merge_linkedin_export(existing, export)
    assert (updated, added) == (1, 1)
    row = merged.set_index("post_id").loc["buf-1"]
    assert row["clicks"] == 42 and row["impressions"] == 65 and row["format"] == "single image"
    assert "LinkedIn content export" in row["source"]
    assert merged.set_index("post_id").loc["buf-2", "likes"] == 5


def test_append_keeps_values_a_new_row_leaves_blank(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    ds = schemas.get("social_posts")
    first, _ = storage.validate(pd.DataFrame([{"post_id": "p1", "date": "2026-10-01", "channel": "linkedin", "format": "text",
                                               "likes": "1", "clicks": "9", "source": "LinkedIn export"}]), ds)
    storage.save("social_posts", first)
    # A later Buffer pull has fresh likes but no clicks.
    later, _ = storage.validate(pd.DataFrame([{"post_id": "p1", "date": "2026-10-01", "channel": "linkedin", "format": "text",
                                               "likes": "3", "source": "Buffer"}]), ds)
    storage.save("social_posts", later)
    row = storage.load("social_posts").df.set_index("post_id").loc["p1"]
    assert row["likes"] == 3 and row["clicks"] == 9
