# Content reporting dashboard

A Streamlit dashboard that brings newsletter, Instagram, LinkedIn and Substack performance into one weekly and monthly report. It was built for AI Edge, Blavity's AI training brand, and is shared here so any team can run it with its own data. See [Setting it up for your team](#setting-it-up-for-your-team).

The report has two parts: general reporting (subscriber growth, follower count, open rate, click-through rate) and qualitative reporting (best-performing CTAs, and Instagram static carousels against videos). The app has four pages:

| Page | What it shows |
| --- | --- |
| **General reporting** | KPI cards and trend lines for subscriber growth, follower count, open rate and click-through rate. Filter by date range and channel in the sidebar. |
| **Qualitative reporting** | Best-performing CTAs ranked by clicks (CTA text, where used, channel, date, clicks), Instagram comment keywords, LinkedIn posts ranked by clicks, and a side-by-side comparison of Instagram static carousels and videos (average likes, comments, shares and saves per post). |
| **Data log** | Every table behind the dashboard, with the source of each row and a CSV download. |
| **Update data** | CSV upload and one-row entry forms for every table, plus pulls from connected sources. |

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

The app opens at http://localhost:8501. A fresh clone has no real data, so it shows the files in `sample_data/` and says so on every page. These are made-up numbers for trying the app, not any team's real results. As soon as you save your first real table, sample data turns off everywhere. Tables you have not filled yet then show as empty, so sample and real numbers never mix.

To run the tests:

```bash
pip install -r requirements-dev.txt
pytest
```

## Setting it up for your team

Everything specific to one team lives in settings and data, not in the code. To use the dashboard for your own brand:

1. **Copy the repo.** Fork it on GitHub, or clone it and push it to a new repo of your own.
2. **Name it.** Copy `.env.example` to `.env` and set `APP_TITLE`, for example `APP_TITLE=Your Brand content reporting`. On Streamlit Community Cloud, put it in Secrets instead.
3. **Add your numbers.** Run the app and use the Update data page. Upload CSVs that follow the schemas below, or fill in the forms. Sample data turns off as soon as you save your first real table.
4. **Connect your accounts (optional).** For Buffer, set your own `BUFFER_API_KEY`, `BUFFER_ORGANIZATION_ID` and `BUFFER_CHANNEL_IDS`. For ManyChat clicks, set your own `MANYCHAT_SHEET_CSV_URL`.

Things that adjust themselves: Instagram comment keywords (like `AI NEWS`) are read from your own captions, and CTAs come from your own link and ManyChat data.

If your team does not use one of the four channels, leave its tables empty; its cards will say there is no data yet. To hide it, untick it under Channels in the sidebar. Channel display names and colors are in `content_dashboard/config.py`. Adding a new channel, such as TikTok, means adding it to `CHANNELS` in `config.py`, to the tables that hold it in `schemas.py`, and to the cards and charts in `views/general.py`.

Your real data is saved in `data/`, which git ignores, so pushing your copy of the repo never publishes your numbers.

## Where your data lives

Real numbers are saved as CSV files in `data/`, one file per table, such as `data/followers.csv`. Git ignores this folder, so your numbers stay off GitHub. Back it up or share it some other way, such as a shared drive.

To keep the data somewhere else, set `AI_EDGE_DATA_DIR` in `.env`. A relative path is read from the repo root.

## Updating the data each reporting period

Do this once a week, or once a month for the monthly report. Everything happens on the **Update data** page.

| Table | When | What to do |
| --- | --- | --- |
| Newsletter sends | After each send | Enter delivered, total opens, unique link clicks and unsubscribes from the Iterable campaign export. |
| Newsletter reporting periods | Weekly or monthly | Enter the Apple MPP filtered open rate and filtered click-through rate from the Iterable metrics export. |
| Newsletter links | After each send | Upload the top links and their unique clicks from the Iterable link heatmap. |
| Instagram and LinkedIn posts | Weekly | Click **Pull from Buffer** if Buffer is set up. Then upload the LinkedIn content export (LinkedIn page > Analytics > Content > Export) as it is, to add LinkedIn clicks. |
| Followers | Weekly | Enter the Instagram and LinkedIn follower counts with the date you read them. |
| Substack | Weekly | Enter the subscriber count, open rate and click-through rate from Substack Stats. |
| ManyChat link clicks | Weekly | Click **Pull from ManyChat (Google Sheet)** if it is set up. Otherwise upload the clicks per keyword. |

When you upload, choose **Add to my data** to keep existing rows. A new row with the same key as an existing row updates it, which is how you correct a number. Blank cells in the new row keep the old value.

**LinkedIn content export.** Buffer does not report LinkedIn clicks, but LinkedIn's own export does. On the Update data page, pick **Instagram and LinkedIn posts** and upload the export file (.xls) without changing it. Each post in the export is matched to the same post from Buffer by its opening words and date, and takes LinkedIn's clicks, impressions, likes, comments and reposts. Posts Buffer does not have are added. The export's "Posted by" names are not kept. The export has no follower count; that comes from Analytics > Followers. The key is listed on each table's **Columns and template** tab.

Rates are entered as shares in CSVs, so 17.9% is `0.179`. The entry forms take percentages and convert them for you.

## CSV schemas

Every CSV has a header row with these exact column names. Dates are `YYYY-MM-DD`. Columns marked optional can be blank. Every table ends with an optional `source` column that says where the row came from, such as `Iterable export` or `Manual entry`. The **Columns and template** tab on the Update data page has the same information and an empty template to download. The schemas are defined in `content_dashboard/schemas.py`.

### newsletter_sends.csv

One row per newsletter send. Unique by `send_date`. Source: Iterable campaign metrics export.

| Column | Type | Required | Notes |
| --- | --- | --- | --- |
| send_date | date | yes | Date the newsletter went out |
| day_time_et | text | no | Send day and time, Eastern, such as `Mon 12pm` |
| delivered | whole number | yes | Emails delivered. Used as the newsletter subscriber count |
| total_opens | whole number | no | Raw total opens |
| unique_link_clicks | whole number | no | Unique link clicks, summed across links |
| unsubscribes | whole number | no | |

### newsletter_periods.csv

Filtered rates per reporting period: a week, a month or a single send. Unique by `period_id`. Source: Iterable metrics export.

| Column | Type | Required | Notes |
| --- | --- | --- | --- |
| period_id | text | yes | Short unique id, such as `2026-09` |
| label | text | yes | Name shown in the app, such as `September (4 sends)` |
| start_date | date | yes | |
| end_date | date | yes | |
| sends | whole number | no | |
| delivered | whole number | no | |
| open_rate_filtered | rate | yes | Unique opens with Apple MPP filtered out, divided by delivered |
| click_rate_filtered | rate | yes | Filtered unique clicks divided by delivered |
| click_to_open_filtered | rate | no | |
| unsubscribe_rate | rate | no | |

### newsletter_links.csv

Link clicks per send. These feed the CTA ranking. Unique by `link_id`. Source: Iterable link heatmap.

| Column | Type | Required | Notes |
| --- | --- | --- | --- |
| link_id | text | yes | Short unique id, such as `nl-1005-gemini` |
| send_date | date | yes | |
| link_text | text | yes | |
| cta_wording | text | no | CTA wording around the link |
| section | text | no | Story, Events, Go Deeper and so on |
| unique_clicks | whole number | yes | |

### social_posts.csv

One row per Instagram or LinkedIn post. Unique by `post_id`. Source: Buffer, or Instagram and LinkedIn exports.

| Column | Type | Required | Notes |
| --- | --- | --- | --- |
| post_id | text | yes | Any unique text for manual rows |
| date | date | yes | |
| channel | text | yes | `instagram` or `linkedin` |
| format | text | yes | `carousel`, `video`, `single image`, `text`, `story` or `other` |
| likes, comments, shares | whole number | no | |
| saves | whole number | no | Instagram only |
| views, reach | whole number | no | |
| impressions | whole number | no | LinkedIn only |
| clicks | whole number | no | LinkedIn only, from the LinkedIn content export. LinkedIn counts any click on a post, not only link clicks |
| text | text | no | Caption. Used to find comment keywords like `AI NEWS` |

### followers.csv

Follower count per channel on the date you read it. Unique by `channel` + `date`. Source: Instagram professional dashboard and LinkedIn page analytics.

| Column | Type | Required | Notes |
| --- | --- | --- | --- |
| date | date | yes | |
| channel | text | yes | `instagram` or `linkedin` |
| followers | whole number | yes | |

### substack.csv

Unique by `date`. Source: Substack dashboard, Stats page.

| Column | Type | Required | Notes |
| --- | --- | --- | --- |
| date | date | yes | |
| subscribers | whole number | no | Total subscribers. Leave blank on rows that only record a post's open rate |
| open_rate | rate | no | `0.42` means 42% |
| click_rate | rate | no | |

### manychat_clicks.csv

Link clicks from Instagram DM automations. ManyChat is the source of truth for Instagram click-through. Unique by `date` + `keyword`.

| Column | Type | Required | Notes |
| --- | --- | --- | --- |
| date | date | yes | Day, or last day of the period, the clicks were counted for |
| keyword | text | yes | Comment keyword that triggers the flow, such as `AI NEWS` |
| cta_text | text | no | CTA as written in the post |
| link | text | no | Where the link goes |
| clicks | whole number | yes | |

## How the numbers are worked out

- **Newsletter subscribers** is the delivered count on each send. The card shows the latest send in the date range, its change from the send before, and its change across the range.
- **Newsletter open rate and click-through rate** come from reporting periods, using Iterable's Apple MPP filtered opens and filtered unique clicks. The card shows the last period that overlaps the date range, compared with the period before it, in percentage points.
- **Followers and Substack** show the latest entry in the range, its change from the entry before, and its change across the range.
- **CTA ranking** puts newsletter link clicks and ManyChat keyword clicks in one list, sorted by clicks.
- **Instagram comment keywords** are read from captions, such as `Comment "AI NEWS"`. Spelling variants like `AINEWS` count as the same keyword.
- **Carousels vs videos** averages each metric per Instagram feed post. It leaves out Stories, single-image posts and posts with no metrics. One post that travels far can move an average a lot, so the page lists the posts behind it.

## Connectors and settings

Connectors are optional. They fill a table automatically and save through the same path as a CSV upload. Settings come from environment variables. Locally, copy `.env.example` to `.env` and fill in what you use. Never commit `.env`.

| Connector | Fills | Settings |
| --- | --- | --- |
| Buffer | Instagram and LinkedIn posts | `BUFFER_API_KEY`, `BUFFER_ORGANIZATION_ID`, `BUFFER_CHANNEL_IDS` |
| ManyChat (Google Sheet) | ManyChat link clicks | `MANYCHAT_SHEET_CSV_URL` |
| ManyChat API | ManyChat link clicks | `MANYCHAT_API_KEY` (not built yet, see below) |

**Buffer.** Create a key at https://publish.buffer.com/settings/api. Only the Buffer organization owner can create one, and the key can read everything in that organization, so keep it secret. Buffer refreshes post metrics about once a day. Buffer does not provide follower counts, so those are still entered by hand.

**ManyChat through Google Sheets.** In each keyword flow in ManyChat, add a Google Sheets **Add row** action right after the link is clicked. Have it write these columns: `date`, `keyword`, `cta_text`, `link`, `clicks` (put `1` in clicks). In Google Sheets, choose File > Share > Publish to web, pick the sheet, choose CSV, and put the link in `MANYCHAT_SHEET_CSV_URL`. Each pull totals the clicks per day and keyword. Anyone with that link can read the sheet, so log only what the dashboard needs.

## Deploying on Streamlit Community Cloud

1. Push this repo to GitHub. A private repo works.
2. Go to https://share.streamlit.io, choose **Create app**, pick the repo and branch, and set the main file to `app.py`.
3. Under **Advanced settings**, pick Python 3.11 or newer. Paste any settings you use into **Secrets** in TOML format:

   ```toml
   BUFFER_API_KEY = "..."
   BUFFER_ORGANIZATION_ID = "..."
   BUFFER_CHANNEL_IDS = "id1,id2"
   ```

   Streamlit exposes these secrets as environment variables, so the app reads them the same way as `.env`.
4. Deploy, and use the app's sharing settings to choose who can view it.

Community Cloud does not keep files between restarts. Rows saved in the app there are lost when the app restarts or redeploys. For a hosted copy, either pull from connectors each time you open it, or keep your CSVs somewhere durable and upload them. Running locally avoids this.

## Adding the ManyChat API connector

The connector framework is in `content_dashboard/connectors/`. A placeholder, `ManyChatApiConnector`, is already registered and shows on the Update data page as "not built yet". To build it:

1. **Check what the API offers.** ManyChat's API key comes from Settings > API in ManyChat, and the reference is at https://api.manychat.com/swagger. At the time of writing, the public API covers contacts, tags, custom fields and flows, but not link-click statistics. If that is still true, have each flow store clicks somewhere the API can read. For example, increment a custom field per keyword with an action step, then read it back.
2. **Write `fetch()`.** In `content_dashboard/connectors/manychat.py`, fill in `ManyChatApiConnector.fetch(start, end)`. It must return a pandas DataFrame with the `manychat_clicks` columns: `date`, `keyword`, `cta_text`, `link`, `clicks`, `source`. Set `source` to something like `ManyChat API, pulled 2026-10-20`. Raise `ConnectorError` with a plain message for anything the person can fix, such as a wrong key.
3. **Turn it on.** Set `implemented = True` on the class. It reads `MANYCHAT_API_KEY` through `config.env()`. Add any other settings it needs to `required_env` and to `.env.example`.
4. **Test it.** Add a test in `tests/` that mocks the HTTP call, like `tests/test_buffer.py` does, and checks that the rows pass `storage.validate()`.

Nothing else changes. The Update data page lists the connector and saves its rows through `storage.save()`, and every page reads the `manychat_clicks` table as before. The same steps work for any new source, such as a Substack or LinkedIn connector. Subclass `Connector` in `connectors/base.py` and add it to `REGISTRY` in `connectors/__init__.py`.

## Repo layout

```
app.py                      Entry point: sidebar filters and page navigation
content_dashboard/
  config.py                 Paths, channel names, settings from environment variables
  schemas.py                One CSV schema per table
  storage.py                Load, validate and save CSVs
  metrics.py                Every calculation, with no Streamlit code
  components.py             KPI cards, charts and table helpers
  connectors/               Buffer, ManyChat (Google Sheet) and the ManyChat API placeholder
  importers.py              Readers for platform exports, such as the LinkedIn content export
  views/                    One module per page
sample_data/                Made-up sample CSVs, one per table
data/                       Your real CSVs (ignored by git)
tests/                      pytest tests, including a headless run of every page
```

## License

MIT. See `LICENSE`.
