"""Platforms a brand's channels can be on, and what each kind of platform reports.

A platform's kind decides which numbers the dashboard expects for it:
  social  followers, plus posts with likes, comments, shares and so on
  email   subscribers, open rate and click-through rate
  other   an audience count only (subscribers, listeners, members)

To support a new platform, add one line to PLATFORMS. Nothing else changes.
"""

from __future__ import annotations

from dataclasses import dataclass

SOCIAL = "social"
EMAIL = "email"
OTHER = "other"


@dataclass(frozen=True)
class Platform:
    key: str
    label: str
    kind: str
    # Buffer's name for the service, when Buffer can pull its posts.
    buffer_service: str | None = None

    @property
    def audience_metric(self) -> str:
        return "followers" if self.kind == SOCIAL else "subscribers"


PLATFORMS: dict[str, Platform] = {p.key: p for p in [
    Platform("instagram", "Instagram", SOCIAL, "instagram"),
    Platform("tiktok", "TikTok", SOCIAL, "tiktok"),
    Platform("facebook", "Facebook", SOCIAL, "facebook"),
    Platform("linkedin", "LinkedIn", SOCIAL, "linkedin"),
    Platform("x", "X (Twitter)", SOCIAL, "twitter"),
    Platform("threads", "Threads", SOCIAL, "threads"),
    Platform("pinterest", "Pinterest", SOCIAL, "pinterest"),
    Platform("youtube", "YouTube", SOCIAL, "youtube"),
    Platform("bluesky", "Bluesky", SOCIAL, "bluesky"),
    Platform("snapchat", "Snapchat", SOCIAL),
    Platform("reddit", "Reddit", SOCIAL),
    Platform("tumblr", "Tumblr", SOCIAL),
    Platform("spill", "Spill", SOCIAL),
    Platform("flipboard", "Flipboard", SOCIAL),
    Platform("giphy", "Giphy", SOCIAL),
    Platform("newsletter", "Email newsletter", EMAIL),
    Platform("substack", "Substack", EMAIL),  # Buffer only posts Substack Notes, which have no email stats
    Platform("podcast", "Podcast", OTHER),
    Platform("other", "Other", OTHER),
]}
