"""Paths and settings.

Brands and their channels are not set here; they live in brands/<brand-id>.toml.

Everything resolves relative to the repo root, so the app runs the same on a
laptop, in CI and on Streamlit Community Cloud. Credentials only ever come
from environment variables (a local .env file, or Streamlit secrets).
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent

# A local .env file is optional. On Streamlit Community Cloud, root-level
# secrets are exposed as environment variables, so os.getenv covers both.
load_dotenv(REPO_ROOT / ".env")


def _repo_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


# Real data you enter or upload, one folder per brand. Ignored by git.
DATA_DIR = _repo_path(os.getenv("DATA_DIR") or "data")

# Made-up data for the example brand, committed so a fresh clone runs straight away.
SAMPLE_DIR = REPO_ROOT / "sample_data"


def brand_prefix(brand_id: str) -> str:
    """Prefix for a brand's own settings: travel-noire -> TRAVEL_NOIRE_."""
    return brand_id.upper().replace("-", "_") + "_"


def env(name: str, default: str | None = None, brand: str | None = None) -> str | None:
    """Read a setting from the environment. Empty strings count as unset.

    With a brand id, a brand's own setting wins: TRAVEL_NOIRE_BUFFER_API_KEY is
    read before BUFFER_API_KEY. That lets one copy of the app hold several
    brands that each pull from their own accounts.
    """
    names = ([brand_prefix(brand) + name] if brand else []) + [name]
    for n in names:
        value = os.getenv(n)
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return default


