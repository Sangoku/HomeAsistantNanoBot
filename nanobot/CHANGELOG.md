# Changelog

## 0.2.24

- Added `ffmpeg` to the Docker container for Discord voice message support.
  NanoBot can now transcribe and process audio/voice messages sent in Discord channels.
- Updated voice assistant documentation: the built-in HA "OpenAI Conversation"
  integration no longer supports custom endpoints — docs now point users to the
  **Extended OpenAI Conversation** HACS integration with step-by-step setup instructions.

## 0.2.23

- Fixed OpenAI-compatible API to accept multi-message conversations from HA voice
  assistants (Extended OpenAI Conversation, etc.). Previously the API rejected any
  request with more than one message, returning "Only a single user message is
  supported". Now system instructions, conversation history, and user messages are
  all combined and passed to the agent loop as structured context.

## 0.2.22

- Fixed MCP server configs getting reset on every add-on restart: user/agent-added
  MCP servers in `config.json` are now preserved across restarts. Only the managed
  `homeassistant` entry is regenerated from addon options — all other MCP servers
  (added via WebUI, agent, or manual edits) survive container restarts.

## 0.2.21

- Fixed WebUI password reset on every add-on restart: pass `--config /config/nanobot/config.json`
  to `nanobot webui start` so that `webui_config.json` (users/passwords) is stored in the
  persisted `/config/nanobot/` volume instead of the ephemeral `/root/.nanobot/` container path.

## 0.2.20

- Added `webui` config for "Open Web UI" button on the add-on page (links to `http://<host>:18780/dashboard`)

## 0.2.19

- Removed nginx reverse proxy and HA ingress — WebUI served directly on port 18780
- Removed static file extraction and path rewriting (source of startup crashes)
- WebUI accessible via direct port mapping (e.g. `http://<host>:18780`)

## 0.2.3

- Removed WebUI auth bypass (`webui_no_auth` option and `webui_auth_bypass.py`) — login is now always required
- Default credentials: username `admin`, password `nanobot` (auto-created on first run)
- Added WebUI login instructions to docs and READMEs

## 0.2.0

### Home Assistant Integration (6 phases)

**Phase 1 — HA MCP via ha-mcp add-on**
- New options: `ha_mcp_enabled`, `ha_mcp_url`, `ha_access_token`, `ha_read_only`
- Connects NanoBot MCP client to the ha-mcp add-on (92 HA tools)
- Read-only safety mode enabled by default (no accidental device control)
- Full-access mode available via `ha_read_only: false`

**Phase 2 — OpenAI-compatible API for HA Conversation**
- New option: `api_enabled`
- Exposes NanoBot's OpenAI-compatible API on port 8900 (bound to `0.0.0.0`)
- Enables HA's `openai_conversation` integration to use NanoBot as the voice assistant brain

**Phase 3 — HA Event Streaming**
- New options: `ha_events_enabled`, `ha_event_types`
- New script: `ha_event_listener.py` — subscribes to HA WebSocket event bus
- Events written to `/config/nanobot/workspace/events/` as JSON files
- Auto-cleanup of events older than 24 hours

**Phase 4 — MQTT Bidirectional Channel**
- New option: `mqtt_enabled`
- New script: `ha_mqtt_bridge.py` — pub/sub on `nanobot/inbox` / `nanobot/outbox` / `nanobot/status`
- Auto-detects Mosquitto broker via HA service discovery (`bashio::services mqtt`)
- Added `paho-mqtt` and `websockets` to Dockerfile

**Phase 5 — Proactive Cron Agent**
- New `workspace-templates/` directory with example instruction files:
  - `morning-briefing.md` — daily 7am home summary
  - `security-watch.md` — overnight motion/door alerts
  - `energy-monitor.md` — weekly energy usage report
- Templates auto-copied to workspace on first run

**Phase 6 — REST Command Documentation**
- Documented how HA automations can POST tasks to NanoBot Gateway on port 18790

### Other Changes
- Version bumped to 0.2.0
- Comprehensive `DOCS.md` rewrite with setup guides for all integration modes
- Updated `translations/en.yaml` with descriptions for all new options
- Add-on description updated to reflect smart home integration capabilities

## 0.1.4

- Initial release
- Based on NanoBot v0.1.4.post6
- LLM provider configuration via HA options
- Discord bot integration
- Gateway API on port 18790

