"""Runs the app and each page headless and checks nothing errors."""

import pathlib

import pytest
from streamlit.testing.v1 import AppTest

from content_dashboard import brands

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGES = ["general", "qualitative", "data_log", "update_data"]
BRAND_FILES = [*sorted(brands.BRANDS_DIR.glob("*.toml")), *sorted((brands.BRANDS_DIR / "starters").glob("*.toml"))]

PAGE_SCRIPT = """
import datetime, pathlib
from content_dashboard import brands, config, storage
from content_dashboard.components import Filters
from content_dashboard.views import {page}

config.DATA_DIR = pathlib.Path({data_dir!r})
brand = brands.load_brand(pathlib.Path({brand_file!r}))
channels = {channels!r} or brand.channel_ids
{page}.render(storage.load_all(brand), Filters(brand, datetime.date(2026, 8, 1), datetime.date(2026, 10, 31), channels))
"""


def run_page(page, brand_file, data_dir, channels=None):
    script = PAGE_SCRIPT.format(page=page, brand_file=str(brand_file), data_dir=str(data_dir), channels=channels)
    at = AppTest.from_string(script, default_timeout=60).run()
    assert not at.exception, (page, brand_file.name, [e.value for e in at.exception])
    return at


def test_app_entry_point_runs_on_the_example_brand(data_dir, monkeypatch):
    monkeypatch.setenv("BRAND", "example")
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    values = {m.label: m.value for m in at.metric}
    for label in ["Subscribers · Newsletter", "Followers · Instagram", "Followers · TikTok"]:
        assert values[label] != "-", label


@pytest.mark.parametrize("page", PAGES)
def test_page_runs_on_sample_data(data_dir, page):
    run_page(page, brands.BRANDS_DIR / "example.toml", data_dir)


@pytest.mark.parametrize("page", PAGES)
def test_page_runs_with_one_channel_selected(data_dir, page):
    run_page(page, brands.BRANDS_DIR / "example.toml", data_dir, ["substack"])


@pytest.mark.parametrize("brand_file", BRAND_FILES, ids=lambda p: p.stem)
def test_every_brand_runs_with_no_data(tmp_path, brand_file):
    for page in PAGES:
        run_page(page, brand_file, tmp_path / "empty")
