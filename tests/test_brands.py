"""Brand files: every one in brands/ and brands/starters/ loads, and mistakes get plain messages."""

import pytest

from content_dashboard import brands
from content_dashboard.platforms import PLATFORMS


@pytest.mark.parametrize("folder", [brands.BRANDS_DIR, brands.BRANDS_DIR / "starters"])
def test_every_shipped_brand_file_loads(folder):
    found = brands.list_brands(folder)
    assert found
    for brand in found.values():
        assert brand.channels


def test_channels_get_kinds_metrics_and_default_colors(make_brand):
    b = make_brand("travel", """
name = "Travel"
[[channels]]
id = "instagram"
platform = "instagram"
[[channels]]
id = "tn-plus-instagram"
name = "TN Plus Instagram"
platform = "instagram"
[[channels]]
id = "newsletter"
platform = "newsletter"
""")
    assert b.title == "Travel content reporting"
    assert [c.name for c in b.channels] == ["Instagram", "TN Plus Instagram", "Email newsletter"]
    assert len(b.on_platform("instagram")) == 2
    assert [c.audience_metric for c in b.channels] == ["followers", "followers", "subscribers"]
    assert len({c.color for c in b.channels}) == 3
    assert b.data_dir.name == "travel"


@pytest.mark.parametrize("body, message", [
    ('name = "X"', "no channels"),
    ('[[channels]]\nid = "a"\nplatform = "myspace"', "not one of"),
    ('[[channels]]\nid = "a"\nplatform = "x"\n[[channels]]\nid = "a"\nplatform = "tiktok"', "used twice"),
    ('[[channels]]\nid = "My Channel"\nplatform = "x"', "lowercase"),
    ('name = ', "not valid TOML"),
])
def test_brand_file_mistakes(make_brand, body, message):
    with pytest.raises(brands.BrandError, match=message):
        make_brand("x", body)


def test_default_brand_prefers_env_then_a_real_brand(monkeypatch, example):
    monkeypatch.delenv("BRAND", raising=False)
    assert brands.default_brand_id({"example": example}) == "example"
    assert brands.default_brand_id({"example": example, "ai-edge": example}) == "ai-edge"
    monkeypatch.setenv("BRAND", "example")
    assert brands.default_brand_id({"example": example, "ai-edge": example}) == "example"


def test_every_platform_has_a_known_kind():
    assert {p.kind for p in PLATFORMS.values()} <= {"social", "email", "other"}
