# Content reporting dashboard

A Streamlit dashboard that brings a brand's email, social and other channels into one weekly and monthly report. It was built for AI Edge, Blavity's AI training brand, and works for any brand. Each brand lists the channels it tracks in a short file in `brands/`, and the pages build themselves from that list. One brand can track a newsletter and Instagram, another can track Facebook, X, TikTok, Pinterest and two Instagram accounts, with no code changes.

The app has four pages:

| Page | What it shows |
| --- | --- |
| **General reporting** | A follower or subscriber card for every channel, open rate and click-through rate for every email channel, and trend lines for each. Filter by date range and channel in the sidebar. |
| **Qualitative reporting** | Best-performing CTAs ranked by clicks (CTA, where used, channel, date, clicks), comment keywords from captions, posts ranked by clicks, and engagement by post format for any social channel, such as carousels against videos (average likes, comments, shares and saves per post). |
| **Data log** | Every table behind the dashboard, with the source of each row and a CSV download. |
| **Update data** | CSV upload and one-row entry forms for every table, the LinkedIn content export, and pulls from connected sources. |

Every number on the dashboard comes from a row you can see in the Data log. Nothing is hardcoded.

## Run it

You need Python 3.11 or newer.

```bash
git clone <your-repo-url> content-dashboard
cd content-dashboard
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

The app opens at http://localhost:8501. Pick a brand in the sidebar. The **Example Brand** shows the made-up numbers in `sample_data/` so you can try every page. Real brands start empty and never show sample data, so made-up and real numbers never mix.

To run the tests:

```bash
pip install -r requirements-dev.txt
pytest
```

## Brands and channels

A brand is one file in `brands/`. Here is AI Edge's:

```toml
name = "AI Edge"
title = "AI Edge content reporting"

[[channels]]
id = "newsletter"
name = "Newsletter"
platform = "newsletter"

[[channels]]
id = "instagram"
name = "Instagram"
platform = "instagram"
handle = "@ai.edge.workshops"
```

And so on for each channel. Each channel has:

| Field | Required | What it is |
| --- | --- | --- |
| `id` | yes | Short id used in the data files. Lowercase letters, numbers and dashes. Unique within the brand. |
| `platform` | yes | One of the platforms below. It decides which numbers the channel gets. |
| `name` | no | Name shown in the app. Defaults to the platform's name. |
| `handle` | no | Account handle, for reference. |
| `color` | no | Chart color, such as `"#C2417A"`. One is picked if you leave it out. |

`title` is optional too. It defaults to the brand name followed by "content reporting".

A brand can have any number of channels, including two on the same platform. For example, Travel Noire's Instagram and TN Plus Instagram are two channels with `platform = "instagram"` and different ids. Remove a channel by deleting its block. Its rows stay in the data files but no longer show.

### Starting a new brand

`brands/starters/` has a starter file for each Blavity brand, listing the content platforms from the brand accounts list: Blavity, Healthstack, Aisle21, Travel Noire, Shadow & Act, Shadow & Act Unscripted, Lunchtable, AfroTech, AfroTech Conference, AfroTech Culture, AfroTech Events, Black Tech Green Money Podcast, BlavityFoodie, BlavityLive, BlavityEvents and BlavityShop.

1. Copy the starter to `brands/`, for example `brands/starters/travel-noire.toml` to `brands/travel-noire.toml`. Or copy `brands/example.toml` and edit it. The file name is the brand id.
2. Add, remove or rename channels. Add a newsletter channel if the brand sends one.
3. Run the app and pick the brand in the sidebar. Its data is saved in `data/<brand id>/`.

To open on one brand, set `BRAND` in `.env`, for example `BRAND=travel-noire`. If it is not set, the app opens on the first brand that is not the example.

### Platforms

The platform's kind decides what the dashboard expects:

- **social**: a follower count, and posts with likes, comments, shares, saves, views, reach, impressions and clicks.
- **email**: a subscriber count, plus open rate and click-through rate.
- **other**: an audience count only, such as podcast subscribers.

Any channel can have CTA clicks.

| Platform | Name | Kind | Buffer can pull posts |
| --- | --- | --- | --- |
| `instagram` | Instagram | social | yes |
| `tiktok` | TikTok | social | yes |
| `facebook` | Facebook | social | yes |
| `linkedin` | LinkedIn | social | yes |
| `x` | X (Twitter) | social | yes |
| `threads` | Threads | social | yes |
| `pinterest` | Pinterest | social | yes |
| `youtube` | YouTube | social | yes |
| `bluesky` | Bluesky | social | yes |
| `snapchat` | Snapchat | social |  |
| `reddit` | Reddit | social |  |
| `tumblr` | Tumblr | social |  |
| `spill` | Spill | social |  |
| `flipboard` | Flipboard | social |  |
| `giphy` | Giphy | social |  |
| `newsletter` | Email newsletter | email |  |
| `substack` | Substack | email |  |
| `podcast` | Podcast | other |  |
| `other` | Other | other |  |

To add a platform, add one line to `PLATFORMS` in `content_dashboard/platforms.py`, such as `Platform("twitch", "Twitch", SOCIAL)`. Nothing else changes.

### One repo, many brands

This repo holds every brand's file on the main branch. No branch per brand is needed. Each team can either:

- **Use this repo.** Add a brand file, run the app, and keep your numbers in `data/<brand id>/`. If the brands pull from different Buffer or ManyChat accounts, give each brand its own settings (see [Connectors and settings](#connectors-and-settings)).
- **Fork it.** Fork the repo, add your brand file, and set `BRAND` to it. To get later fixes, pull from this repo now and then. Your brand file won't conflict because no one else edits it.

Brand files hold no secrets and no numbers, so they are safe to commit. Your numbers stay in `data/`, which git ignores.

## Where your data lives

Real numbers are saved as CSV files in `data/<brand id>/`, one file per table, such as `data/ai-edge/audience.csv`. Git ignores `data/`, so pushing the repo never publishes your numbers. Back it up or share it some other way, such as a shared drive.

To keep the data somewhere else, set `DATA_DIR` in `.env`. A relative path is read from the repo root.

## Updating the data each reporting period

Do this once a week, or once a month for the monthly report. Everything happens on the **Update data** page. Pick the table, then upload a CSV, fill in the form, or pull from a connector. The forms only offer channels that use that table.

| Table | When | What to do |
| --- | --- | --- |
| Audience | Weekly | Enter each channel's follower or subscriber count with the date you read it. For a newsletter, the delivered count on each send works as the subscriber count. |
| Email stats | After each send, or each period | Enter open rate and click-through rate from your email platform's export. Use one row per send or one row per week or month. |
| Posts | Weekly | Click **Pull from Buffer** if Buffer is set up, or upload each platform's export. For LinkedIn, upload the content export (see below) to add LinkedIn's clicks. |
| CTA clicks | After each send, and weekly | Upload newsletter link clicks from your email platform's link report. Click **Pull from ManyChat** for DM automation clicks if it is set up. |

When you upload, choose **Add to my data** to keep existing rows. A new row with the same key as an existing row updates it, which is how you correct a number. Blank cells in the new row keep the old value, and the row's source notes both.

**LinkedIn content export.** Buffer does not report LinkedIn clicks, but LinkedIn's own export does. On the LinkedIn page, go to Analytics > Content > Export. On the Update data page, pick **Posts** and upload the file (.xls) without changing it. This option shows for brands with a LinkedIn channel. Each post in the export is matched to the same post from Buffer by its opening words and date, and takes LinkedIn's clicks, impressions, likes, comments and reposts. Posts Buffer does not have are added. The export's "Posted by" names are not kept.

Rates are entered as shares in CSVs, so 17.9% is `0.179`. The entry forms take percentages and convert them for you.

## CSV schemas

Every brand uses the same four tables. Each row says which channel it belongs to in the `channel` column, using the channel ids from the brand file. Dates are `YYYY-MM-DD`. Columns marked optional can be blank. The **Columns and template** tab on the Update data page has the same information and an empty template to download. The schemas are defined in `content_dashboard/schemas.py`.

### audience.csv

Followers or subscribers per channel on the date you read the count. Unique by `channel` + `metric` + `date`. Used by social, email, other channels. Where to get it: Each platform's analytics page (followers), or your email platform or Substack (subscribers).

| Column | Type | Required | Notes |
| --- | --- | --- | --- |
| date | date | yes | Date you read the count. |
| channel | channel id | yes | Channel id from your brand file, such as instagram or newsletter. |
| metric | text | yes | followers for social channels, subscribers for email and other channels. One of: `followers`, `subscribers`. |
| value | whole number | yes | The count. |
| source | text | no | Where this row came from, such as 'Iterable export' or 'Manual entry'. |

### email_stats.csv

Open rate and click-through rate for an email channel, per send or per reporting period. Unique by `channel` + `period_id`. Used by email channels. Where to get it: Your email platform's campaign or period export (for example Iterable or Substack Stats).

| Column | Type | Required | Notes |
| --- | --- | --- | --- |
| channel | channel id | yes | Channel id from your brand file, such as instagram or newsletter. |
| period_id | text | yes | Short id, unique within the channel. Example: 2026-09 or send-2026-10-05. |
| label | text | yes | Name shown in the app. Example: September (4 sends) or 10/5 send. |
| start_date | date | yes | First day of the period. For one send, the send date. |
| end_date | date | yes | Last day of the period. For one send, the send date. |
| sends | whole number | no |  |
| delivered | whole number | no |  |
| total_opens | whole number | no | Raw total opens. |
| link_clicks | whole number | no | Link clicks in the period. |
| open_rate | rate | no | Opens divided by delivered. Use the privacy-filtered rate if your platform has one. |
| click_rate | rate | no | Unique clicks divided by delivered. |
| click_to_open | rate | no |  |
| unsubscribe_rate | rate | no |  |
| source | text | no | Where this row came from, such as 'Iterable export' or 'Manual entry'. |

### posts.csv

One row per post on a social channel, with its engagement. Unique by `post_id`. Used by social channels. Where to get it: Pulled from Buffer when it is set up, or exported from each platform's analytics.

| Column | Type | Required | Notes |
| --- | --- | --- | --- |
| post_id | text | yes | Unique post id. Any unique text works for manual rows. |
| date | date | yes | Date the post went live. |
| channel | channel id | yes | Channel id from your brand file, such as instagram or newsletter. |
| format | text | yes | Post format. One of: `carousel`, `video`, `single image`, `text`, `story`, `other`. |
| likes | whole number | no |  |
| comments | whole number | no |  |
| shares | whole number | no |  |
| saves | whole number | no |  |
| views | whole number | no |  |
| reach | whole number | no |  |
| impressions | whole number | no |  |
| clicks | whole number | no | Clicks on the post as the platform counts them. |
| text | text | no | Caption or post text. Used to find comment keywords like AI NEWS. |
| source | text | no | Where this row came from, such as 'Iterable export' or 'Manual entry'. |

### cta_clicks.csv

Clicks on a call to action: a newsletter link, a DM automation keyword, a link in bio, and so on. Unique by `cta_id`. Used by social, email, other channels. Where to get it: Email link reports (such as an Iterable link heatmap), ManyChat, or a link tool like Linktree.

| Column | Type | Required | Notes |
| --- | --- | --- | --- |
| cta_id | text | yes | Short unique id. Example: nl-1005-gemini. |
| date | date | yes | Send date, post date, or the last day the clicks were counted for. |
| channel | channel id | yes | Channel id from your brand file, such as instagram or newsletter. |
| cta | text | yes | The CTA as people saw it. |
| where_used | text | no | Where it appeared. Example: Email, Story section. |
| clicks | whole number | yes | Clicks or conversions. |
| measure | text | no | What the clicks count. Example: Unique link clicks, DM link clicks. |
| keyword | text | no | Comment keyword that triggers a DM automation, if any. Example: AI NEWS. |
| link | text | no |  |
| source | text | no | Where this row came from, such as 'Iterable export' or 'Manual entry'. |
## How the numbers are worked out

- **Followers and subscribers** show the latest count in the date range for each channel, its change from the count before, and its change across the range.
- **Open rate and click-through rate** come from the email stats row that ends last in the date range for each email channel, compared with the row before it in percentage points. For AI Edge's newsletter, these are Iterable's Apple MPP filtered opens and filtered unique clicks.
- **CTA ranking** puts every channel's CTA clicks in one list, sorted by clicks. The Measure column says what each count is, because a newsletter's unique link clicks and a DM automation's link clicks are not the same thing.
- **Comment keywords** are read from captions, such as `Comment "AI NEWS"`. Spelling variants like `AINEWS` count as the same keyword. Clicks come from CTA clicks rows with the same keyword.
- **Engagement by post format** averages each metric per post for the formats you pick, on one channel. It leaves out Stories and posts with no metrics. One post that travels far can move an average a lot, so the page lists the posts behind it.

## Connectors and settings

Connectors are optional. They fill a table automatically and save through the same path as a CSV upload. Settings come from environment variables. Locally, copy `.env.example` to `.env` and fill in what you use. Never commit `.env`.

| Connector | Fills | Settings |
| --- | --- | --- |
| Buffer | Posts | `BUFFER_API_KEY`, `BUFFER_ORGANIZATION_ID`, `BUFFER_CHANNEL_IDS` |
| ManyChat (Google Sheet) | CTA clicks | `MANYCHAT_SHEET_CSV_URL`, optional `MANYCHAT_CHANNEL` |
| ManyChat API | CTA clicks | `MANYCHAT_API_KEY` (not built yet, see below) |

**Settings for one brand.** Put the brand id in capitals, with `_` for `-`, in front of any setting to make it apply to that brand only. `TRAVEL_NOIRE_BUFFER_API_KEY` is used for `brands/travel-noire.toml` and wins over `BUFFER_API_KEY`. A brand without its own setting uses the plain one. The same works for `APP_TITLE`.

**Buffer.** Create a key at https://publish.buffer.com/settings/api. Only the Buffer organization owner can create one, and the key can read everything in that organization, so keep it secret. List the Buffer channel ids to pull in `BUFFER_CHANNEL_IDS`. Each post is filed under the brand's channel on the same platform. When a brand has two channels on one platform, write `id:channel` to say which is which, such as `abc123:instagram,def456:tn-plus-instagram`. Buffer refreshes post metrics about once a day. It does not provide follower counts or Substack email stats, so those are entered by hand.

**ManyChat through Google Sheets.** In each keyword flow in ManyChat, add a Google Sheets **Add row** action right after the link is clicked. Have it write these columns: `date`, `keyword`, `cta_text`, `link`, `clicks` (put `1` in clicks). In Google Sheets, choose File > Share > Publish to web, pick the sheet, choose CSV, and put the link in `MANYCHAT_SHEET_CSV_URL`. Each pull totals the clicks per day and keyword and files them under the brand's first Instagram channel, or the channel in `MANYCHAT_CHANNEL`. Anyone with that link can read the sheet, so log only what the dashboard needs.

## Deploying on Streamlit Community Cloud

1. Push this repo to GitHub. A private repo works.
2. Go to https://share.streamlit.io, choose **Create app**, pick the repo and branch, and set the main file to `app.py`.
3. Under **Advanced settings**, pick Python 3.11 or newer. Paste any settings you use into **Secrets** in TOML format:

   ```toml
   BRAND = "ai-edge"
   BUFFER_API_KEY = "..."
   BUFFER_ORGANIZATION_ID = "..."
   BUFFER_CHANNEL_IDS = "id1,id2"
   ```

   Streamlit exposes these secrets as environment variables, so the app reads them the same way as `.env`.
4. Deploy, and use the app's sharing settings to choose who can view it.

Community Cloud does not keep files between restarts. Rows saved in the app there are lost when the app restarts or redeploys. For a hosted copy, either pull from connectors each time you open it, or keep your CSVs somewhere durable and upload them. Running locally avoids this.

## Adding a connector

The connector framework is in `content_dashboard/connectors/`. A placeholder, `ManyChatApiConnector`, is already registered and shows on the Update data page as "not built yet". To build it, or any new connector:

1. **Check what the API offers.** For ManyChat, the API key comes from Settings > API, and the reference is at https://api.manychat.com/swagger. At the time of writing, the public API covers contacts, tags, custom fields and flows, but not link-click statistics. If that is still true, have each flow store clicks somewhere the API can read. For example, increment a custom field per keyword with an action step, then read it back.
2. **Write `fetch(start, end, brand)`.** It must return a pandas DataFrame with the columns of the table it fills, such as `cta_clicks`, with `channel` set to one of the brand's channel ids and `source` set to something like `ManyChat API, pulled 2026-10-20`. Read settings with `config.env(name, brand=brand.id)` so each brand can have its own. Raise `ConnectorError` with a plain message for anything the person can fix, such as a wrong key.
3. **Turn it on.** Set `implemented = True` and list its settings in `required_env` and `.env.example`. A new connector subclasses `Connector` in `connectors/base.py` and is added to `REGISTRY` in `connectors/__init__.py`.
4. **Test it.** Add a test in `tests/` that mocks the HTTP call, like `tests/test_buffer.py` does, and checks that the rows pass `storage.validate()`.

Nothing else changes. The Update data page lists the connector and saves its rows through `storage.save()`.

## Repo layout

```
app.py                      Entry point: brand picker, sidebar filters and page navigation
brands/                     One file per brand: its name and channels
  starters/                 Starter files for each Blavity brand
content_dashboard/
  platforms.py              Every platform a channel can be on, and its kind
  brands.py                 Reads and checks the brand files
  config.py                 Paths and settings from environment variables
  schemas.py                The four tables
  storage.py                Load, validate and save each brand's CSVs
  metrics.py                Every calculation, with no Streamlit code
  components.py             KPI cards, charts and table helpers
  connectors/               Buffer, ManyChat (Google Sheet) and the ManyChat API placeholder
  importers.py              Readers for platform exports, such as the LinkedIn content export
  views/                    One module per page
sample_data/                Made-up CSVs for the example brand
data/                       Real CSVs, one folder per brand (ignored by git)
tests/                      pytest tests, including a headless run of every page for every brand file
```

## License

MIT. See `LICENSE`.
