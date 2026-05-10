---
title: Coalitions
full_width: true
---

Use the filter to view monthly-average polling shares broken down by party status, coalition bloc, and political spectrum for the selected country.

```sql countries
select
    country
from international_polling.my_query
group by 1
```

<Dropdown
    name=selected_country
    data={countries}
    value=country
/>

```sql status_breakdown
WITH joined AS (
    SELECT
        DATE_TRUNC('month', p.end_date) AS month,
        p.end_date,
        p.pollster,
        COALESCE(NULLIF(pa.status, ''), 'Unaligned') AS category,
        p.percentage
    FROM international_polling.my_query p
    LEFT JOIN international_polling.parties pa ON p.party = pa.party
    WHERE p.country = '${inputs.selected_country.value}'
),
poll_totals AS (
    SELECT month, end_date, pollster, category, SUM(percentage) AS poll_total
    FROM joined
    GROUP BY 1, 2, 3, 4
)
SELECT month AS end_date, category, AVG(poll_total) AS monthly_avg
FROM poll_totals
GROUP BY 1, 2
ORDER BY 1, 2
```

```sql coalition_breakdown
WITH joined AS (
    SELECT
        DATE_TRUNC('month', p.end_date) AS month,
        p.end_date,
        p.pollster,
        COALESCE(NULLIF(pa.coalition, ''), 'Unaligned') AS category,
        p.percentage
    FROM international_polling.my_query p
    LEFT JOIN international_polling.parties pa ON p.party = pa.party
    WHERE p.country = '${inputs.selected_country.value}'
),
poll_totals AS (
    SELECT month, end_date, pollster, category, SUM(percentage) AS poll_total
    FROM joined
    GROUP BY 1, 2, 3, 4
)
SELECT month AS end_date, category, AVG(poll_total) AS monthly_avg
FROM poll_totals
GROUP BY 1, 2
ORDER BY 1, 2
```

```sql spectrum_breakdown
WITH joined AS (
    SELECT
        DATE_TRUNC('month', p.end_date) AS month,
        p.end_date,
        p.pollster,
        COALESCE(NULLIF(pa.spectrum, ''), 'Unaligned') AS category,
        p.percentage
    FROM international_polling.my_query p
    LEFT JOIN international_polling.parties pa ON p.party = pa.party
    WHERE p.country = '${inputs.selected_country.value}'
),
poll_totals AS (
    SELECT month, end_date, pollster, category, SUM(percentage) AS poll_total
    FROM joined
    GROUP BY 1, 2, 3, 4
)
SELECT month AS end_date, category, AVG(poll_total) AS monthly_avg
FROM poll_totals
GROUP BY 1, 2
ORDER BY 1, 2
```

<LineChart
    data={status_breakdown}
    x=end_date
    y=monthly_avg
    series=category
    seriesColors={{
        "In government":       "#169a21",
        "Opposition":          "#c01212",
        "Extra-parliamentary": "#575757"
    }}
    lineWidth=3
    title="Polling share by party status (monthly average)"
    yAxisTitle="Polling %"
    yFmt='0.0"%"'
    chartAreaHeight=400
    handleMissing=connect
/>

<LineChart
    data={coalition_breakdown}
    x=end_date
    y=monthly_avg
    series=category
    seriesColors={{
        "Left bloc":       "#dc1010",
        "Right bloc":      "#1f50cc",
        "Unaligned":       "#383838"
    }}    
    lineWidth=3
    title="Polling share by coalition bloc (monthly average)"
    yAxisTitle="Polling %"
    yFmt='0.0"%"'
    chartAreaHeight=400
    handleMissing=connect
/>

<AreaChart
    data={spectrum_breakdown}
    x=end_date
    y=monthly_avg
    series=category
    type=stacked
    title="Polling share by political spectrum (monthly average)"
    yAxisTitle="Polling %"
    yFmt='0.0"%"'
    chartAreaHeight=400
    handleMissing=connect
/>

<LastRefreshed/>
