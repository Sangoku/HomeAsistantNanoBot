# NanoBot Home Assistant Add-on

This repository contains the [NanoBot](https://github.com/HKUDS/nanobot) AI assistant packaged as a [Home Assistant](https://www.home-assistant.io/) add-on.

## Quick Start (Development)

```bash
# 1. Clone this repo
git clone <this-repo> nanoBotAddon
cd nanoBotAddon

# 2. Clone nanobot reference (already done if nanobot-ref/ exists)
git clone https://github.com/HKUDS/nanobot nanobot-ref

# 3. Run the dev setup script
./dev/setup.sh

# 4. Open Home Assistant at http://localhost:8123
# Login: admin / admin
```

## Project Structure

```
nanoBotAddon/
├── nanobot/              # The HA add-on (config, Dockerfile, run.sh)
├── nanobot-ref/          # NanoBot source reference (git-ignored)
├── dev/                  # Development environment
│   ├── docker-compose.yml
│   ├── setup.sh          # Bootstrap script
│   └── .storage/         # Pre-populated HA storage (skips onboarding)
├── .devcontainer/        # VS Code devcontainer config
├── .vscode/              # VS Code tasks
├── repository.yaml       # HA add-on repository manifest
└── plans/plan.md         # Architecture documentation
```

## Add-on Configuration

| Option | Description |
|--------|-------------|
| `llm_provider` | LLM provider (`custom`, `openai`, `anthropic`, etc.) |
| `llm_api_key` | API key for the LLM provider |
| `llm_base_url` | Base URL for custom OpenAI-compatible endpoints |
| `llm_model` | Model name (e.g., `claude-4.5`, `gpt-4o`) |
| `discord_enabled` | Enable Discord bot |
| `discord_bot_token` | Discord bot token |
| `discord_channel_id` | Discord channel ID to restrict bot to |
| `log_level` | Log level (`trace`, `debug`, `info`, `warning`, `error`) |

## Architecture

See [plans/plan.md](plans/plan.md) for detailed architecture documentation.

## License

MIT
