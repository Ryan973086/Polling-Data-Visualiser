## Welcome to the international polling visualiser

Use the filters below to view recent polling data for the relevant country.

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

<LineChart 
    data={moving_avg_scatter}
    x=end_date
    y=rolling_avg
    yAxisTitle="percentage (%)"
    series=party
    chartAreaHeight=360
/>

```sql scatter_data
select 
    end_date as Date,
    party,
    percentage
from international_polling.my_query
where country = '${inputs.selected_country.value}'
```

<ScatterPlot 
    data={scatter_data}
    x=Date
    y=percentage
    series=party
    pointSize=5
    yMin=0
    chartAreaHeight=360
/>

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
