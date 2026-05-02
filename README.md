# International Polling Data Visualiser

A personal dashboard that pulls voting-intention polls for several countries into one place.

Live Dashboard: https://ryan973086.github.io/Polling-Data-Visualiser/

## Why this project exists

I kept finding myself bouncing between Wikipedia tabs to check the latest UK / Spanish / German / New Zealand polls. Each country's table looks slightly different, the pollsters and parties differ, and there's no easy way to eyeball the trend across releases.

The goal of this project is simple:

1. **Cut down the time I spend looking up polling information** by consolidating it into a single local dashboard with consistent visuals across countries.
2. **Lay the groundwork for additional insight** beyond what raw polling tables offer — see [Future ideas](#future-ideas) below.

## What it does today

- **Country selector** — currently UK, Spain, Germany, and New Zealand.
- **Polling trend chart** — a per-party line chart of a 10-period rolling average, overlaid with grey scatter points showing each individual poll. Lets you see the noise and the signal at the same time.
- **Polls table** — a pivoted table of every poll for the selected country (date, pollster, sample size, then one column per party with the reported percentage).
- **Country-accurate party colours** — each party renders in its own brand colour so charts read naturally regardless of country.

## Tech stack

- **[Evidence.dev](https://evidence.dev)** v40 — the BI / dashboard framework (Svelte under the hood, served by Vite).
- **SQLite** — single-file database, queried directly by the Evidence dashboard.
- **Python ETL** — a small scraper using `requests` + `BeautifulSoup` to pull polling tables from Wikipedia.
- **Node ≥ 18**, **npm ≥ 7**.

## Project layout

```
.
├── Evidence/                 # The dashboard (Evidence.dev project)
│   ├── pages/index.md        # The single dashboard page
│   ├── sources/              # Data source wiring (SQLite connection)
│   └── package.json          # npm scripts live here
├── data/
│   ├── polling_data.db       # The SQLite database (built by the ETL)
│   ├── schema.sql            # `polls` table definition
│   └── queries/              # Reusable SQL (pivot, rolling avg)
├── etl/
│   ├── Polling Dashboard Source Data ETL Script.py
│   └── Wikipedia Pages.txt   # List of source URLs
└── README.md                 # This file
```

## Data pipeline

1. The Python script in [etl/Polling Dashboard Source Data ETL Script.py](etl/Polling%20Dashboard%20Source%20Data%20ETL%20Script.py) reads the source URL list from [etl/Wikipedia Pages.txt](etl/Wikipedia%20Pages.txt).
2. For each country it fetches the Wikipedia "Opinion polling for…" page, locates the polls table, and parses each row.
3. Rows are normalised into a single shape (see [data/schema.sql](data/schema.sql)) — one row per `(country, end_date, pollster, party)` combination — and written to [data/polling_data.db](data/polling_data.db).
4. The same `.db` is mirrored into `Evidence/sources/international_polling/` where the dashboard reads it via the SQLite connector ([Evidence/sources/international_polling/connection.yaml](Evidence/sources/international_polling/connection.yaml)).

The `polls` schema:

| column      | type | notes                                  |
|-------------|------|----------------------------------------|
| country     | TEXT | e.g. "United Kingdom"                  |
| start_date  | DATE | polling-period start                   |
| end_date    | DATE | polling-period end (used as the x-axis)|
| pollster    | TEXT | pollster / publisher                   |
| sample_size | TEXT | kept as text — Wikipedia is messy here |
| party       | TEXT | short code, e.g. `Lab`, `PSOE`, `NAT`  |
| percentage  | REAL | reported voting intention              |

## Running locally

From the repo root:

```bash
# 1. Refresh the database (only when the Wikipedia data is stale)
python "etl/Polling Dashboard Source Data ETL Script.py"

# 2. Install dashboard deps (one-off)
cd Evidence
npm install

# 3. Validate sources
npm run sources

# 4. Start the dev server (opens the dashboard in your browser)
npm run dev
```

Other useful scripts (all run from inside `Evidence/`):

- `npm run build` — production build
- `npm run build:strict` — fail the build on source/query errors
- `npm run preview` — serve the production build locally

## Future ideas

A few directions to push beyond "just show me the polls":

- **Cross-country normalised view** — incumbents on one chart, oppositions on another, regardless of country.
- **Coalition-feasibility tracker** — sum likely-partner parties and check against the seat / vote-share threshold for a majority. Useful for Spain and Germany especially.
- **Pollster house-effect analysis** — for each pollster, the average deviation of their polls from the rolling average. Helps spot consistent leans.
- **Momentum / swing detection** — biggest weekly movers per country, surfaced as a leaderboard.
- **Election-day forecast overlay** — project the current trend forward to the known next-election date and show a fan of plausible outcomes.
- **More countries** — France, Italy, Canada, Australia, US. Each is one URL in `Wikipedia Pages.txt` plus a country config block in the ETL script.

## Notes

- Source data is Wikipedia, so accuracy ultimately depends on the Wikipedia editors maintaining each polling page. Cross-check before quoting numbers.
- `polling_data.db` is a generated artefact. It's currently committed for convenience; treat it as build output rather than source of truth.
- This is a personal project — not designed for outside contributions, and the ETL is opinionated about how it parses each country's table.
