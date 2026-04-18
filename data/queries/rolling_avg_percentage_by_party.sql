SELECT
    country,
    party,
    end_date,
    percentage,
    AVG(percentage) OVER (
        PARTITION BY country, party
        ORDER BY end_date
        GROUPS BETWEEN 4 PRECEDING AND CURRENT ROW
    ) AS rolling_avg
FROM polls
ORDER BY country, party, end_date;
