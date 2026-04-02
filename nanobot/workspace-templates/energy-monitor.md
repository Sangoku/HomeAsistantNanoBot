# Energy Monitor

Weekly energy usage report for the household.

## Schedule

Run every Sunday at 09:00.

```
cron: 0 9 * * 0
```

## Steps

1. Use `ha_search_entities` to find all energy-related entities:
   - `sensor.*energy*`, `sensor.*power*`, `sensor.*kwh*`
   - `sensor.*consumption*`, `sensor.*production*`
2. Use `ha_get_statistics` for each entity (period: last 7 days, statistic_type: sum or mean as appropriate).
3. Identify:
   - Top 3 energy consumers this week
   - Total household energy consumption (kWh)
   - Solar production vs consumption (if solar entities exist)
   - Compare to previous week if history is available
4. Use `ha_eval_template` to format currency costs if energy price sensors exist.
5. Write a Markdown energy report to `/config/nanobot/workspace/energy-reports/week-<YYYY-WW>.md`.
6. Send a concise summary via Discord (if configured):
   - "⚡ Weekly energy: X kWh total, top consumer: Living Room TV (Y kWh)"

## Notes

- Skip entities that have no data or are unavailable.
- Round all values to 2 decimal places.
- If no energy entities are found, write a note explaining how to set up energy monitoring in HA.
