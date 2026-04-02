# NanoBot AI Assistant

Ultra-lightweight personal AI assistant powered by [NanoBot](https://github.com/HKUDS/nanobot), deeply integrated with Home Assistant.

## About

NanoBot is an ultra-lightweight personal AI assistant with full tool-use capabilities. This add-on runs NanoBot inside Home Assistant and connects it to your smart home through multiple integration layers:

- **Smart home awareness** — reads device states, history, automations, and more via 92 HA tools
- **Smart home control** — calls HA services, controls devices, creates automations (opt-in)
- **Voice assistant backend** — becomes the AI brain behind HA Assist / voice commands
- **Reactive automation** — reacts to home events (motion, door open, state changes) in real-time
- **MQTT bridge** — two-way communication with HA automations and IoT devices
- **Proactive agent** — scheduled briefings, energy reports, security alerts

---

## Configuration

### LLM Provider Settings

| Option | Description |
|--------|-------------|
| **LLM Provider** | Provider name: `custom` (any OpenAI-compat endpoint), `openai`, `anthropic`, `openrouter`, etc. |
| **LLM API Key** | API key for the provider |
| **LLM Base URL** | Base URL for the API (required for `custom`). Example: `https://api.openai.com/v1` |
| **LLM Model** | Model name. Examples: `claude-4.5`, `gpt-4o`, `deepseek-chat` |

### Discord Integration

| Option | Description |
|--------|-------------|
| **Enable Discord** | Toggle Discord bot on/off |
| **Discord Bot Token** | Bot token from https://discord.com/developers/applications |
| **Discord Channel ID** | Restrict bot to a specific channel (optional) |
| **Discord Allowed Users** | Comma-separated Discord user IDs, or `*` for all users |
| **Discord Group Policy** | `open` = respond to all messages; `mention` = only when @mentioned |

### Logging

| Option | Description |
|--------|-------------|
| **Log Level** | `trace`, `debug`, `info` (default), `warning`, `error` |

---

## Phase 1: Home Assistant MCP Integration

NanoBot connects to your Home Assistant via the [ha-mcp](https://github.com/homeassistant-ai/ha-mcp) add-on, giving it **92 tools** to read and control the entire smart home.

### Setup

1. **Install the ha-mcp add-on** from https://github.com/homeassistant-ai/ha-mcp and start it.
2. Open the **ha-mcp add-on logs** and copy the MCP server URL (e.g., `http://homeassistant.local:8808/mcp`).
3. In NanoBot's configuration:
   - Set **Enable Home Assistant MCP** to `true`
   - Paste the URL into **HA MCP Server URL**
   - Leave **HA Long-Lived Access Token** blank (ha-mcp handles auth automatically when installed as a local add-on)
   - Leave **HA Read-Only Mode** enabled (default, recommended) — NanoBot can read everything but cannot control devices

### Read-Only vs Full Access

| Mode | What NanoBot can do |
|------|---------------------|
| **Read-Only** (default, `ha_read_only: true`) | Read all entity states, search entities, view history, logbook, statistics, automations, dashboards. Cannot call services or change anything. |
| **Full Access** (`ha_read_only: false`) | All 92 tools including `ha_call_service`, `ha_bulk_control`, `ha_config_set_automation`, `ha_backup_create`, etc. |

To grant full access, set **HA Read-Only Mode** to `false` in the add-on configuration.

### Available Tools (sample)

Once connected, NanoBot can use these tools naturally in conversation:

```
ha_get_overview         — get a full summary of your home
ha_get_state            — get the state of any entity
ha_search_entities      — find entities by name, area, or type
ha_get_history          — get historical state data
ha_call_service         — call any HA service (full-access only)
ha_config_set_automation — create/modify automations (full-access only)
```

### Example Conversations

> "What lights are on in the living room?"  
> "Turn off all lights in the bedroom" (requires full access)  
> "Show me the temperature trend in the kitchen over the last 24 hours"  
> "Create an automation that turns off the living room lights at midnight"

---

## Phase 2: Voice Assistant / HA Conversation Integration

NanoBot can become the AI brain behind HA Assist — handling voice commands with full smart home context.

### Setup

1. Set **Enable OpenAI-Compatible API** to `true` in the NanoBot add-on configuration.
2. In Home Assistant, go to **Settings → Devices & Services → Add Integration**.
3. Search for **OpenAI Conversation** and add it.
4. Configure it with:
   - **API Key**: any non-empty string (e.g., `nanobot`)
   - **Base URL**: `http://<your-ha-ip>:8900/v1`
5. Go to **Settings → Voice Assistants**, create or edit a voice assistant, and set **Conversation agent** to the NanoBot OpenAI integration.

NanoBot will now handle all voice and Assist queries with full HA context via its MCP tools.

---

## Phase 3: HA Event Streaming

NanoBot can react to real-time Home Assistant events: motion detected, doors opened, lights changed, automations triggered, and more.

### Setup

1. Set **Enable HA Event Streaming** to `true`.
2. Optionally configure **HA Event Types** (comma-separated). Default: `state_changed`.
   - Examples: `state_changed,automation_triggered,call_service`
3. Restart the add-on.

### How It Works

NanoBot's event listener connects to HA's WebSocket API and writes event files to:

```
/config/nanobot/workspace/events/<timestamp>-<event_type>.json
```

NanoBot's proactive agent (see Phase 5) watches this directory and reacts according to the instruction files in `/config/nanobot/workspace/instructions/`.

### Event File Format

```json
{
  "timestamp": "2025-04-01T22:05:33+00:00",
  "event_type": "state_changed",
  "summary": "binary_sensor.hallway_motion: off → on",
  "data": {
    "entity_id": "binary_sensor.hallway_motion",
    "new_state": { "state": "on", ... },
    "old_state": { "state": "off", ... }
  }
}
```

---

## Phase 4: MQTT Bidirectional Channel

NanoBot can communicate with HA automations and IoT devices over MQTT.

### Requirements

- The **Mosquitto broker** add-on must be installed and running.
- **Enable OpenAI-Compatible API** (`api_enabled`) must be `true` — the MQTT bridge forwards incoming messages to NanoBot's API server on port 8900.
- Set **Enable MQTT Integration** to `true` in NanoBot configuration.
- NanoBot will auto-detect the Mosquitto broker via HA service discovery.

### MQTT Topics

| Topic | Direction | Description |
|-------|-----------|-------------|
| `nanobot/inbox` | HA → NanoBot | Send a task to NanoBot. Payload: plain text or `{"task": "..."}` |
| `nanobot/outbox` | NanoBot → HA | NanoBot publishes responses/results here |
| `nanobot/status` | NanoBot → HA | `online` when running, `offline` when stopped (retained) |

### HA Automation Examples

**Send a task to NanoBot:**
```yaml
service: mqtt.publish
data:
  topic: nanobot/inbox
  payload: "What lights are on right now?"
```

**React to a NanoBot response:**
```yaml
trigger:
  - platform: mqtt
    topic: nanobot/outbox
action:
  - service: notify.mobile_app_phone
    data:
      message: "{{ trigger.payload }}"
```

**NanoBot publishes to custom topic from workspace:**

NanoBot can publish to any MQTT topic by writing a JSON file to `/config/nanobot/workspace/mqtt_publish/`:
```json
{
  "topic": "home/nanobot/alert",
  "payload": "Motion detected in hallway at 2:34 AM",
  "retain": false
}
```

---

## Phase 5: Proactive Cron Agent

NanoBot can autonomously perform scheduled tasks and react to events using instruction files in the workspace.

### Workspace Instructions Directory

Instruction files are placed in:
```
/config/nanobot/workspace/instructions/
```

On first start, NanoBot installs three example templates:

| File | Purpose |
|------|---------|
| `morning-briefing.md` | Daily 7am home summary sent to Discord |
| `security-watch.md` | Overnight motion/door alerts |
| `energy-monitor.md` | Weekly energy usage report |

Edit these files in HA's **Studio Code Server** or **File Editor** add-on to customize them.

### Creating Custom Instructions

Any `.md` file in the `instructions/` directory is read by the NanoBot agent. Use natural language to describe what you want NanoBot to do. Include cron expressions or trigger conditions.

**Example — Daily Irrigation Check:**
```markdown
# Irrigation Check

Every day at 06:00, check:
1. Use ha_get_state to check weather.home forecast
2. If rain is expected today, use ha_call_service to turn off switch.irrigation_zone1
3. Otherwise, turn it on for 20 minutes

cron: 0 6 * * *
```

---

## Phase 6: HA REST Command Integration (Zero-Code)

HA automations can push tasks directly to NanoBot using the OpenAI-compatible API on port 8900. Requires `api_enabled: true`.

### Configuration (`configuration.yaml`)

```yaml
rest_command:
  ask_nanobot:
    url: "http://localhost:8900/v1/chat/completions"
    method: POST
    content_type: "application/json"
    payload: '{"messages": [{"role": "user", "content": "{{ message }}"}], "stream": false}'
```

### Automation Example

```yaml
automation:
  - alias: "Ask NanoBot when doorbell rings"
    trigger:
      - platform: state
        entity_id: binary_sensor.doorbell
        to: "on"
    action:
      - service: rest_command.ask_nanobot
        data:
          message: "The doorbell just rang. Who might it be and what should I do?"
```

---

## API Access

| Port | Endpoint | Description |
|------|----------|-------------|
| **18790** | `http://<ha-ip>:18790/` | NanoBot Gateway (channels, cron, heartbeat — no HTTP API) |
| **8900** | `http://<ha-ip>:8900/v1` | OpenAI-compatible API (when `api_enabled: true`) |

The gateway on port 18790 manages channels (Discord, etc.), cron jobs, and heartbeat. It does **not** expose any HTTP endpoints.

The OpenAI-compatible API on port 8900 provides `POST /v1/chat/completions`, `GET /v1/models`, and `GET /health`. This is the endpoint used by HA Conversation, MQTT bridge, and REST commands.

---

## Architecture

```
User (voice / dashboard)
        │
        ▼
HA Assist → openai_conversation → NanoBot API :8900
                                        │
                                        ▼
                               NanoBot Agent Loop
                               ├── LLM Provider (external)
                               ├── ha-mcp tools → HA REST API
                               ├── mqtt_* tools → Mosquitto broker
                               ├── filesystem → /config/nanobot/workspace/
                               └── Discord channel → User

HA Event Bus ──WebSocket──→ ha_event_listener.py
                                        │
                                        ▼
                           /config/nanobot/workspace/events/
                                        │
                                  NanoBot cron tick
                                        │
                                Discord alert / HA action

HA Automation ──mqtt.publish──→ nanobot/inbox
                                        │
                                  MQTT Bridge
                                        │
                               NanoBot Gateway :18790
```

---

## Support

- [NanoBot GitHub](https://github.com/HKUDS/nanobot)
- [NanoBot Documentation](https://github.com/HKUDS/nanobot#readme)
- [ha-mcp GitHub](https://github.com/homeassistant-ai/ha-mcp)
