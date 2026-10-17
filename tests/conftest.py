import pytest

from content_dashboard import brands, config


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """An empty data folder, so nothing in the real data/ is read or written."""
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def example():
    return brands.load_brand(brands.BRANDS_DIR / "example.toml")


@pytest.fixture
def make_brand(tmp_path):
    """Write a brand file and load it: make_brand("x", 'name = "X"\\n[[channels]]...')."""
    def make(brand_id: str, toml: str) -> brands.Brand:
        path = tmp_path / "brands" / f"{brand_id}.toml"
        path.parent.mkdir(exist_ok=True)
        path.write_text(toml)
        return brands.load_brand(path)
    return make
