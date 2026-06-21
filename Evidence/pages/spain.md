---
title: Spain
max_width: 1500
---

Spain is a country of roughly 48 million people on the Iberian Peninsula in south-western Europe, with Madrid as its capital and largest city. It is highly regionalised, with strong distinct identities and co-official languages in areas such as Catalonia, the Basque Country and Galicia. Spain is a parliamentary constitutional monarchy: the 350 members of the Congress of Deputies are elected by proportional representation, and the Prime Minister leads the government. Its politics centres on the centre-left PSOE and centre-right PP, alongside Vox, Sumar and Podemos, and a range of influential regional parties.

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
WHERE country = 'Spain'
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
    WHERE country = 'Spain'
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
    WHERE country = 'Spain'
)
ON party
USING MAX(percentage)
GROUP BY country, end_date, pollster, sample_size
ORDER BY end_date DESC
```

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
    WHERE p.country = 'Spain'
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
    WHERE p.country = 'Spain'
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
    WHERE p.country = 'Spain'
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

<Grid cols=1>

<Chart 
    data={moving_avg_scatter} 
    x="end_date" 
    yMin =0 
    title="Polling Trends" 
    chartAreaHeight=500
    series="party"
    seriesColors={{
        "Lab":          "#E4003B",
        "Con":          "#0087DC",
        "Ref":          "#12B6CF",
        "RB":           "#0f0f56",
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

{#if first_vs_latest?.length > 0}
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
        chartAreaHeight=350
        labels=true
        seriesColors={{
            "Last Election":      "#9CA3AF",
            "Latest 10-poll avg": "#1f49b4"
        }}
    />
{:else}
    <em>Loading comparison for Spain…</em>
{/if}

</Grid>

{#if polls_wide?.length > 0}
    <DataTable data={polls_wide} />
{:else}
    <em>Loading data for Spain…</em>
{/if}

---

## Coalitions

See the polling broken down by Government\Opposition, Left\Right blocs, and political spectrum.

<Grid cols=2>

<LineChart
    data={status_breakdown}
    x=end_date
    y=monthly_avg
    series=category
    seriesColors={{
        "Government+Support":       "#169a21",
        "Opposition":          "#c01212",
        "Extra-parliamentary": "#575757"
    }}
    lineWidth=3
    title="Polling share by party status (monthly average)"
    yAxisTitle="Polling %"
    yFmt='0.0"%"'
    chartAreaHeight=325
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
    chartAreaHeight=325
    handleMissing=connect
/>

</Grid>

<AreaChart
    data={spectrum_breakdown}
    x=end_date
    y=monthly_avg
    yMax=100
    series=category
    seriesOrder={['Far-left populist', 'Left-wing populist', 'Left-wing', 'Centre-left', 'Centrist', 'Centre-right', 'Right-wing', 'Right-wing populist', 'Far-right populist']}
    seriesColors={{
        "Far-left populist":       "#7a0000",
        "Left-wing populist":      "#d81a1a",
        "Left-wing":               "#da5757",
        "Centre-left":             "#d37a7a",
        "Centrist":                "#dbca12",
        "Centre-right":            "#8197ce",
        "Right-wing":              "#577bd6",
        "Right-wing populist":     "#194ac4",
        "Far-right populist":      "#022274"
    }}        
    type=stacked
    title="Polling share by political spectrum (monthly average)"
    yAxisTitle="Polling %"
    yFmt='0.0"%"'
    chartAreaHeight=350
    handleMissing=connect>
    <ReferenceLine y=50/>
</AreaChart>

<LastRefreshed/>
