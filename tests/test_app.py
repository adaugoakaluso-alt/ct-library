"""Runs the app and each page headless, on sample data, and checks nothing errors."""

import pathlib

import pytest
from streamlit.testing.v1 import AppTest

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGES = ["general", "qualitative", "data_log", "update_data"]

PAGE_SCRIPT = """
import datetime
from ai_edge_dashboard import storage
from ai_edge_dashboard.components import Filters
from ai_edge_dashboard.views import {page}

{page}.render(
    storage.load_all(),
    Filters(datetime.date(2026, 8, 1), datetime.date(2026, 10, 31), ["newsletter", "instagram", "linkedin", "substack"]),
)
"""


@pytest.fixture
def sample_only(tmp_path, monkeypatch):
    # An empty data folder makes every table fall back to sample_data/.
    from ai_edge_dashboard import config
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)


def test_app_entry_point_runs(sample_only):
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    values = {m.label: m.value for m in at.metric}
    assert values["Subscribers · Newsletter"] != "-"
    assert values["Followers · Instagram"] != "-"


@pytest.mark.parametrize("page", PAGES)
def test_page_runs_on_sample_data(sample_only, page):
    at = AppTest.from_string(PAGE_SCRIPT.format(page=page), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]


def test_page_runs_with_a_channel_filter(sample_only):
    script = PAGE_SCRIPT.replace('["newsletter", "instagram", "linkedin", "substack"]', '["substack"]')
    for page in PAGES:
        at = AppTest.from_string(script.format(page=page), default_timeout=60).run()
        assert not at.exception, (page, [e.value for e in at.exception])
