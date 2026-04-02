# Security Watch

Monitor the home for security events overnight and send alerts.

## Trigger

Watch for event files in `/config/nanobot/workspace/events/` where:
- `event_type` is `state_changed`
- `data.entity_id` matches `binary_sensor.*motion*`, `binary_sensor.*door*`, or `binary_sensor.*window*`
- `data.new_state.state` is `"on"` (motion/contact opened)
- The event timestamp is between 23:00 and 07:00

## Steps

1. Read the event file and extract entity_id, new state, old state, and timestamp.
2. Use `ha_get_state` to confirm current state and get the friendly name.
3. Use `ha_get_history` on the entity (last 15 minutes) to check if this is a sustained change or a brief trigger.
4. If this appears to be a genuine security event:
   - Compose an alert message: e.g., "🚨 Motion detected in Hallway at 02:34 AM"
   - Send alert via Discord (if configured).
   - Optionally write a log entry to `/config/nanobot/workspace/security-log.md`.
5. After processing, delete the event file (or move it to `/config/nanobot/workspace/events/processed/`).

## Notes

- Do NOT trigger on entities that normally change at night (e.g., scheduled lights, regular automations).
- Only alert if the state changed to `"on"` — ignore `"off"` transitions.
- Avoid sending more than one alert per entity per 30-minute window (check security-log.md).
