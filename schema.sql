CREATE TABLE polls (
    country     TEXT NOT NULL,
    date        TEXT NOT NULL,
    pollster    TEXT NOT NULL,
    sample_size TEXT,
    party       TEXT NOT NULL,
    percentage  REAL NOT NULL
);
