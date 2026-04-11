CREATE TABLE polls (
    country     TEXT NOT NULL,
    start_date  DATE,
    end_date    DATE,
    pollster    TEXT NOT NULL,
    sample_size TEXT,
    party       TEXT NOT NULL,
    percentage  REAL NOT NULL
);
