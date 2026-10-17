"""The four CSV tables every brand uses.

Every table has a `channel` column holding a channel id from the brand's file
in brands/. That is what lets one set of tables cover any mix of platforms.

These definitions drive loading, upload checks, the entry forms, the CSV
templates and the README tables. Change a schema here and every page follows.

Rates (open rate, click-through rate) are stored as shares: 0.179 means 17.9%.
Dates are YYYY-MM-DD.
"""

from __future__ import annotations

from dataclasses import dataclass, field

TEXT = "text"
DATE = "date"
INT = "int"
FLOAT = "float"
RATE = "rate"        # a share between 0 and 1
CHANNEL = "channel"  # a channel id from the brand's file

FORMATS = ("carousel", "video", "single image", "text", "story", "other")
AUDIENCE_METRICS = ("followers", "subscribers")


@dataclass(frozen=True)
class Column:
    name: str
    kind: str
    required: bool = True
    help: str = ""
    choices: tuple[str, ...] = ()


@dataclass(frozen=True)
class Dataset:
    name: str
    title: str
    description: str
    where_to_get_it: str
    key: tuple[str, ...]
    date_column: str
    kinds: tuple[str, ...]  # which kinds of channel use this table: social, email, other
    columns: tuple[Column, ...] = field(default_factory=tuple)

    @property
    def column_names(self) -> list[str]:
        return [c.name for c in self.columns]

    def column(self, name: str) -> Column:
        return next(c for c in self.columns if c.name == name)


SOURCE = Column("source", TEXT, required=False, help="Where this row came from, such as 'Iterable export' or 'Manual entry'.")
CHANNEL_COL = Column("channel", CHANNEL, help="Channel id from your brand file, such as instagram or newsletter.")

DATASETS: dict[str, Dataset] = {
    "audience": Dataset(
        name="audience",
        title="Audience",
        description="Followers or subscribers per channel on the date you read the count.",
        where_to_get_it="Each platform's analytics page (followers), or your email platform or Substack (subscribers).",
        key=("channel", "metric", "date"),
        date_column="date",
        kinds=("social", "email", "other"),
        columns=(
            Column("date", DATE, help="Date you read the count."),
            CHANNEL_COL,
            Column("metric", TEXT, help="followers for social channels, subscribers for email and other channels.", choices=AUDIENCE_METRICS),
            Column("value", INT, help="The count."),
            SOURCE,
        ),
    ),
    "email_stats": Dataset(
        name="email_stats",
        title="Email stats",
        description="Open rate and click-through rate for an email channel, per send or per reporting period.",
        where_to_get_it="Your email platform's campaign or period export (for example Iterable or Substack Stats).",
        key=("channel", "period_id"),
        date_column="end_date",
        kinds=("email",),
        columns=(
            CHANNEL_COL,
            Column("period_id", TEXT, help="Short id, unique within the channel. Example: 2026-09 or send-2026-10-05."),
            Column("label", TEXT, help="Name shown in the app. Example: September (4 sends) or 10/5 send."),
            Column("start_date", DATE, help="First day of the period. For one send, the send date."),
            Column("end_date", DATE, help="Last day of the period. For one send, the send date."),
            Column("sends", INT, required=False),
            Column("delivered", INT, required=False),
            Column("total_opens", INT, required=False, help="Raw total opens."),
            Column("link_clicks", INT, required=False, help="Link clicks in the period."),
            Column("open_rate", RATE, required=False, help="Opens divided by delivered. Use the privacy-filtered rate if your platform has one."),
            Column("click_rate", RATE, required=False, help="Unique clicks divided by delivered."),
            Column("click_to_open", RATE, required=False),
            Column("unsubscribe_rate", RATE, required=False),
            SOURCE,
        ),
    ),
    "posts": Dataset(
        name="posts",
        title="Posts",
        description="One row per post on a social channel, with its engagement.",
        where_to_get_it="Pulled from Buffer when it is set up, or exported from each platform's analytics.",
        key=("post_id",),
        date_column="date",
        kinds=("social",),
        columns=(
            Column("post_id", TEXT, help="Unique post id. Any unique text works for manual rows."),
            Column("date", DATE, help="Date the post went live."),
            CHANNEL_COL,
            Column("format", TEXT, help="Post format.", choices=FORMATS),
            Column("likes", INT, required=False),
            Column("comments", INT, required=False),
            Column("shares", INT, required=False),
            Column("saves", INT, required=False),
            Column("views", INT, required=False),
            Column("reach", INT, required=False),
            Column("impressions", INT, required=False),
            Column("clicks", INT, required=False, help="Clicks on the post as the platform counts them."),
            Column("text", TEXT, required=False, help="Caption or post text. Used to find comment keywords like AI NEWS."),
            SOURCE,
        ),
    ),
    "cta_clicks": Dataset(
        name="cta_clicks",
        title="CTA clicks",
        description="Clicks on a call to action: a newsletter link, a DM automation keyword, a link in bio, and so on.",
        where_to_get_it="Email link reports (such as an Iterable link heatmap), ManyChat, or a link tool like Linktree.",
        key=("cta_id",),
        date_column="date",
        kinds=("social", "email", "other"),
        columns=(
            Column("cta_id", TEXT, help="Short unique id. Example: nl-1005-gemini."),
            Column("date", DATE, help="Send date, post date, or the last day the clicks were counted for."),
            CHANNEL_COL,
            Column("cta", TEXT, help="The CTA as people saw it."),
            Column("where_used", TEXT, required=False, help="Where it appeared. Example: Email, Story section."),
            Column("clicks", INT, help="Clicks or conversions."),
            Column("measure", TEXT, required=False, help="What the clicks count. Example: Unique link clicks, DM link clicks."),
            Column("keyword", TEXT, required=False, help="Comment keyword that triggers a DM automation, if any. Example: AI NEWS."),
            Column("link", TEXT, required=False),
            SOURCE,
        ),
    ),
}


def get(name: str) -> Dataset:
    return DATASETS[name]
