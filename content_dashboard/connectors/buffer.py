"""Social posts from Buffer's GraphQL API, for any platform Buffer supports.

Settings (environment variables):
  BUFFER_API_KEY          Personal API key from https://publish.buffer.com/settings/api
  BUFFER_ORGANIZATION_ID  The Buffer organization that holds the channels
  BUFFER_CHANNEL_IDS      Comma-separated Buffer channel ids. Write id:channel to send a
                          Buffer channel to a channel in your brand file, such as
                          6a4f...:tn-plus-instagram. A bare id goes to the brand's first
                          channel on that platform.

Buffer refreshes post metrics about once a day, so a pull reflects the
numbers as of Buffer's last refresh.
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone

import pandas as pd
import requests

from .. import config
from ..brands import Brand
from .base import Connector, ConnectorError

API_URL = "https://api.buffer.com"
PAGE_SIZE = 100
MAX_PAGES = 20

POSTS_QUERY = """
query AiEdgePosts($input: PostsInput!, $first: Int, $after: String) {
  posts(input: $input, first: $first, after: $after) {
    pageInfo { hasNextPage endCursor }
    edges { node {
      id channelId channelService status via text dueAt sentAt metricsUpdatedAt
      assets { type }
      metadata {
        ... on InstagramPostMetadata { type }
        ... on LinkedInPostMetadata { type }
      }
      metrics { type value }
    } }
  }
}
"""

# Buffer metric type -> column in the posts table
METRIC_COLUMNS = {
    "reactions": "likes",
    "likes": "likes",
    "comments": "comments",
    "shares": "shares",
    "saves": "saves",
    "views": "views",
    "reach": "reach",
    "impressions": "impressions",
    "clicks": "clicks",
}


def post_format(node: dict) -> str:
    """carousel, video, single image, text or story, from Buffer's post type and attachments."""
    post_type = ((node.get("metadata") or {}).get("type") or "").lower()
    asset_types = [a.get("type") for a in node.get("assets") or []]
    if post_type == "story":
        return "story"
    if post_type in ("reel", "short") or "video" in asset_types:
        return "video"
    if post_type == "carousel" or len(asset_types) > 1:
        return "carousel"
    if len(asset_types) == 1:
        return "single image"
    return "text"


def node_to_row(node: dict, pulled_on: str, channel: str) -> dict:
    row = {
        "post_id": node["id"],
        "date": (node.get("sentAt") or node.get("dueAt") or "")[:10],
        "channel": channel,
        "format": post_format(node),
        "text": node.get("text") or "",
        "source": f"Buffer API, pulled {pulled_on}",
    }
    for m in node.get("metrics") or []:
        col = METRIC_COLUMNS.get(m.get("type"))
        if col and row.get(col) is None:
            row[col] = m.get("value")
    return row


class BufferConnector(Connector):
    name = "Buffer"
    dataset = "posts"
    required_env = ("BUFFER_API_KEY", "BUFFER_ORGANIZATION_ID", "BUFFER_CHANNEL_IDS")
    description = "Pulls every sent post on your Buffer channels with likes, comments, shares, saves, views and reach."

    def _post(self, variables: dict, brand: Brand) -> dict:
        try:
            resp = requests.post(
                API_URL,
                json={"query": POSTS_QUERY, "variables": variables},
                headers={"Authorization": f"Bearer {config.env('BUFFER_API_KEY', brand=brand.id)}"},
                timeout=60,
            )
        except requests.RequestException as exc:
            raise ConnectorError(f"Could not reach Buffer: {exc}") from exc
        if resp.status_code in (401, 403):
            raise ConnectorError("Buffer refused the API key. Check BUFFER_API_KEY.")
        if resp.status_code >= 400:
            raise ConnectorError(f"Buffer returned an error ({resp.status_code}): {resp.text[:300]}")
        body = resp.json()
        if body.get("errors"):
            raise ConnectorError("Buffer returned an error: " + "; ".join(e.get("message", "") for e in body["errors"]))
        return body["data"]["posts"]

    @staticmethod
    def channel_map(brand: Brand) -> dict[str, str | None]:
        """Buffer channel id -> brand channel id (None: decide by the post's platform)."""
        out = {}
        for item in (config.env("BUFFER_CHANNEL_IDS", "", brand=brand.id) or "").split(","):
            item = item.strip()
            if not item:
                continue
            buffer_id, _, channel = item.partition(":")
            if channel and channel not in brand.channel_ids:
                raise ConnectorError(f"BUFFER_CHANNEL_IDS sends {buffer_id} to '{channel}', which is not a channel in brands/{brand.id}.toml.")
            out[buffer_id] = channel or None
        return out

    @staticmethod
    def channel_for_service(brand: Brand, service: str) -> str | None:
        for c in brand.channels:
            if c.platform.buffer_service == service:
                return c.id
        return None

    def fetch(self, start: date, end: date, brand: Brand) -> pd.DataFrame:
        mapping = self.channel_map(brand)
        channel_ids = list(mapping)
        start_at = datetime.combine(start, time.min, tzinfo=timezone.utc).isoformat()
        end_at = datetime.combine(end, time.max.replace(microsecond=0), tzinfo=timezone.utc).isoformat()
        variables = {
            "first": PAGE_SIZE,
            "input": {
                "organizationId": config.env("BUFFER_ORGANIZATION_ID", brand=brand.id),
                "filter": {"channelIds": channel_ids, "status": ["sent"], "dueAt": {"start": start_at, "end": end_at}},
                "sort": [{"field": "dueAt", "direction": "desc"}],
            },
        }
        pulled_on = date.today().isoformat()
        rows: list[dict] = []
        for _ in range(MAX_PAGES):
            page = self._post(variables, brand)
            for e in page.get("edges") or []:
                node = e["node"]
                channel = mapping.get(node.get("channelId")) or self.channel_for_service(brand, node.get("channelService"))
                if channel:
                    rows.append(node_to_row(node, pulled_on, channel))
            info = page.get("pageInfo") or {}
            if not info.get("hasNextPage"):
                break
            variables["after"] = info.get("endCursor")
        return pd.DataFrame(rows)
