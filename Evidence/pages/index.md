---
title: International Polling Visualiser
full_width: true
---

Use the filters below to view recent polling data for the selected country.

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

```sql moving_avg_scatter
SELECT
    country,
    party,
    end_date,
    percentage,
    AVG(percentage) OVER (
        PARTITION BY party
        ORDER BY end_date
        GROUPS BETWEEN 10 PRECEDING AND CURRENT ROW
    ) AS rolling_avg
FROM international_polling.my_query
WHERE country = '${inputs.selected_country.value}'
```

```sql first_vs_latest
WITH ranked AS (
    SELECT
        country,
        party,
        end_date,
        percentage,
        AVG(percentage) OVER (
            PARTITION BY party
            ORDER BY end_date
            GROUPS BETWEEN 10 PRECEDING AND CURRENT ROW
        ) AS rolling_avg,
        ROW_NUMBER() OVER (PARTITION BY party ORDER BY end_date ASC,  pollster ASC)  AS rn_first,
        ROW_NUMBER() OVER (PARTITION BY party ORDER BY end_date DESC, pollster DESC) AS rn_last
    FROM international_polling.my_query
    WHERE country = '${inputs.selected_country.value}'
),
first_poll AS (
    SELECT country, party, percentage AS value, 'Last Election' AS measure
    FROM ranked WHERE rn_first = 1
),
latest_avg AS (
    SELECT country, party, rolling_avg AS value, 'Latest 10-poll avg' AS measure
    FROM ranked WHERE rn_last  = 1
),
sort_keys AS (
    SELECT party, value AS sort_key FROM latest_avg
)
SELECT u.country, u.party, u.measure, u.value, s.sort_key
FROM (SELECT * FROM first_poll UNION ALL SELECT * FROM latest_avg) u
LEFT JOIN sort_keys s ON s.party = u.party
ORDER BY s.sort_key DESC NULLS LAST, u.party, u.measure
```

```sql polls_wide
PIVOT (
    SELECT country, end_date, pollster, sample_size, party, percentage
    FROM international_polling.my_query
    WHERE country = '${inputs.selected_country.value}'
)
ON party
USING MAX(percentage)
GROUP BY country, end_date, pollster, sample_size
ORDER BY end_date DESC
```

<Grid cols=2 gapSize=none>

<Chart 
    data={moving_avg_scatter} 
    x="end_date" 
    yMin =0 
    title="Polling Trends" 
    chartAreaHeight=400
    series="party"
    seriesColors={{
        "Lab":          "#E4003B",
        "Con":          "#0087DC",
        "Ref":          "#12B6CF",
        "LD":           "#FAA61A",
        "Grn":          "#02A95B",
        "SNP":          "#FFF95D",
        "PC":           "#005B54",
        "PP":           "#009FE3",
        "PSOE":         "#E30613",
        "Vox":          "#63BE21",
        "Sumar":        "#E8234A",
        "ERC":          "#F4B301",
        "Junts":        "#00C1B5",
        "EH Bildu":     "#A3C940",
        "PNV":          "#009944",
        "BNG":          "#6BBDE3",
        "CCa":          "#FFD700",
        "UPN":          "#003B8E",
        "Podemos":      "#6A0F8E",
        "SALF":         "#39B54A",
        "Aliança.cat":  "#0055A5",
        "Union":        "#000000",
        "AfD":          "#009EE0",
        "SPD":          "#E3000F",
        "Grüne":        "#64A12D",
        "Linke":        "#BE3075",
        "BSW":          "#8B1A1A",
        "FDP":          "#FFED00",
        "NAT":          "#00529F",
        "LAB":          "#D82A20",
        "GRN":          "#098137",
        "ACT":          "#FFD700",
        "NZF":          "#000000",
        "TPM":          "#8f5a25",
        "TOP":          "#12cfbc"
    }} 
    echartsOptions={{
        tooltip: {
            show: false
        }
    }}
>
    <Line y="rolling_avg" handleMissing=connect lineWidth=3/>
    <Scatter y="percentage" pointSize=5 opacity=0.3 fillColor="grey"/>
</Chart>

{#if first_vs_latest?.length > 0 && first_vs_latest[0]?.country === inputs.selected_country.value}
    <BarChart
        data={first_vs_latest}
        x=party
        y=value
        series=measure
        type=grouped
        sort=false
        title="Last Election vs latest 10-poll rolling average"
        xAxisTitle="Party"
        yAxisTitle="Percentage"
        yFmt='0.0"%"'
        chartAreaHeight=400
        seriesColors={{
            "Last Election":      "#9CA3AF",
            "Latest 10-poll avg": "#1f49b4"
        }}
    />
{:else}
    <em>Loading comparison for {inputs.selected_country.value}…</em>
{/if}

</Grid>

{#if polls_wide?.length > 0 && polls_wide[0]?.country === inputs.selected_country.value}
    <DataTable data={polls_wide} />
{:else}
    <em>Loading data for {inputs.selected_country.value}…</em>
{/if}

<LastRefreshed/>