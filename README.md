# NanoBot AI Assistant for Home Assistant

<p align="center">
  <img src="nanobot/logo.svg" alt="NanoBot" width="180" />
</p>

<p align="center">
  <strong>Your personal AI brain for Home Assistant.</strong><br>
  Ask questions. Control devices. Get briefings. All by voice, Discord, or MQTT.
</p>

<p align="center">
  <a href="#installation">Install</a> &bull;
  <a href="#what-can-it-do">Features</a> &bull;
  <a href="#configuration">Configure</a> &bull;
  <a href="#development">Develop</a>
</p>

---

## What is this?

NanoBot is an ultra-lightweight AI assistant that runs **inside** Home Assistant as an add-on. It connects to any OpenAI-compatible LLM (Claude, GPT, DeepSeek, local Ollama, etc.) and gives it full awareness and control of your smart home.

Unlike simple chatbots, NanoBot has **tool-use capabilities** — it can read sensor states, call services, search entity history, create automations, and react to events autonomously.

## What can it do?

| Capability | Description |
|---|---|
| **Smart Home Awareness** | Reads all entity states, history, automations, areas, and devices via 38+ read-only HA tools |
| **Smart Home Control** | Calls services, controls devices, creates automations (opt-in, disabled by default) |
| **Voice Assistant** | Becomes the AI brain behind HA Assist — auto-registers as conversation agent with one checkbox |
| **Discord Bot** | Full Discord integration — chat with your home from anywhere |
| **MQTT Bridge** | Two-way messaging with HA automations and IoT devices via `nanobot/inbox` and `nanobot/outbox` |
| **Event Reactions** | Subscribes to HA event bus — reacts to motion, doors, state changes in real-time |
| **Proactive Agent** | Scheduled morning briefings, security alerts, energy reports via cron |
| **REST API** | OpenAI-compatible `/v1/chat/completions` endpoint for any integration |

## Example Conversations

> "What's the temperature in the living room?"
>
> "Are any lights on right now?"
>
> "Turn off all lights in the bedroom" *(requires full-access mode)*
>
> "Show me the energy usage trend for the last week"
>
> "Create an automation that turns on the porch light at sunset"

---

## Installation

### As a Home Assistant Add-on

1. In Home Assistant, go to **Settings -> Add-ons -> Add-on Store**
2. Click the three dots (top right) -> **Repositories**
3. Paste the URL of this repository and click **Add**
4. Find **NanoBot AI Assistant** in the store and click **Install**
5. Configure your LLM provider (API key + base URL) in the add-on settings
6. Click **Start**

### Prerequisites

| Requirement | Purpose |
|---|---|
| An LLM API key | Any OpenAI-compatible provider (OpenAI, Anthropic, OpenRouter, local Ollama, etc.) |
| [ha-mcp add-on](https://github.com/homeassistant-ai/ha-mcp) | Gives NanoBot tools to read/control your smart home (optional but recommended) |
| [Mosquitto broker add-on](https://github.com/home-assistant/addons/tree/master/mosquitto) | Required only for MQTT integration (optional) |

---

## Configuration

### Quick Start (Minimum)

| Option | Value |
|---|---|
| **LLM Provider** | `custom` |
| **LLM API Key** | Your API key |
| **LLM Base URL** | Your provider's URL (e.g., `https://api.openai.com/v1`) |
| **LLM Model** | Model name (e.g., `claude-4.5`, `gpt-4o`) |

### Smart Home Integration

| Option | Default | Description |
|---|---|---|
| **Enable HA MCP** | `false` | Connect to Home Assistant via ha-mcp (38+ tools) |
| **HA MCP URL** | | URL from ha-mcp add-on logs |
| **HA Read-Only** | `true` | When on, NanoBot can only read — cannot control devices |

### Voice Assistant

| Option | Default | Description |
|---|---|---|
| **Enable API** | `false` | Start the OpenAI-compatible API on port 8900 |
| **Auto Conversation Agent** | `false` | Auto-register as HA's voice assistant on startup |

### Channels

| Option | Default | Description |
|---|---|---|
| **Enable Discord** | `false` | Discord bot for remote access |
| **Enable MQTT** | `false` | Two-way MQTT bridge (requires Mosquitto) |

### Events & Automation

| Option | Default | Description |
|---|---|---|
| **Enable Event Streaming** | `false` | Subscribe to HA event bus for reactive automations |
| **Event Types** | `state_changed` | Comma-separated event types to monitor |

---

## Architecture

```
                        Voice / Dashboard / Discord
                                  |
                                  v
                    HA Assist / openai_conversation
                                  |
                                  v
                      NanoBot API Server (:8900)
                                  |
                                  v
                         NanoBot Agent Loop
                        /    |    |    \
                       /     |    |     \
                 LLM API  ha-mcp  MQTT   Filesystem
                (external) tools  bridge  workspace
                            |      |        |
                            v      v        v
                      Home Assistant   /config/nanobot/
                      REST/WS API      workspace/

    HA Event Bus ---websocket---> Event Listener ---> workspace/events/
                                                          |
                                                    Cron Agent picks up
                                                          |
                                                  Discord alert / HA action

    HA Automation ---mqtt.publish---> nanobot/inbox
                                          |
                                    MQTT Bridge ---> NanoBot API
                                          |
                                    nanobot/outbox ---> HA trigger
```

---

## Development

### Local Dev Environment

```bash
cd dev/
cp .env.example .env
# Edit .env with your real API keys and HA details
docker compose up --build
```

NanoBot runs headless — interact via Discord, MQTT, or the API at `http://localhost:8900`.

### Project Structure

```
nanoBotAddon/
├── nanobot/                        # The HA add-on
│   ├── config.yaml                 # Add-on manifest (options, schema, ports)
│   ├── Dockerfile                  # Container build
│   ├── run.sh                      # Entrypoint — starts all services
│   ├── generate_config.py          # Translates HA options -> nanobot config.json
│   ├── nanobot_api_server.py       # OpenAI-compatible API (/v1/chat/completions)
│   ├── setup_conversation_agent.py # Auto-registers as HA conversation agent
│   ├── ha_event_listener.py        # WebSocket event bus subscriber
│   ├── ha_mqtt_bridge.py           # MQTT pub/sub bridge
│   ├── workspace-templates/        # Example instruction files
│   ├── translations/en.yaml        # UI translations
│   ├── DOCS.md                     # Shown in HA add-on UI
│   └── CHANGELOG.md
├── dev/                            # Development environment
│   ├── docker-compose.yml
│   ├── .env.example
│   ├── options.json                # Mock HA options for dev
│   └── nanobot-workspace/          # Bind-mounted workspace
├── nanobot-ref/                    # Upstream NanoBot source (git-ignored)
├── repository.yaml                 # HA add-on repository manifest
└── README.md                       # This file
```

### Key Design Decisions

- **`nanobot serve` doesn't exist** in the published PyPI package (v0.1.4.post6). The API server is a standalone `nanobot_api_server.py` that wraps the same `AgentLoop` and `MessageBus`.
- **s6-overlay strips Docker env vars.** Dev mode reads options from `/data/options.json` with env var fallbacks. Production uses `bashio::config`.
- **Config validation:** nanobot v0.1.4 rejects unknown keys in config.json (strict Pydantic). The `api` block is not written to config.json — the API server reads host/port from env vars.
- **Read-only safety mode** uses `enabled_tools` in MCP config to whitelist 45 read-only tool names out of 90+ available in ha-mcp.

---

## License

MIT
