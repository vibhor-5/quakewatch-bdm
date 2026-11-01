# Power BI report

`.pbix` files can only be authored in Power BI Desktop (Windows), so this repo ships the
**model inputs** plus an equivalent standalone dashboard (`dashboard/index.html`).

## Build the report (about 10 minutes)
1. **Get data → Text/CSV**: import every file in `data/exports/` except `import_report.json` and `benchmark.json`.
2. **Model view**: relate `dim_calendar[date]` (one) → `fact_earthquakes[date]` (many). Leave the `agg_*` tables unrelated.
3. **New measure**: paste each measure from [`measures.dax`](measures.dax).
4. **Pages**
   - *Overview* – KPI cards (Total Events, Strong Events, Strong Share, Largest Magnitude), monthly line chart by year.
   - *Time & Place* – hourly and weekday columns from `fact_earthquakes`; bubble map from `agg_hotspots_grid` (`grid_lat`, `grid_lon`, `Grid Events`).
   - *Conditions* – Strong Share by `depth_class`, `mag_type`, `network`; table with event counts as denominators.

| Table | Grain |
|---|---|
| fact_earthquakes | one event |
| dim_calendar | one date |
| agg_hotspots_grid | 2° grid cell and year |
| agg_conditions | condition type, value and year |
| agg_regions | region and year |
| agg_depth_mag_matrix | depth class, magnitude class and year |
