"""One CSV schema per table.

These definitions drive everything else: loading and type conversion, upload
validation, the manual entry forms, the CSV templates and the README tables.
Change a schema here and every page follows.

Rates (open rate, click-through rate) are stored as shares: 0.179 means 17.9%.
Dates are YYYY-MM-DD.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Column kinds
TEXT = "text"
DATE = "date"
INT = "int"
FLOAT = "float"
RATE = "rate"  # a share between 0 and 1


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
    channels: tuple[str, ...]
    description: str
    where_to_get_it: str
    key: tuple[str, ...]
    columns: tuple[Column, ...] = field(default_factory=tuple)

    @property
    def column_names(self) -> list[str]:
        return [c.name for c in self.columns]

    @property
    def date_column(self) -> str:
        return next(c.name for c in self.columns if c.kind == DATE)

    def column(self, name: str) -> Column:
        return next(c for c in self.columns if c.name == name)


SOURCE = Column("source", TEXT, required=False, help="Where this row came from, such as 'Iterable export' or 'Manual entry'.")

DATASETS: dict[str, Dataset] = {
    "newsletter_sends": Dataset(
        name="newsletter_sends",
        title="Newsletter sends",
        channels=("newsletter",),
        description="One row per newsletter send.",
        where_to_get_it="Iterable campaign metrics export for each send.",
        key=("send_date",),
        columns=(
            Column("send_date", DATE, help="Date the newsletter went out."),
            Column("day_time_et", TEXT, required=False, help="Send day and time, Eastern. Example: Mon 12pm."),
            Column("delivered", INT, help="Emails delivered. Used as the newsletter subscriber count."),
            Column("total_opens", INT, required=False, help="Total opens, raw (not MPP filtered)."),
            Column("unique_link_clicks", INT, required=False, help="Unique link clicks, summed across links."),
            Column("unsubscribes", INT, required=False, help="Unsubscribes from this send."),
            SOURCE,
        ),
    ),
    "newsletter_periods": Dataset(
        name="newsletter_periods",
        title="Newsletter reporting periods",
        channels=("newsletter",),
        description="Filtered open rate and click-through rate per reporting period (a week, a month, or a single send).",
        where_to_get_it="Iterable metrics export for the period. Use the Apple MPP filtered open rate and filtered unique clicks.",
        key=("period_id",),
        columns=(
            Column("period_id", TEXT, help="Short unique id. Example: 2026-09 or send-2026-10-05."),
            Column("label", TEXT, help="Name shown in the app. Example: September (4 sends)."),
            Column("start_date", DATE, help="First day of the period."),
            Column("end_date", DATE, help="Last day of the period."),
            Column("sends", INT, required=False, help="Number of sends in the period."),
            Column("delivered", INT, required=False, help="Emails delivered across the period."),
            Column("open_rate_filtered", RATE, help="Unique opens with Apple MPP filtered out, divided by delivered."),
            Column("click_rate_filtered", RATE, help="Filtered unique clicks divided by delivered."),
            Column("click_to_open_filtered", RATE, required=False, help="Filtered clicks divided by filtered opens."),
            Column("unsubscribe_rate", RATE, required=False, help="Unsubscribes divided by delivered."),
            SOURCE,
        ),
    ),
    "newsletter_links": Dataset(
        name="newsletter_links",
        title="Newsletter links",
        channels=("newsletter",),
        description="Link clicks per send. Feeds the CTA ranking.",
        where_to_get_it="Iterable link heatmap for each send.",
        key=("link_id",),
        columns=(
            Column("link_id", TEXT, help="Short unique id. Example: nl-1005-gemini."),
            Column("send_date", DATE, help="Date of the send the link was in."),
            Column("link_text", TEXT, help="The linked text or a short name for the link."),
            Column("cta_wording", TEXT, required=False, help="CTA wording around the link, if any."),
            Column("section", TEXT, required=False, help="Newsletter section. Example: Story, Events, Go Deeper."),
            Column("unique_clicks", INT, help="Unique clicks on this link."),
            SOURCE,
        ),
    ),
    "social_posts": Dataset(
        name="social_posts",
        title="Instagram and LinkedIn posts",
        channels=("instagram", "linkedin"),
        description="One row per Instagram or LinkedIn post with its engagement.",
        where_to_get_it="Pulled from Buffer when BUFFER_API_KEY is set. LinkedIn clicks come from the LinkedIn content export (Analytics > Content > Export), uploaded on the Update data page.",
        key=("post_id",),
        columns=(
            Column("post_id", TEXT, help="Unique post id. Any unique text works for manual rows."),
            Column("date", DATE, help="Date the post went live."),
            Column("channel", TEXT, choices=("instagram", "linkedin")),
            Column("format", TEXT, help="Post format.", choices=("carousel", "video", "single image", "text", "story", "other")),
            Column("likes", INT, required=False),
            Column("comments", INT, required=False),
            Column("shares", INT, required=False),
            Column("saves", INT, required=False, help="Instagram only."),
            Column("views", INT, required=False),
            Column("reach", INT, required=False),
            Column("impressions", INT, required=False, help="LinkedIn only."),
            Column("clicks", INT, required=False, help="LinkedIn only, from the LinkedIn content export. Counts any click on the post, not only link clicks."),
            Column("text", TEXT, required=False, help="Caption or post text. Used to find comment keywords like AI NEWS."),
            SOURCE,
        ),
    ),
    "followers": Dataset(
        name="followers",
        title="Followers",
        channels=("instagram", "linkedin"),
        description="Follower count per channel on the date you read it.",
        where_to_get_it="Instagram professional dashboard and LinkedIn page analytics.",
        key=("channel", "date"),
        columns=(
            Column("date", DATE, help="Date you read the count."),
            Column("channel", TEXT, choices=("instagram", "linkedin")),
            Column("followers", INT),
            SOURCE,
        ),
    ),
    "substack": Dataset(
        name="substack",
        title="Substack",
        channels=("substack",),
        description="Substack subscriber count, open rate and click-through rate on the date you read them.",
        where_to_get_it="Substack dashboard, Stats page.",
        key=("date",),
        columns=(
            Column("date", DATE, help="Date you read the numbers."),
            Column("subscribers", INT, required=False, help="Total subscribers on this date. Leave blank on rows that only record a post's open rate."),
            Column("open_rate", RATE, required=False, help="Open rate as a share. 0.42 means 42%. Use the post's Opened figure for a per-post row."),
            Column("click_rate", RATE, required=False, help="Click-through rate as a share. 0.031 means 3.1%."),
            SOURCE,
        ),
    ),
    "manychat_clicks": Dataset(
        name="manychat_clicks",
        title="ManyChat link clicks",
        channels=("instagram",),
        description="Link clicks from Instagram DM automations. ManyChat is the source of truth for Instagram click-through.",
        where_to_get_it="ManyChat automation stats, or the Google Sheet your ManyChat flows log clicks to.",
        key=("date", "keyword"),
        columns=(
            Column("date", DATE, help="Day, or last day of the period, the clicks were counted for."),
            Column("keyword", TEXT, help="Comment keyword that triggers the flow. Example: AI NEWS."),
            Column("cta_text", TEXT, required=False, help="CTA as written in the post. Example: Comment AI NEWS for the newsletter link."),
            Column("link", TEXT, required=False, help="Where the link goes."),
            Column("clicks", INT, help="Link clicks."),
            SOURCE,
        ),
    ),
}


def get(name: str) -> Dataset:
    return DATASETS[name]
