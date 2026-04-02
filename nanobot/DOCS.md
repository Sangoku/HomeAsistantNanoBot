# NanoBot AI Assistant

Your personal cat butler for Home Assistant. It sees your entire home, remembers your conversations, organizes your life, and grows into your perfect pet assistant over time. Think Jarvis — but fluffier, with a working memory and paws to do the boring work.

Be careful what you ask for though. Send it to find cheap solar panels and it will. Send it to find cheap underpants and it also will. Leave it unsupervised long enough and it might bring back your neighbor's dead parrot. It's helpful like that.

---

## Getting Started

### 1. Give it a brain

NanoBot needs an LLM to think. Any OpenAI-compatible provider works — cloud or local.

| Option | Example |
|---|---|
| **LLM Provider** | `custom` |
| **LLM API Key** | `sk-abc123...` |
| **LLM Base URL** | `https://api.openai.com/v1` |
| **LLM Model** | `gpt-4o`, `claude-4.5`, `deepseek-chat` |

### 2. Give it eyes

Install the [ha-mcp](https://github.com/homeassistant-ai/ha-mcp) add-on so NanoBot can see your home:

1. Start ha-mcp and copy the **MCP Server URL** from its logs
2. Enable **Enable Home Assistant MCP** in NanoBot settings
3. Paste the URL into **HA MCP Server URL**
4. Leave **HA Read-Only Mode** on — the cat can look at everything but touch nothing (until you decide to trust it)

NanoBot now has 38+ tools to query your entire smart home — states, history, areas, automations, devices, sensors, calendars, and more.

### 3. Give it a voice

1. Enable **Enable OpenAI-Compatible API**
2. Enable **Auto-register as Conversation Agent**
3. Restart the add-on

Done. NanoBot is now your HA Assist voice assistant. No manual integration setup, no URL copying, no API key fiddling. Just talk to your home.

---

## What it remembers

NanoBot isn't a stateless chatbot. It has **persistent memory**. Every conversation, every preference, every little thing you mention — it keeps it in its workspace at `/config/nanobot/`. Over time it learns what you care about, how you like things, and what to watch out for.

The more you use it, the more it becomes *yours*. It stops being a generic AI and starts being your personal cat butler who knows that you like the hallway light dim at night and that the irrigation should skip rainy days.

---

## What it can see (Read-Only Mode)

With HA Read-Only on (the default), the cat observes but doesn't touch:

> "What's the temperature in the living room?"
>
> "Which lights did I leave on?"
>
> "Show me the energy usage for the last 24 hours"
>
> "What happened overnight?"
>
> "Are there any pending updates?"

It reads entity states, searches by name/area/domain, browses history, logbook, statistics, automations, dashboards, calendars, HACS repos, system health — the works.

## What it can do (Full Access Mode)

Set **HA Read-Only** to `false` and the cat gets claws:

> "Turn off all lights in the bedroom"
>
> "Set the thermostat to 22 degrees"
>
> "Create an automation that turns on the porch light at sunset"
>
> "Lock the front door"

| Mode | What NanoBot can do |
|---|---|
| **Read-Only** (default) | Read states, search entities, view history, logbook, statistics, automations, dashboards, HACS info |
| **Full Access** | Everything above plus call services, control devices, create/modify automations, bulk control, backups |

## What it can organize

NanoBot isn't just about your smart home. It's your personal assistant:

> "Remind me to water the plants every Wednesday"
>
> "Add milk to the shopping list"
>
> "Find me the cheapest 400W solar panel online"
>
> "What did we talk about last week regarding the garden?"
>
> "Keep track of when the furnace filter was last changed"

It stores notes, reminders, lists, and research results in its workspace. It remembers context across conversations. It's the cat that keeps your life organized while also watching the house.

---

## Voice Assistant

When API + Auto Conversation Agent are enabled, NanoBot registers itself as the conversation agent in your default HA Assist pipeline. Your voice commands go through NanoBot, which uses its full toolkit to answer and act.

**Automatic setup (recommended):** Enable the two checkboxes, restart. That's it.

**Manual setup:** Add the `OpenAI Conversation` integration in HA Settings -> Devices & Services. Set API key to anything (e.g. `nanobot`) and base URL to `http://<your-ha-ip>:8900/v1`. Then set it as the conversation agent in Settings -> Voice Assistants.

---

## Discord

Enable Discord and the cat follows you everywhere. Ask about your home from the office, the beach, wherever. It remembers the conversation context across channels too.

| Option | What |
|---|---|
| **Discord Bot Token** | Create a bot at [Discord Developer Portal](https://discord.com/developers/applications) |
| **Discord Channel ID** | Lock the cat to one channel (leave empty for all) |
| **Discord Allowed Users** | Comma-separated user IDs, or `*` for everyone |
| **Discord Group Policy** | `open` = responds to all messages, `mention` = only when @mentioned |

---

## MQTT Bridge

Enable MQTT for two-way communication with HA automations and IoT devices. The cat listens on `nanobot/inbox`, responds on `nanobot/outbox`, and reports status on `nanobot/status`.

**Requires:** Mosquitto broker add-on + **Enable OpenAI-Compatible API** must both be on.

| Topic | Direction | What |
|---|---|---|
| `nanobot/inbox` | HA -> NanoBot | Send a task (plain text or `{"task": "..."}`) |
| `nanobot/outbox` | NanoBot -> HA | Response published automatically |
| `nanobot/status` | NanoBot -> HA | `online` / `offline` (retained) |

**Send a task from an automation:**
```yaml
service: mqtt.publish
data:
  topic: nanobot/inbox
  payload: "What lights are on right now?"
```

**React to NanoBot's answer:**
```yaml
trigger:
  - platform: mqtt
    topic: nanobot/outbox
action:
  - service: notify.mobile_app_phone
    data:
      message: "{{ trigger.payload }}"
```

---

## Event Reactions

Enable **HA Event Streaming** and the cat starts watching the event bus — motion sensors, doors opening, lights changing, automations firing. Events are saved as JSON files in `/config/nanobot/workspace/events/` and the proactive agent picks them up.

Set **HA Event Types** to a comma-separated list of what to watch (default: `state_changed`). Examples: `state_changed,automation_triggered,call_service`.

---

## Proactive Agent

The cat doesn't just wait to be asked. It can do things on its own.

NanoBot ships with example instruction files in `/config/nanobot/workspace/instructions/`:

| Template | What the cat does |
|---|---|
| `morning-briefing.md` | Wakes you up with a home summary at 7am |
| `security-watch.md` | Alerts you about overnight motion/door events |
| `energy-monitor.md` | Weekly energy usage report every Sunday |

Edit these with **File Editor** or **Studio Code Server**. Write your own — just describe what you want in plain English and add a cron expression. The cat follows natural language instructions.

**Example — irrigation check:**
```markdown
# Irrigation Check

Every day at 06:00, check:
1. Look at the weather forecast for today
2. If rain is expected, turn off the irrigation
3. Otherwise, run it for 20 minutes

cron: 0 6 * * *
```

---

## REST API

Any HA automation can talk to NanoBot directly. The cat speaks fluent OpenAI.

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
          message: "Someone's at the door. What should I do?"
```

---

## All Options

| Option | Default | What it does |
|---|---|---|
| **LLM Provider** | `custom` | LLM backend (`custom`, `openai`, `anthropic`, `openrouter`) |
| **LLM API Key** | | Your API key |
| **LLM Base URL** | | Provider endpoint URL |
| **LLM Model** | `claude-4.5` | Which model powers the cat's brain |
| **Enable HA MCP** | off | Connect to Home Assistant via ha-mcp |
| **HA MCP URL** | | URL from ha-mcp add-on logs |
| **HA Access Token** | | Only for remote HA instances (leave blank for local) |
| **HA Read-Only** | on | On = the cat looks but doesn't touch. Off = claws out. |
| **Enable API** | off | OpenAI-compatible API on port 8900 |
| **Auto Conversation Agent** | off | Auto-register as HA voice assistant on startup |
| **Enable Discord** | off | Discord bot |
| **Discord Bot Token** | | From Discord Developer Portal |
| **Discord Channel ID** | | Lock to one channel (optional) |
| **Discord Allowed Users** | `*` | Who can talk to the cat |
| **Discord Group Policy** | `open` | `open` or `mention` |
| **Enable MQTT** | off | MQTT bridge (needs Mosquitto + API enabled) |
| **Enable Event Streaming** | off | Watch the HA event bus |
| **Event Types** | `state_changed` | What events to watch (comma-separated) |
| **Log Level** | `info` | `trace` / `debug` / `info` / `warning` / `error` |

## Ports

| Port | What lives there |
|---|---|
| **8900** | OpenAI-compatible API (`/v1/chat/completions`, `/v1/models`, `/health`) |
| **18790** | NanoBot Gateway (channels, cron, heartbeat — internal plumbing, no HTTP) |

---

## Links

- [NanoBot](https://github.com/HKUDS/nanobot) — the upstream project
- [ha-mcp](https://github.com/homeassistant-ai/ha-mcp) — Home Assistant MCP server (gives the cat its eyes)
