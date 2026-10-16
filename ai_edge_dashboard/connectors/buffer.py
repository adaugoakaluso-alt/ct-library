"""Instagram and LinkedIn posts from Buffer's GraphQL API.

Settings (environment variables):
  BUFFER_API_KEY          Personal API key from https://publish.buffer.com/settings/api
  BUFFER_ORGANIZATION_ID  The Buffer organization that holds the channels
  BUFFER_CHANNEL_IDS      Comma-separated channel ids for Instagram and LinkedIn

Buffer refreshes post metrics about once a day, so a pull reflects the
numbers as of Buffer's last refresh.
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone

import pandas as pd
import requests

from .. import config
from .base import Connector, ConnectorError

API_URL = "https://api.buffer.com"
PAGE_SIZE = 100
MAX_PAGES = 20

POSTS_QUERY = """
query AiEdgePosts($input: PostsInput!, $first: Int, $after: String) {
  posts(input: $input, first: $first, after: $after) {
    pageInfo { hasNextPage endCursor }
    edges { node {
      id channelService status via text dueAt sentAt metricsUpdatedAt
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

# Buffer metric type -> column in social_posts
METRIC_COLUMNS = {
    "reactions": "likes",
    "likes": "likes",
    "comments": "comments",
    "shares": "shares",
    "saves": "saves",
    "views": "views",
    "reach": "reach",
    "impressions": "impressions",
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


def node_to_row(node: dict, pulled_on: str) -> dict:
    row = {
        "post_id": node["id"],
        "date": (node.get("sentAt") or node.get("dueAt") or "")[:10],
        "channel": node.get("channelService"),
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
    dataset = "social_posts"
    required_env = ("BUFFER_API_KEY", "BUFFER_ORGANIZATION_ID", "BUFFER_CHANNEL_IDS")
    description = "Pulls every sent Instagram and LinkedIn post with likes, comments, shares, saves, views and reach."

    def _post(self, variables: dict) -> dict:
        try:
            resp = requests.post(
                API_URL,
                json={"query": POSTS_QUERY, "variables": variables},
                headers={"Authorization": f"Bearer {config.env('BUFFER_API_KEY')}"},
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

    def fetch(self, start: date, end: date) -> pd.DataFrame:
        channel_ids = [c.strip() for c in config.env("BUFFER_CHANNEL_IDS", "").split(",") if c.strip()]
        start_at = datetime.combine(start, time.min, tzinfo=timezone.utc).isoformat()
        end_at = datetime.combine(end, time.max.replace(microsecond=0), tzinfo=timezone.utc).isoformat()
        variables = {
            "first": PAGE_SIZE,
            "input": {
                "organizationId": config.env("BUFFER_ORGANIZATION_ID"),
                "filter": {"channelIds": channel_ids, "status": ["sent"], "dueAt": {"start": start_at, "end": end_at}},
                "sort": [{"field": "dueAt", "direction": "desc"}],
            },
        }
        pulled_on = date.today().isoformat()
        rows: list[dict] = []
        for _ in range(MAX_PAGES):
            page = self._post(variables)
            rows += [node_to_row(e["node"], pulled_on) for e in page.get("edges") or []]
            info = page.get("pageInfo") or {}
            if not info.get("hasNextPage"):
                break
            variables["after"] = info.get("endCursor")
        rows = [r for r in rows if r["channel"] in ("instagram", "linkedin")]
        return pd.DataFrame(rows)
