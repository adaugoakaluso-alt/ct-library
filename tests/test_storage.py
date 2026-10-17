import pandas as pd

from content_dashboard import schemas, storage


def test_validate_reports_missing_columns(example):
    _, problems = storage.validate(pd.DataFrame([{"date": "2026-10-01"}]), schemas.get("audience"), example)
    assert problems and "Missing columns" in problems[0]


def test_validate_catches_percent_entered_as_whole_number(example):
    df = pd.DataFrame([{"channel": "substack", "period_id": "p1", "label": "Post", "start_date": "2026-10-01",
                        "end_date": "2026-10-01", "open_rate": "42"}])
    _, problems = storage.validate(df, schemas.get("email_stats"), example)
    assert any("0.179" in p for p in problems)


def test_validate_catches_bad_dates_choices_and_unknown_channels(example):
    df = pd.DataFrame([{"date": "last week", "channel": "myspace", "metric": "fans", "value": "10"}])
    _, problems = storage.validate(df, schemas.get("audience"), example)
    assert any("not a date" in p for p in problems)
    assert any("'fans' is not one of" in p for p in problems)
    assert any("myspace" in p and "brands/example.toml" in p for p in problems)


def test_save_appends_and_replaces_rows_with_the_same_key(data_dir, example):
    ds = schemas.get("audience")
    first, _ = storage.validate(pd.DataFrame([
        {"date": "2026-10-01", "channel": "instagram", "metric": "followers", "value": "100"},
        {"date": "2026-10-01", "channel": "tiktok", "metric": "followers", "value": "50"},
    ]), ds, example)
    assert storage.save("audience", first, example) == 2
    update, _ = storage.validate(pd.DataFrame([
        {"date": "2026-10-01", "channel": "instagram", "metric": "followers", "value": "105"},
        {"date": "2026-10-08", "channel": "instagram", "metric": "followers", "value": "120"},
    ]), ds, example)
    assert storage.save("audience", update, example) == 3
    assert (data_dir / "example" / "audience.csv").exists()
    table = storage.load("audience", example)
    assert table.origin == storage.YOUR_DATA
    ig = table.df[(table.df["channel"] == "instagram") & (table.df["date"] == "2026-10-01")]
    assert ig["value"].iloc[0] == 105


def test_example_brand_shows_sample_data_that_fits_its_channels(data_dir, example):
    for name, table in storage.load_all(example).items():
        assert table.origin == storage.SAMPLE, name
        assert not table.df.empty, name
        assert list(table.df.columns[: len(table.dataset.columns)]) == table.dataset.column_names
        _, problems = storage.validate(storage.to_csv_frame(table.df, table.dataset).astype("string"), table.dataset, example)
        assert problems == [], (name, problems)


def test_sample_data_turns_off_once_any_real_table_exists(data_dir, example):
    (data_dir / "example").mkdir()
    (data_dir / "example" / "audience.csv").write_text("date,channel,metric,value,source\n2026-10-01,instagram,followers,100,Manual entry\n")
    tables = storage.load_all(example)
    assert tables["audience"].origin == storage.YOUR_DATA
    assert tables["posts"].origin == storage.EMPTY and tables["posts"].df.empty


def test_real_brands_never_show_sample_data(data_dir, make_brand):
    b = make_brand("travel", '[[channels]]\nid = "instagram"\nplatform = "instagram"')
    assert all(t.origin == storage.EMPTY for t in storage.load_all(b).values())


def test_append_keeps_the_source_of_values_it_keeps(data_dir, example):
    ds = schemas.get("email_stats")
    base = {"channel": "substack", "period_id": "p1", "label": "9/8 post", "start_date": "2026-09-08", "end_date": "2026-09-08"}
    first, _ = storage.validate(pd.DataFrame([{**base, "open_rate": "1.0", "source": "Posts list"}]), ds, example)
    storage.save("email_stats", first, example)
    later, _ = storage.validate(pd.DataFrame([{**base, "delivered": "1", "source": "Growth export"}]), ds, example)
    storage.save("email_stats", later, example)
    row = storage.load("email_stats", example).df.iloc[0]
    assert row["delivered"] == 1 and row["open_rate"] == 1.0
    assert "Growth export" in row["source"] and "Posts list" in row["source"]
