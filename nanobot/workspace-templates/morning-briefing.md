# Morning Briefing

Every day at 07:00, perform a morning briefing for the household.

## Steps

1. Use `ha_get_overview` to get a summary of the current home state.
2. Use `ha_get_states` to find all weather sensor entities (look for `sensor.*temperature*`, `sensor.*humidity*`, `weather.*`).
3. Use `ha_get_calendar_events` to retrieve today's calendar events (if any calendar entities exist).
4. Use `ha_get_history` (last 8 hours) to identify any unusual activity overnight (doors opened, motion triggered, lights left on).
5. Check for any pending HA updates via `ha_get_updates`.
6. Compose a friendly, concise briefing covering:
   - Current indoor/outdoor temperature and weather
   - Today's calendar events
   - Any alerts from overnight (lights left on, doors left open, motion events)
   - Pending HA updates if any
7. Send the briefing as a message via Discord (if Discord is configured) using the `send_message` tool.
   Otherwise, write the briefing to `/config/nanobot/workspace/briefings/morning-<date>.md`.

## Schedule

Run this at 07:00 every day.

```
cron: 0 7 * * *
```
