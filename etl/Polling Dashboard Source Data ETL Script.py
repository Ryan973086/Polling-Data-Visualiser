#Polling Dashboard Source Data ETL Script

import re
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

import requests
import pandas as pd
from bs4 import BeautifulSoup, Tag

# --- Configuration ---

URLS_FILE = "etl/Wikipedia Pages.txt"
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_FILES = [
    DATA_DIR / "polling_data.db",
    PROJECT_ROOT / "Evidence" / "sources" / "international_polling" / "polling_data.db",
]
SCHEMA_FILE = DATA_DIR / "schema.sql"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

COUNTRY_CONFIGS = {
    "United_Kingdom": {
        "url_match": "United_Kingdom",
        "country_name": "United Kingdom",
        "section_id": "National_poll_results",
        "stop_ids": ["Seat_projections"],
        "exclude_ids": [],
        "meta_columns": ["date(s)conducted", "pollster", "samplesize"],
        "skip_columns": ["client", "area", "lead", "others"],
    },
    "Spain": {
        "url_match": "Spanish",
        "country_name": "Spain",
        "section_id": "Nationwide_polling",
        "stop_ids": ["Sub-national_polling"],
        "exclude_ids": ["Voting_preferences", "Hypothetical_scenarios"],
        "meta_columns": ["pollingfirm/commissioner", "fieldworkdate", "samplesize"],
        "skip_columns": ["turnout", "lead"],
    },
    "Germany": {
        "url_match": "German",
        "country_name": "Germany",
        "section_id": "Poll_results",
        "stop_ids": ["By_state"],
        "exclude_ids": ["CDU_and_CSU", "Scenario_polls"],
        "meta_columns": ["pollingfirm", "fieldworkdate", "samplesize"],
        "skip_columns": ["abs.", "lead", "others"],
    },
    "New_Zealand": {
        "url_match": "New_Zealand",
        "country_name": "New Zealand",
        "section_id": "Table_of_polls",
        "stop_ids": ["Preferred_prime_minister"],
        "exclude_ids": [],
        "meta_columns": ["date", "pollingorganisation", "samplesize"],
        "skip_columns": ["lead", "others"],
    },
}

# Normalise a header string for matching against config keys
def normalise_header(text):
    return re.sub(r'[^a-z0-9/.]', '', text.lower())


def get_config_for_url(url):
    """Return the country config matching the given URL."""
    for cfg in COUNTRY_CONFIGS.values():
        if cfg["url_match"] in url:
            return cfg
    return None


def fetch_html(url):
    """Fetch a Wikipedia page and return its HTML."""
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    return resp.text


def find_heading_by_id(soup, heading_id):
    """Find a heading element by its id or by a child span's id."""
    # Check id directly on heading elements
    heading = soup.find(["h2", "h3", "h4", "h5"], id=heading_id)
    if heading:
        return heading
    # Check span with mw-headline class
    span = soup.find("span", id=heading_id)
    if span:
        return span.find_parent(["h2", "h3", "h4", "h5"])
    return None


def get_heading_id(element):
    """Extract the id from a heading element, checking the element and child spans."""
    if not isinstance(element, Tag):
        return ""
    heading = None
    if element.name in ("h2", "h3"):
        heading = element
    elif element.name == "div" and "mw-heading" in element.get("class", []):
        heading = element.find(["h2", "h3", "h4", "h5"])
    if not heading:
        return ""
    hid = heading.get("id", "")
    if not hid:
        span = heading.find("span", class_="mw-headline")
        hid = span.get("id", "") if span else ""
    return hid


def get_heading_level(element):
    """Get heading level (2 or 3) from a heading or mw-heading div."""
    if element.name in ("h2", "h3"):
        return int(element.name[1])
    if element.name == "div" and "mw-heading" in element.get("class", []):
        h = element.find(["h2", "h3", "h4", "h5"])
        if h:
            return int(h.name[1])
    return 0


def find_national_tables(soup, config):
    """Find all wikitable elements in the national polling section.

    Uses find_all_next() instead of sibling traversal to handle
    Wikipedia's HTML where void elements cause incorrect nesting.
    """
    section_heading = find_heading_by_id(soup, config["section_id"])
    if section_heading is None:
        print(f"  WARNING: Could not find section '{config['section_id']}'")
        return []

    # Determine the level of our starting section
    start_level = get_heading_level(section_heading)
    if section_heading.parent and "mw-heading" in section_heading.parent.get("class", []):
        section_heading = section_heading.parent

    # Find all tables and headings after our section heading
    tables = []
    in_excluded = False
    excluded_level = 0

    for element in section_heading.find_all_next(["table", "h2", "h3", "h4", "h5", "div"]):
        if not isinstance(element, Tag):
            continue

        # Check if it's a heading
        hid = get_heading_id(element)
        hlevel = get_heading_level(element)

        if hlevel > 0:
            # Stop if we hit a stop section
            if hid in config["stop_ids"]:
                break
            # Stop if we hit a same-or-higher-level heading that's not a sub-section
            if hlevel <= start_level and hid != config["section_id"]:
                break
            # Handle excluded sub-sections
            if hid in config["exclude_ids"]:
                in_excluded = True
                excluded_level = hlevel
            elif in_excluded:
                # Exit exclusion when we hit a heading at the same or higher level
                if hlevel <= excluded_level and hid not in config["exclude_ids"]:
                    in_excluded = False
            continue

        # Collect wikitables not in excluded sub-sections
        if element.name == "table" and "wikitable" in element.get("class", []) and not in_excluded:
            tables.append(element)

    return tables


def extract_header_name(th):
    """Extract a meaningful name from a header cell.

    Checks: text content -> title attribute -> alt attribute on child img.
    """
    # Check for title attribute on images first (Spain uses this)
    img = th.find("img")
    if img:
        alt = img.get("alt", "").strip()
        if alt:
            return alt
    # Check title attribute on links
    a_tag = th.find("a")
    if a_tag and a_tag.get("title"):
        title = a_tag["title"].strip()
        # Use title only if the visible text is very short (abbreviation)
        text = th.get_text(strip=True)
        if len(text) <= 6 and title:
            return text  # Keep the abbreviation as the column name
    # Fall back to text
    text = th.get_text(strip=True)
    # Also check th's own title attribute
    if not text and th.get("title"):
        text = th["title"].strip()
    return text


def parse_cell_value(td, is_spain=False):
    """Extract the text value from a data cell.

    For Spain, only take text before <br/> to exclude seat projections.
    Strips footnote references and % signs.
    """
    if is_spain:
        # Get text before first <br> tag
        br = td.find("br")
        if br:
            # Collect text from elements before the <br>
            parts = []
            for child in td.children:
                if child == br:
                    break
                if isinstance(child, Tag):
                    if child.name == "sup":
                        continue
                    parts.append(child.get_text())
                else:
                    parts.append(str(child))
            text = "".join(parts).strip()
        else:
            # Remove footnote sup elements before extracting text
            td_copy = td.__copy__()
            for sup in td_copy.find_all("sup"):
                sup.decompose()
            text = td_copy.get_text(" ", strip=True)
    else:
        # Remove footnote sup elements before extracting text
        td_copy = td.__copy__()
        for sup in td_copy.find_all("sup"):
            sup.decompose()
        text = td_copy.get_text(" ", strip=True)

    # Strip any remaining bracket references
    text = re.sub(r'\[[a-z0-9 ]+\]', '', text)
    # Strip % signs
    text = text.replace('%', '').strip()
    # Normalise whitespace
    text = text.replace('\xa0', ' ')
    text = re.sub(r'\s+', ' ', text).strip()
    # Fix spaces around dashes in date ranges (e.g., "18– 20" -> "18–20")
    text = re.sub(r'\s*–\s*', '–', text)

    return text


def extract_table_data(table, config):
    """Parse a wikitable and return a list of dicts (rows)."""
    rows = table.find_all("tr")
    if not rows:
        return []

    # --- Parse headers ---
    # Handle multi-row headers (rowspan)
    header_rows = []
    for row in rows:
        ths = row.find_all("th")
        if ths and not row.find("td"):
            header_rows.append(row)
        else:
            break

    if not header_rows:
        return []

    # Determine number of columns from the first data row or header spans
    # Build a column map: col_index -> header_name
    # First, figure out total columns
    max_cols = 0
    for row in rows:
        cells = row.find_all(["th", "td"])
        col_count = sum(int(c.get("colspan", 1)) for c in cells)
        max_cols = max(max_cols, col_count)

    # Build header grid
    header_grid = [[""] * max_cols for _ in range(len(header_rows))]
    for r_idx, row in enumerate(header_rows):
        col_ptr = 0
        for th in row.find_all("th"):
            # Skip to next unfilled position
            while col_ptr < max_cols and header_grid[r_idx][col_ptr] != "":
                col_ptr += 1
            if col_ptr >= max_cols:
                break

            name = extract_header_name(th)
            colspan = int(th.get("colspan", 1))
            rowspan = int(th.get("rowspan", 1))

            for dr in range(rowspan):
                for dc in range(colspan):
                    r, c = r_idx + dr, col_ptr + dc
                    if r < len(header_grid) and c < max_cols:
                        if header_grid[r][c] == "":
                            header_grid[r][c] = name
            col_ptr += colspan

    # Use the last non-empty value in each column as the header
    headers = []
    for col in range(max_cols):
        name = ""
        for r in range(len(header_rows)):
            if header_grid[r][col]:
                name = header_grid[r][col]
        headers.append(name)

    # --- Classify columns ---
    meta_keys = config["meta_columns"]
    skip_keys = config["skip_columns"]
    is_spain = config["country_name"] == "Spain"

    def matches_key(norm, key):
        """Check if a normalised header matches a config key."""
        norm_key = normalise_header(key)
        if norm == norm_key:
            return True
        # Allow startswith matching only for keys >= 4 chars to avoid false positives
        if len(norm_key) >= 4 and norm.startswith(norm_key):
            return True
        if len(norm) >= 4 and norm_key.startswith(norm):
            return True
        return False

    col_roles = {}  # col_index -> ("meta", standard_name) or ("party", party_name) or ("skip", _)
    for i, h in enumerate(headers):
        norm = normalise_header(h)
        matched = False
        for mk in meta_keys:
            if matches_key(norm, mk):
                # Map to standard names
                if "date" in mk:
                    col_roles[i] = ("meta", "Date")
                elif "pollster" in mk or "pollingfirm" in mk or "pollingorganisation" in mk:
                    col_roles[i] = ("meta", "Pollster")
                elif "sample" in mk:
                    col_roles[i] = ("meta", "Sample Size")
                matched = True
                break
        if not matched:
            skip = False
            for sk in skip_keys:
                if matches_key(norm, sk):
                    skip = True
                    break
            if skip or not h:
                col_roles[i] = ("skip", "")
            else:
                col_roles[i] = ("party", h)

    # --- Parse data rows ---
    data_rows = []
    data_start = len(header_rows)

    # Track rowspan carry-overs for data cells
    rowspan_carry = {}  # col_index -> (value, remaining_rows)

    for row in rows[data_start:]:
        cells = row.find_all(["th", "td"])

        # Skip annotation rows (colspan spanning most of the table)
        if len(cells) <= 3:
            for cell in cells:
                if int(cell.get("colspan", 1)) > 3:
                    # Clear any rowspan state since this row is an interruption
                    continue
            if any(int(c.get("colspan", 1)) > 3 for c in cells):
                continue

        # Skip rows that are sub-headers (all th, no td)
        if all(c.name == "th" for c in cells):
            # Could be an "election result" reference row - skip
            continue

        # Build cell values considering rowspan carry-overs
        cell_values = {}
        col_ptr = 0
        cell_idx = 0

        while col_ptr < max_cols:
            # Check for rowspan carry-over
            if col_ptr in rowspan_carry:
                val, remaining = rowspan_carry[col_ptr]
                cell_values[col_ptr] = val
                if remaining <= 1:
                    del rowspan_carry[col_ptr]
                else:
                    rowspan_carry[col_ptr] = (val, remaining - 1)
                col_ptr += 1
                continue

            if cell_idx >= len(cells):
                col_ptr += 1
                continue

            cell = cells[cell_idx]
            colspan = int(cell.get("colspan", 1))
            rowspan = int(cell.get("rowspan", 1))

            value = parse_cell_value(cell, is_spain=is_spain)

            for dc in range(colspan):
                c = col_ptr + dc
                if c < max_cols:
                    cell_values[c] = value

            # Register rowspan carry-over
            if rowspan > 1:
                for dc in range(colspan):
                    c = col_ptr + dc
                    if c < max_cols:
                        rowspan_carry[c] = (value, rowspan - 1)

            col_ptr += colspan
            cell_idx += 1

        # Build row dict
        row_dict = {}
        has_any_party = False
        for col_idx, role in col_roles.items():
            val = cell_values.get(col_idx, "")
            if role[0] == "meta":
                row_dict[role[1]] = val
            elif role[0] == "party":
                row_dict[role[1]] = val
                if val and val not in ("–", "—", "-", "?", "N/A", ""):
                    has_any_party = True

        # Only add rows that have at least some party data
        if has_any_party and "Date" in row_dict:
            data_rows.append(row_dict)

    return data_rows


def get_year_from_heading(table):
    """Try to find a year from the heading preceding this table.

    Uses find_previous to traverse the full document tree backwards,
    not just siblings, since Wikipedia's HTML can nest tables under
    different parent elements than the headings.
    """
    for heading in table.find_all_previous(["h2", "h3", "h4", "h5"]):
        text = heading.get_text()
        match = re.search(r'(20\d{2})', text)
        if match:
            return match.group(1)
    return None


def parse_date_range(date_str):
    """Parse a date string into (start_date, end_date) as ISO format strings.

    Returns (None, end_iso) for single dates.
    Returns (start_iso, end_iso) for date ranges.
    Returns (None, None) if parsing fails.
    """
    if not date_str or not date_str.strip():
        return None, None

    date_str = date_str.strip()
    EN_DASH = '\u2013'

    # Require a year for parsing
    if not re.search(r'20\d{2}', date_str):
        return None, None

    if EN_DASH in date_str:
        parts = date_str.split(EN_DASH, 1)
        start_part = parts[0].strip()
        end_part = parts[1].strip()

        # Parse end date (always has the year)
        try:
            end_date = datetime.strptime(end_part, '%d %b %Y').date()
        except ValueError:
            return None, None

        start_tokens = start_part.split()

        if len(start_tokens) == 1:
            # Just a day number: "6" in "6–7 Apr 2025"
            try:
                start_date = end_date.replace(day=int(start_tokens[0]))
            except (ValueError, TypeError):
                return None, None

        elif len(start_tokens) == 2:
            # Day + month: "27 Mar" in "27 Mar–1 Apr 2025"
            try:
                candidate = datetime.strptime(
                    f'{start_tokens[0]} {start_tokens[1]} {end_date.year}',
                    '%d %b %Y',
                ).date()
            except ValueError:
                return None, None
            # Cross-year: if start > end, start must be previous year
            if candidate > end_date:
                candidate = candidate.replace(year=candidate.year - 1)
            start_date = candidate

        elif len(start_tokens) == 3:
            # Full date: "23 Dec 2025"
            try:
                start_date = datetime.strptime(start_part, '%d %b %Y').date()
            except ValueError:
                return None, None
        else:
            return None, None

        return start_date.isoformat(), end_date.isoformat()

    else:
        # Single date
        try:
            single = datetime.strptime(date_str, '%d %b %Y').date()
            return None, single.isoformat()
        except ValueError:
            return None, None


def process_url(url):
    """Fetch, parse, and extract polling data from a single Wikipedia URL."""
    config = get_config_for_url(url)
    if config is None:
        print(f"WARNING: No config found for URL: {url}")
        return pd.DataFrame()

    country = config["country_name"]
    print(f"Processing {country}...")

    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    tables = find_national_tables(soup, config)
    print(f"  Found {len(tables)} national polling table(s)")

    all_rows = []
    for table in tables:
        year = get_year_from_heading(table)
        rows = extract_table_data(table, config)
        # Prepend year to dates if missing
        if year and rows:
            for row in rows:
                date_val = row.get("Date", "")
                if date_val and not re.search(r'20\d{2}', date_val):
                    row["Date"] = f"{date_val} {year}"
        all_rows.extend(rows)

    if not all_rows:
        print(f"  WARNING: No data extracted for {country}")
        return pd.DataFrame()

    # Parse dates into start/end columns
    for row in all_rows:
        date_val = row.pop("Date", "")
        start_date, end_date = parse_date_range(date_val)
        row["Start Date"] = start_date
        row["End Date"] = end_date

    print(f"  Extracted {len(all_rows)} polling rows")

    # Build wide DataFrame
    df = pd.DataFrame(all_rows)

    # Identify party columns (everything that isn't a meta column)
    meta_cols = ["Start Date", "End Date", "Pollster", "Sample Size"]
    party_cols = [c for c in df.columns if c not in meta_cols]

    # Add country
    df["Country"] = country

    # Melt to long format
    id_vars = ["Country"] + [c for c in meta_cols if c in df.columns]
    df_long = df.melt(
        id_vars=id_vars,
        value_vars=party_cols,
        var_name="Party",
        value_name="Percentage",
    )

    # Clean percentage values
    df_long["Percentage"] = df_long["Percentage"].replace(
        {"–": None, "—": None, "-": None, "?": None, "N/A": None, "Tie": None, "": None}
    )
    df_long["Percentage"] = pd.to_numeric(df_long["Percentage"], errors="coerce")

    # Drop rows with no percentage
    df_long = df_long.dropna(subset=["Percentage"])

    return df_long


def main():
    # Read URLs
    with open(URLS_FILE, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    print(f"Found {len(urls)} URLs to process\n")

    all_data = []
    for url in urls:
        try:
            df = process_url(url)
            if not df.empty:
                all_data.append(df)
        except Exception as e:
            print(f"  ERROR processing {url}: {e}")
        print()

    if not all_data:
        print("ERROR: No data extracted from any URL")
        return

    # Combine all data
    result = pd.concat(all_data, ignore_index=True)

    # Reorder columns
    col_order = ["Country", "Start Date", "End Date", "Pollster", "Sample Size", "Party", "Percentage"]
    result = result[[c for c in col_order if c in result.columns]]

    # Rename columns to snake_case for SQL-friendly names
    result = result.rename(columns={
        "Country": "country",
        "Start Date": "start_date",
        "End Date": "end_date",
        "Pollster": "pollster",
        "Sample Size": "sample_size",
        "Party": "party",
        "Percentage": "percentage",
    })

    # Write output to SQLite
    schema_sql = """CREATE TABLE polls (
    country     TEXT NOT NULL,
    start_date  DATE,
    end_date    DATE,
    pollster    TEXT NOT NULL,
    sample_size TEXT,
    party       TEXT NOT NULL,
    percentage  REAL NOT NULL
);"""

    primary_db, *secondary_dbs = OUTPUT_FILES
    if primary_db.exists():
        primary_db.unlink()
    conn = sqlite3.connect(primary_db)
    conn.execute(schema_sql)
    result.to_sql("polls", conn, if_exists="append", index=False)
    conn.close()

    for secondary_db in secondary_dbs:
        shutil.copyfile(primary_db, secondary_db)

    # Export schema for version control
    with open(SCHEMA_FILE, "w", encoding="utf-8") as f:
        f.write(schema_sql + "\n")

    for output_file in OUTPUT_FILES:
        print(f"Written {len(result)} rows to {output_file}")
    print(f"Schema exported to {SCHEMA_FILE}")
    print(f"\nRows per country:")
    print(result.groupby("country").size().to_string())


if __name__ == "__main__":
    main()
