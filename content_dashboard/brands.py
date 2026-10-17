"""Brands and their channels, read from brands/<brand-id>.toml.

Each brand file lists the channels that brand reports on. Example:

    name = "Travel Noire"
    title = "Travel Noire content reporting"   # optional

    [[channels]]
    id = "instagram"          # used in every CSV's channel column
    name = "Instagram"        # shown in the app
    platform = "instagram"    # one of platforms.PLATFORMS
    handle = "@travelnoire"   # optional
    color = "#C2417A"         # optional

    [[channels]]
    id = "tn-plus-instagram"
    name = "TN Plus Instagram"
    platform = "instagram"

A brand can have two channels on the same platform, as long as their ids differ.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from . import config
from .platforms import EMAIL, PLATFORMS, SOCIAL, Platform

BRANDS_DIR = config.REPO_ROOT / "brands"
EXAMPLE_BRAND = "example"

PALETTE = ["#2F6FDB", "#C2417A", "#0F8B8D", "#D9822B", "#6B4FBB", "#3C8D2F", "#B5487A", "#8A6D1F"]
_ID = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class BrandError(Exception):
    """A brand file is missing something or has a mistake. The message says what."""


@dataclass(frozen=True)
class Channel:
    id: str
    name: str
    platform: Platform
    color: str
    handle: str = ""

    @property
    def kind(self) -> str:
        return self.platform.kind

    @property
    def audience_metric(self) -> str:
        return self.platform.audience_metric


@dataclass(frozen=True)
class Brand:
    id: str
    name: str
    title: str
    channels: tuple[Channel, ...]

    @property
    def channel_ids(self) -> list[str]:
        return [c.id for c in self.channels]

    def channel(self, channel_id: str) -> Channel | None:
        return next((c for c in self.channels if c.id == channel_id), None)

    def channel_name(self, channel_id) -> str:
        c = self.channel(str(channel_id))
        return c.name if c else str(channel_id)

    def of_kind(self, kind: str) -> list[Channel]:
        return [c for c in self.channels if c.kind == kind]

    @property
    def social(self) -> list[Channel]:
        return self.of_kind(SOCIAL)

    @property
    def email(self) -> list[Channel]:
        return self.of_kind(EMAIL)

    def on_platform(self, platform_key: str) -> list[Channel]:
        return [c for c in self.channels if c.platform.key == platform_key]

    @property
    def data_dir(self) -> Path:
        return config.DATA_DIR / self.id


def load_brand(path: Path) -> Brand:
    brand_id = path.stem
    if not _ID.match(brand_id):
        raise BrandError(f"{path.name}: use lowercase letters, numbers and dashes in the file name.")
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise BrandError(f"{path.name} is not valid TOML: {exc}") from exc
    name = str(raw.get("name") or brand_id)
    channels, seen = [], set()
    for i, ch in enumerate(raw.get("channels") or []):
        cid = str(ch.get("id", "")).strip()
        if not _ID.match(cid):
            raise BrandError(f"{path.name}, channel {i + 1}: id '{cid}' must be lowercase letters, numbers and dashes.")
        if cid in seen:
            raise BrandError(f"{path.name}: channel id '{cid}' is used twice.")
        seen.add(cid)
        pkey = str(ch.get("platform", "")).strip().lower()
        if pkey not in PLATFORMS:
            raise BrandError(f"{path.name}, channel '{cid}': platform '{pkey}' is not one of: {', '.join(PLATFORMS)}.")
        channels.append(Channel(
            id=cid,
            name=str(ch.get("name") or PLATFORMS[pkey].label),
            platform=PLATFORMS[pkey],
            color=str(ch.get("color") or PALETTE[len(channels) % len(PALETTE)]),
            handle=str(ch.get("handle") or ""),
        ))
    if not channels:
        raise BrandError(f"{path.name} has no channels. Add at least one [[channels]] block.")
    title = config.env("APP_TITLE", brand=brand_id) or str(raw.get("title") or f"{name} content reporting")
    return Brand(id=brand_id, name=name, title=title, channels=tuple(channels))


def list_brands(directory: Path | None = None) -> dict[str, Brand]:
    directory = directory or BRANDS_DIR
    return {p.stem: load_brand(p) for p in sorted(directory.glob("*.toml"))}


def default_brand_id(brands: dict[str, Brand]) -> str:
    """BRAND from the environment if set, else the first real brand, else the example."""
    wanted = config.env("BRAND")
    if wanted and wanted in brands:
        return wanted
    real = [b for b in brands if b != EXAMPLE_BRAND]
    return real[0] if real else EXAMPLE_BRAND
