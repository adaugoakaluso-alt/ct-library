import pandas as pd

from content_dashboard import config, schemas, storage


def test_validate_reports_missing_columns():
    _, problems = storage.validate(pd.DataFrame([{"date": "2026-10-01"}]), schemas.get("followers"))
    assert problems and "Missing columns" in problems[0]


def test_validate_catches_percent_entered_as_whole_number():
    df = pd.DataFrame([{"date": "2026-10-01", "subscribers": "500", "open_rate": "42", "click_rate": "0.03"}])
    _, problems = storage.validate(df, schemas.get("substack"))
    assert any("0.179" in p for p in problems)


def test_validate_catches_bad_dates_and_choices():
    df = pd.DataFrame([{"date": "last week", "channel": "tiktok", "followers": "10"}])
    _, problems = storage.validate(df, schemas.get("followers"))
    assert any("not a date" in p for p in problems)
    assert any("tiktok" in p for p in problems)


def test_save_appends_and_replaces_rows_with_the_same_key(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    ds = schemas.get("followers")
    first, _ = storage.validate(pd.DataFrame([
        {"date": "2026-10-01", "channel": "instagram", "followers": "100"},
        {"date": "2026-10-01", "channel": "linkedin", "followers": "50"},
    ]), ds)
    assert storage.save("followers", first) == 2
    update, _ = storage.validate(pd.DataFrame([
        {"date": "2026-10-01", "channel": "instagram", "followers": "105"},
        {"date": "2026-10-08", "channel": "instagram", "followers": "120"},
    ]), ds)
    assert storage.save("followers", update) == 3
    table = storage.load("followers")
    assert table.origin == storage.YOUR_DATA
    ig = table.df[(table.df["channel"] == "instagram") & (table.df["date"] == "2026-10-01")]
    assert ig["followers"].iloc[0] == 105


def test_load_falls_back_to_sample_data(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    for name in schemas.DATASETS:
        table = storage.load(name)
        assert table.origin == storage.SAMPLE, name
        assert not table.df.empty, name
        assert list(table.df.columns[: len(table.dataset.columns)]) == table.dataset.column_names


def test_sample_data_turns_off_once_any_real_table_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    (tmp_path / "followers.csv").write_text("date,channel,followers,source\n2026-10-01,instagram,100,Manual entry\n")
    tables = storage.load_all()
    assert tables["followers"].origin == storage.YOUR_DATA
    assert tables["manychat_clicks"].origin == storage.EMPTY
    assert tables["manychat_clicks"].df.empty


def test_append_keeps_the_source_of_values_it_keeps(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    ds = schemas.get("substack")
    first, _ = storage.validate(pd.DataFrame([{"date": "2026-09-08", "open_rate": "1.0", "source": "Posts list"}]), ds)
    storage.save("substack", first)
    later, _ = storage.validate(pd.DataFrame([{"date": "2026-09-08", "subscribers": "1", "source": "Growth export"}]), ds)
    storage.save("substack", later)
    row = storage.load("substack").df.set_index("date").iloc[0]
    assert row["subscribers"] == 1 and row["open_rate"] == 1.0
    assert "Growth export" in row["source"] and "Posts list" in row["source"]
