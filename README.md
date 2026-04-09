# NanoBot for Home Assistant

<p align="center">
  <img src="nanobot/logo.svg" alt="NanoBot" width="420" />
</p>

<p align="center">
  <em>A cat brain for your smart home.</em><br>
  <strong>NanoBot is your personal AI cat butler that lives inside Home Assistant.</strong><br>
  Think Jarvis from Iron Man — but it's a cat. It knows your entire home,<br>
  remembers your conversations, and grows into your perfect pet assistant over time.
</p>

<p align="center">
  <a href="#get-started">Get Started</a> &bull;
  <a href="#what-nanobot-does">What It Does</a> &bull;
  <a href="#talk-to-it">Talk To It</a> &bull;
  <a href="#development">Development</a>
</p>

---

## Meet your new housecat

NanoBot is an AI assistant that runs as a Home Assistant add-on. Hook it up to any LLM (Claude, GPT, DeepSeek, local Ollama — anything OpenAI-compatible) and it becomes the brain of your smart home.

The whole point of NanoBot is this: **it gives your Home Assistant a personality, a working memory, and paws to do the boring work.**

It **sees** your entire home — every light, every sensor, every automation. It **remembers** — your conversations, your preferences, your routines. It learns what you care about and becomes your personal pet butler over time. It **acts** — flip switches, create automations, organize your to-dos, set reminders. And it **thinks ahead** — morning briefings, security alerts, energy reports, all on its own while you sleep.

Let it loose and it'll go find you a cheap pair of underpants online. Or a solar module deal. It doesn't care — it'll happily fetch whatever you ask for. Just be careful what you wish for. If you're not specific enough, this cat might also bring back your neighbor's dead parrot. It's helpful like that.

It'll meow at you through HA Assist voice commands. It'll purr in your Discord DMs from across the world. It'll nudge your automations via MQTT. Or it'll just quietly keep watch in the background like any good cat does.

Your house, its domain. You just live in it.

## What NanoBot Does

| | What | How |
|---|---|---|
| **Sees everything** | Reads all entity states, areas, devices, history, automations, dashboards | 38+ read-only HA tools via [ha-mcp](https://github.com/homeassistant-ai/ha-mcp) |
| **Remembers you** | Keeps conversation history, learns your preferences, builds context over time | Persistent workspace memory in `/config/nanobot/` |
| **Controls your home** | Calls services, toggles devices, creates automations on the fly | Full-access mode (opt-in, safely off by default) |
| **Organizes your life** | Reminders, to-do lists, notes, scheduled tasks — your personal assistant | Workspace files + cron agent |
| **Talks to you** | Voice assistant through HA Assist — your Jarvis moment | Auto-registers as conversation agent with one checkbox |
| **Chats on Discord** | Full Discord bot — ask about your home from the office, the beach, wherever | Built-in channel integration |
| **Listens to MQTT** | Two-way messaging with any automation or IoT device | `nanobot/inbox` / `nanobot/outbox` topics |
| **Watches events** | Reacts to motion, doors, state changes the moment they happen | WebSocket event bus subscription |
| **Thinks ahead** | Morning briefings, security alerts, energy reports — without being asked | Proactive cron agent with natural-language instruction files |
| **Fetches things** | Web search, price lookups, research — send it on errands | LLM tool-use capabilities |
| **Speaks REST** | OpenAI-compatible API that any integration can call | `POST /v1/chat/completions` on port 8900 |

## Talk To It

> "What's the temperature in the living room?"
>
> "Which lights did I leave on?"
>
> "Turn off everything in the bedroom."
>
> "Remind me to water the plants every Wednesday."
>
> "Create an automation that turns on the porch light at sunset."
>
> "How much energy did I burn this week?"
>
> "What happened in the house while I was asleep?"
>
> "Find me the cheapest 400W solar panel online."

---

## Get Started

### 1. Install the add-on

In Home Assistant: **Settings -> Add-ons -> Add-on Store -> Repositories** -> paste this repo URL -> Install **NanoBot AI Assistant**.

### 2. Give it a brain

Set your LLM provider in the add-on config. Any OpenAI-compatible provider works — cloud or local.

| Option | Example |
|---|---|
| **LLM Provider** | `custom` |
| **LLM API Key** | `sk-abc123...` |
| **LLM Base URL** | `https://api.openai.com/v1` |
| **LLM Model** | `gpt-4o`, `claude-4.5`, `deepseek-chat` |

### 3. Give it eyes

Install [ha-mcp](https://github.com/homeassistant-ai/ha-mcp), copy its URL from the logs, then in NanoBot config:

- Enable **Enable Home Assistant MCP**
- Paste the URL into **HA MCP Server URL**
- Leave **HA Read-Only** on (it can see everything but touch nothing — until you decide to trust the cat)

### 4. Give it a voice

- Enable **Enable OpenAI-Compatible API** in the NanoBot add-on config
- Restart the add-on
- Install **[Extended OpenAI Conversation](https://github.com/jekalmin/extended_openai_conversation)** via HACS:
  1. HACS → Integrations → ⋮ → Custom repositories → paste `https://github.com/jekalmin/extended_openai_conversation` → Category: Integration → Add
  2. Search **"Extended OpenAI Conversation"** in HACS → Download → Restart HA
  3. Settings → Devices & Services → Add Integration → search **"Extended OpenAI"**
  4. Set API Key to `nanobot`, Base URL to `http://<your-ha-ip>:8900/v1`, check **Skip Authentication**
  5. Settings → Voice Assistants → set Conversation Agent to **"NanoBot (Extended OpenAI Conversation)"**

That's it. Open the Assist dialog and talk to your home.

> **Why not the built-in OpenAI Conversation?** Recent HA versions removed support for custom API endpoints — it only works with the official OpenAI API now. The HACS integration restores this ability.

### 5. Let it loose (optional)

Once you're comfortable with the cat roaming around:

- Set **HA Read-Only** to `false` — now it can control devices, call services, create automations
- Enable **Discord** — chat with your home from anywhere in the world
- Enable **MQTT** — wire it into any HA automation as a two-way channel
- Enable **Event Streaming** — it watches the event bus and reacts to what happens in real-time
- Write instruction files in `/config/nanobot/workspace/instructions/` — tell it what to do in plain English (morning briefings, security patrols, shopping research, whatever you want)

The more you use it, the more it remembers. It builds up context about your home, your habits, your preferences. Over time it stops being a chatbot and starts being *your* cat butler.

---

## Architecture

```
         You
          |
    voice | discord | mqtt | rest
          |
          v
    NanoBot (the cat brain)
     |    |    |    |    |
     v    v    v    v    v
    LLM  HA   MQTT  Web  Workspace
   (any) tools bridge srch  & memory
          |      |         |
          v      v         v
    Home Assistant     /config/nanobot/
    (your entire       workspace/
     smart home)       (remembers everything)
```

NanoBot sits in the middle of everything. It talks to your LLM for intelligence, to Home Assistant for awareness and control, to MQTT for automation messaging, to the web for research and errands, and to its workspace for memory and proactive behavior. The cat sees all, knows all, remembers all.

---

## All Options

| Option | Default | What it does |
|---|---|---|
| **LLM Provider** | `custom` | LLM backend (`custom`, `openai`, `anthropic`, `openrouter`) |
| **LLM API Key** | | Your API key |
| **LLM Base URL** | | Provider endpoint URL |
| **LLM Model** | `claude-4.5` | Model to use |
| **Enable HA MCP** | off | Connect to Home Assistant via ha-mcp |
| **HA MCP URL** | | URL from ha-mcp add-on logs |
| **HA Access Token** | | Only needed for remote HA (leave blank for local) |
| **HA Read-Only** | on | On = safe. Off = the cat has claws. |
| **Enable API** | off | OpenAI-compatible API on port 8900 |
| **Auto Conversation Agent** | off | Auto-register as HA voice assistant on startup |
| **Enable Discord** | off | Discord bot channel |
| **Discord Bot Token** | | From Discord Developer Portal |
| **Discord Channel ID** | | Restrict to one channel (optional) |
| **Discord Allowed Users** | `*` | Who can talk to the cat (`*` = everyone) |
| **Discord Group Policy** | `open` | `open` = responds to all, `mention` = only when @mentioned |
| **Enable MQTT** | off | MQTT bridge (needs Mosquitto add-on + API enabled) |
| **Enable Event Streaming** | off | Subscribe to HA event bus |
| **Event Types** | `state_changed` | Which events to watch (comma-separated) |
| **Enable WebUI** | on | Web management panel on port 18780 (login: admin / nanobot) |
| **Log Level** | `info` | `trace` / `debug` / `info` / `warning` / `error` |

### Ports

| Port | What lives there |
|---|---|
| **18780** | NanoBot WebUI (web management panel, login: admin / nanobot) |
| **8900** | OpenAI-compatible API (`/v1/chat/completions`, `/v1/models`, `/health`) |
| **18790** | NanoBot Gateway (channels, cron, heartbeat — internal plumbing, no HTTP) |

---

## Development

### Local Dev

```bash
cd dev/
cp .env.example .env    # fill in your real API keys and HA details
docker compose up --build
```

NanoBot runs headless — interact via Discord, MQTT, or the API at `http://localhost:8900`.

### Project Structure

```
nanoBotAddon/
├── nanobot/                        # The HA add-on
│   ├── config.yaml                 # Add-on manifest (options, schema, ports)
│   ├── Dockerfile                  # Container build
│   ├── run.sh                      # Entrypoint — orchestrates all services
│   ├── generate_config.py          # HA options -> nanobot config.json
│   ├── nanobot_api_server.py       # OpenAI-compatible API server
│   ├── setup_conversation_agent.py # Auto-registers as HA conversation agent
│   ├── ha_event_listener.py        # HA WebSocket event bus subscriber
│   ├── ha_mqtt_bridge.py           # MQTT pub/sub bridge
│   ├── workspace-templates/        # Example instruction files (briefings, alerts)
│   ├── translations/en.yaml        # UI strings
│   ├── DOCS.md                     # Shown in HA add-on panel
│   └── CHANGELOG.md
├── dev/                            # Dev environment
│   ├── docker-compose.yml
│   ├── .env.example
│   ├── options.json                # Mock HA options for local dev
│   └── nanobot-workspace/          # Bind-mounted workspace
├── nanobot-ref/                    # Upstream NanoBot source (git-ignored)
└── repository.yaml                 # HA add-on repository manifest
```

### Notes for Contributors

- `nanobot serve` doesn't exist in PyPI v0.1.4 — `nanobot_api_server.py` is our standalone replacement that wraps the same `AgentLoop` and `MessageBus`
- s6-overlay strips Docker env vars — dev mode reads from `options.json` with `NANOBOT_*` env var fallbacks
- nanobot's Pydantic config rejects unknown keys — `api` block is NOT written to config.json, the API server reads host/port from env vars
- Read-only mode whitelists 45 specific tool names from ha-mcp's 90+ available tools

---

## License

MIT
