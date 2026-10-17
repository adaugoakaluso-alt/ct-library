"""Paths, channel names and settings.

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


# Real data you enter or upload. Ignored by git.
DATA_DIR = _repo_path(os.getenv("AI_EDGE_DATA_DIR", "data"))

# Fake sample data, committed so a fresh clone runs straight away.
SAMPLE_DIR = REPO_ROOT / "sample_data"

# Channel ids used in every CSV, and the names shown in the app.
CHANNELS = {
    "newsletter": "Newsletter",
    "instagram": "Instagram",
    "linkedin": "LinkedIn",
    "substack": "Substack",
}

# One color per channel, used by every chart.
CHANNEL_COLORS = {
    "newsletter": "#2F6FDB",
    "instagram": "#C2417A",
    "linkedin": "#0F8B8D",
    "substack": "#D9822B",
}

FORMAT_COLORS = {
    "carousel": "#2F6FDB",
    "video": "#C2417A",
}


def env(name: str, default: str | None = None) -> str | None:
    """Read a setting from the environment. Empty strings count as unset."""
    value = os.getenv(name, default)
    if value is None or str(value).strip() == "":
        return default
    return str(value).strip()


# Shown in the browser tab and the sidebar. Each team sets its own in .env.
APP_TITLE = env("APP_TITLE", "Content reporting")
