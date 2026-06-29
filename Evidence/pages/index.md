---
title: International Polling Visualiser
max_width: 1500
---

Select a country to view recent polling data, including trends, an election comparison, the poll table, and coalition / spectrum breakdowns.

- [United Kingdom](/united-kingdom)
- [Spain](/spain)
- [Germany](/germany)
- [New Zealand](/new-zealand)

```sql biggest_movers
WITH country_latest AS (
    SELECT country, MAX(end_date) AS latest_date
    FROM international_polling.my_query
    GROUP BY country
),
rolling AS (
    SELECT
        m.country,
        m.party,
        m.end_date,
        cl.latest_date,
        AVG(m.percentage) OVER (
            PARTITION BY m.country, m.party
            ORDER BY m.end_date
            GROUPS BETWEEN 10 PRECEDING AND CURRENT ROW
        ) AS rolling_avg
    FROM international_polling.my_query m
    JOIN country_latest cl USING (country)
),
this_week AS (
    SELECT country, party, rolling_avg AS this_week
    FROM rolling
    WHERE end_date > latest_date - INTERVAL '7 days'
    QUALIFY ROW_NUMBER() OVER (PARTITION BY country, party ORDER BY end_date DESC) = 1
),
last_week AS (
    SELECT country, party, rolling_avg AS last_week
    FROM rolling
    WHERE end_date <= latest_date - INTERVAL '7 days'
    QUALIFY ROW_NUMBER() OVER (PARTITION BY country, party ORDER BY end_date DESC) = 1
)
SELECT
    t.country,
    t.party,
    l.last_week,
    t.this_week,
    t.this_week - l.last_week AS shift,
    ABS(t.this_week - l.last_week) AS abs_shift
FROM this_week t
JOIN last_week l USING (country, party)
QUALIFY ROW_NUMBER() OVER (PARTITION BY t.country ORDER BY ABS(t.this_week - l.last_week) DESC) <= 3
ORDER BY t.country, abs_shift DESC
```

## Biggest movers this week

Parties with the largest change in their 10-poll rolling average versus roughly a week earlier, by country (each country relative to its own latest poll).

{#if biggest_movers?.length > 0}
<DataTable data={biggest_movers} groupBy=country groupType=section subtotals=false sort="abs_shift desc" rowShading=true>
    <Column id=country     title="Country"   />
    <Column id=party       title="Party"     />
    <Column id=last_week   title="Last week" fmt='0.0"%"' align=right />
    <Column id=this_week   title="This week" fmt='0.0"%"' align=right />
    <Column id=shift       title="Change"    contentType=delta fmt='0.0"pp"' downIsGood=false />
</DataTable>
{:else}
<em>Not enough recent polling to compute weekly movers.</em>
{/if}
