# NanoBot AI Assistant

Your personal AI brain for Home Assistant — ask questions, control devices, get briefings, all by voice, Discord, or MQTT.

---

## Getting Started

### 1. Configure your LLM

NanoBot needs an LLM backend. Any OpenAI-compatible provider works.

| Option | Example |
|---|---|
| **LLM Provider** | `custom` |
| **LLM API Key** | `sk-abc123...` |
| **LLM Base URL** | `https://api.openai.com/v1` |
| **LLM Model** | `gpt-4o`, `claude-4.5`, `deepseek-chat` |

### 2. Connect to your smart home

Install the [ha-mcp](https://github.com/homeassistant-ai/ha-mcp) add-on, then:

1. Start ha-mcp and copy the **MCP Server URL** from its logs
2. In NanoBot settings, enable **Enable Home Assistant MCP**
3. Paste the URL into **HA MCP Server URL**
4. Leave **HA Read-Only Mode** enabled (recommended)

NanoBot now has 38+ tools to query your entire smart home — states, history, areas, automations, devices, and more.

### 3. Enable voice control (optional)

1. Enable **Enable OpenAI-Compatible API**
2. Enable **Auto-register as Conversation Agent**
3. Restart the add-on

NanoBot automatically registers itself as the conversation agent in HA Assist. No manual integration setup needed — just talk to your home.

---

## Capabilities

### Smart Home Awareness

With HA MCP connected, NanoBot can naturally answer questions about your home:

> "What's the temperature in the living room?"
>
> "Which lights are on?"
>
> "Show me the energy usage for the last 24 hours"
>
> "Are there any pending updates?"

### Smart Home Control

Set **HA Read-Only Mode** to `false` to let NanoBot control your home:

> "Turn off all lights in the bedroom"
>
> "Set the thermostat to 22 degrees"
>
> "Create an automation that turns on the porch light at sunset"

| Mode | What NanoBot can do |
|---|---|
| **Read-Only** (default) | Read states, search entities, view history, logbook, statistics, automations, dashboards |
| **Full Access** | Everything above, plus call services, control devices, create/modify automations |

### Voice Assistant

When enabled, NanoBot serves as the AI brain behind HA Assist. It handles voice commands with full smart home context through its MCP tools.

**Automatic setup:** Enable the API + auto conversation agent checkboxes. Done.

**Manual setup:** Add the `OpenAI Conversation` integration in HA, point it at `http://<ha-ip>:8900/v1` with any API key.

### Discord Bot

Enable Discord to chat with your smart home from anywhere:

| Option | Description |
|---|---|
| **Discord Bot Token** | From [Discord Developer Portal](https://discord.com/developers/applications) |
| **Discord Channel ID** | Restrict to a channel (leave empty for all) |
| **Discord Allowed Users** | Comma-separated user IDs, or `*` for all |
| **Discord Group Policy** | `open` = all messages, `mention` = only @mentions |

### MQTT Bridge

Enable MQTT for two-way communication with HA automations and IoT devices.

**Prerequisites:** Mosquitto broker add-on + **Enable OpenAI-Compatible API** must both be active.

| Topic | Direction | Description |
|---|---|---|
| `nanobot/inbox` | HA -> NanoBot | Send a task. Payload: plain text or `{"task": "..."}` |
| `nanobot/outbox` | NanoBot -> HA | Responses published here automatically |
| `nanobot/status` | NanoBot -> HA | `online` / `offline` (retained) |

**Send a task from an automation:**
```yaml
service: mqtt.publish
data:
  topic: nanobot/inbox
  payload: "What lights are on right now?"
```

**React to NanoBot's response:**
```yaml
trigger:
  - platform: mqtt
    topic: nanobot/outbox
action:
  - service: notify.mobile_app_phone
    data:
      message: "{{ trigger.payload }}"
```

### Event Reactions

Enable **HA Event Streaming** to make NanoBot react to real-time home events.

Events are written to `/config/nanobot/workspace/events/` as JSON files. NanoBot's proactive agent watches this directory and acts based on your instruction files.

**Configure:** Set **HA Event Types** to a comma-separated list (default: `state_changed`).

### Proactive Agent

NanoBot ships with example instruction files in `/config/nanobot/workspace/instructions/`:

| Template | What it does |
|---|---|
| `morning-briefing.md` | Daily 7am home summary |
| `security-watch.md` | Overnight motion/door alerts |
| `energy-monitor.md` | Weekly energy usage report |

Edit them with the **File Editor** or **Studio Code Server** add-on. Write your own in natural language — just describe what you want NanoBot to do and include a cron expression.

### REST API

Any HA automation can talk to NanoBot via REST:

```yaml
rest_command:
  ask_nanobot:
    url: "http://localhost:8900/v1/chat/completions"
    method: POST
    content_type: "application/json"
    payload: '{"messages": [{"role": "user", "content": "{{ message }}"}], "stream": false}'
```

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
          message: "The doorbell just rang. What should I do?"
```

---

## All Options

| Option | Default | Description |
|---|---|---|
| **LLM Provider** | `custom` | Provider name (`custom`, `openai`, `anthropic`, `openrouter`) |
| **LLM API Key** | | API key for the provider |
| **LLM Base URL** | | Base URL for the API endpoint |
| **LLM Model** | `claude-4.5` | Model name |
| **Enable Discord** | `false` | Start the Discord bot |
| **Discord Bot Token** | | Bot token |
| **Discord Channel ID** | | Restrict to a channel |
| **Discord Allowed Users** | `*` | Allowed user IDs |
| **Discord Group Policy** | `open` | `open` or `mention` |
| **Log Level** | `info` | `trace`, `debug`, `info`, `warning`, `error` |
| **Enable HA MCP** | `false` | Connect to ha-mcp for smart home tools |
| **HA MCP URL** | | MCP server URL from ha-mcp logs |
| **HA Access Token** | | Long-Lived Access Token (only for remote HA) |
| **HA Read-Only** | `true` | Restrict to read-only tools |
| **Enable API** | `false` | OpenAI-compatible API on port 8900 |
| **Auto Conversation Agent** | `false` | Auto-register as HA voice assistant |
| **Enable Event Streaming** | `false` | Subscribe to HA event bus |
| **Event Types** | `state_changed` | Comma-separated event types |
| **Enable MQTT** | `false` | MQTT bridge (requires Mosquitto) |

## Ports

| Port | Service |
|---|---|
| **8900** | OpenAI-compatible API (`/v1/chat/completions`, `/v1/models`, `/health`) |
| **18790** | NanoBot Gateway (channels, cron, heartbeat — internal, no HTTP API) |

---

## Support

- [NanoBot](https://github.com/HKUDS/nanobot) — upstream project
- [ha-mcp](https://github.com/homeassistant-ai/ha-mcp) — Home Assistant MCP server
