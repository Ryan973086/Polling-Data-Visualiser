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

```sql all_polling_data
select *
from international_polling.my_query
where country = '${inputs.selected_country.value}'
```

<DataTable data={all_polling_data} />