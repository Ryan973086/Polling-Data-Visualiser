## Welcome to the international polling visualiser

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
        "NZF":          "#000000"
    }} 
    echartsOptions={{
        tooltip: {
            show: false
        }
    }}
>
    <Line y="rolling_avg" />
    <Scatter y="percentage" pointSize=5 opacity=0.3 />
</Chart>

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

<DataTable data={polls_wide} />
