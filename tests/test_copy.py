"""House style: no em dashes anywhere in interface text."""

import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_no_em_dashes_in_app_code():
    files = [ROOT / "app.py", *sorted((ROOT / "ai_edge_dashboard").rglob("*.py"))]
    offenders = [str(f.relative_to(ROOT)) for f in files if "—" in f.read_text(encoding="utf-8")]
    assert not offenders, f"Em dashes found in: {offenders}"
