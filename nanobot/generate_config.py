#!/usr/bin/env python3
"""Generate nanobot config.json from Home Assistant add-on options.

Reads /data/options.json (HA add-on options) and writes
~/.nanobot/config.json in the format expected by nanobot.

In dev mode, NANOBOT_* environment variables take precedence over
options.json values — this lets you keep credentials in dev/.env
(gitignored) without putting them in options.json.

Discord notes:
  - allowFrom: list of Discord USER IDs allowed to chat with the bot.
    Use ["*"] to allow everyone (default for dev).
  - groupPolicy: "mention" (bot only responds when @mentioned in group channels)
                 "open"    (bot responds to all messages in allowed channels)
  - discord_channel_id is informational only (not used for allowFrom).

HA MCP notes (Phase 1):
  - ha_mcp_enabled: wire NanoBot MCP client to the ha-mcp add-on URL.
  - ha_mcp_url: URL exposed by the ha-mcp add-on (streamableHttp transport).
  - ha_access_token: Long-Lived Access Token passed as Bearer auth header.
    Leave blank when ha-mcp is running as a local HA add-on (it handles auth).
  - ha_read_only: restrict MCP tools to read/query only (no call_service, etc.).

API notes (Phase 2):
  - api_enabled: expose NanoBot's OpenAI-compatible API on port 8900,
    bound to 0.0.0.0 so HA's openai_conversation integration can reach it.
"""

import json
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Read-only tool filter: only allow tools that read/query HA state.
# When ha_read_only=true these are the only tools NanoBot can use.
# ---------------------------------------------------------------------------
HA_READ_ONLY_TOOLS = [
    # State & entity queries
    "ha_get_state",
    "ha_get_states",
    "ha_search_entities",
    "ha_deep_search",
    "ha_get_overview",
    "ha_get_entity",
    # History & statistics
    "ha_get_history",
    "ha_get_logbook",
    "ha_get_statistics",
    # Service listing (read-only, does NOT call services)
    "ha_list_services",
    # Automations & scripts (read-only config)
    "ha_config_get_automation",
    "ha_get_automation_traces",
    "ha_config_get_script",
    # Areas, floors, groups, labels, zones (config listing)
    "ha_config_list_areas",
    "ha_config_list_floors",
    "ha_config_list_groups",
    "ha_config_list_helpers",
    "ha_config_get_label",
    # Dashboards (read-only)
    "ha_config_get_dashboard",
    "ha_config_list_dashboard_resources",
    # Calendar (read-only)
    "ha_config_get_calendar_events",
    # System info
    "ha_get_updates",
    "ha_check_config",
    "ha_eval_template",
    "ha_get_camera_image",
    "ha_report_issue",
    "ha_get_entity_exposure",
    "ha_get_zone",
    "ha_get_device",
    "ha_get_integration",
    # HACS (read-only)
    "ha_hacs_info",
    "ha_hacs_list_installed",
    "ha_hacs_search",
    "ha_hacs_repository_info",
    # Todo (read-only)
    "ha_get_todo",
    # Blueprints (read-only)
    "ha_get_blueprint",
    # Addons (read-only)
    "ha_get_addon",
    # System health
    "ha_get_system_health",
]


def env_or(env_key: str, fallback):
    """Return env var value if set and non-empty, else fallback."""
    val = os.environ.get(env_key, "").strip()
    return val if val else fallback


def env_bool(env_key: str, fallback: bool) -> bool:
    """Return bool from env var, else fallback."""
    val = os.environ.get(env_key, "").strip().lower()
    if val in ("1", "true", "yes"):
        return True
    if val in ("0", "false", "no"):
        return False
    return fallback


def main():
    options_path = Path("/data/options.json")
    # /config/nanobot is accessible from HA's File Editor / Studio Code Server
    # and is bind-mounted to dev/nanobot-workspace/ in dev mode.
    config_dir = Path("/config/nanobot")
    config_path = config_dir / "config.json"

    # Load options.json (may contain placeholder values)
    opts: dict = {}
    if options_path.exists():
        with open(options_path) as f:
            opts = json.load(f)
    else:
        print(
            "WARNING: /data/options.json not found, using env vars only",
            file=sys.stderr,
        )

    # -------------------------------------------------------------------------
    # LLM / core settings
    # -------------------------------------------------------------------------
    llm_provider = env_or("NANOBOT_LLM_PROVIDER", opts.get("llm_provider", "custom"))
    llm_api_key = env_or("NANOBOT_LLM_API_KEY", opts.get("llm_api_key", ""))
    llm_base_url = env_or("NANOBOT_LLM_BASE_URL", opts.get("llm_base_url", ""))
    llm_model = env_or("NANOBOT_LLM_MODEL", opts.get("llm_model", "claude-4.5"))

    # -------------------------------------------------------------------------
    # Discord
    # -------------------------------------------------------------------------
    discord_enabled = opts.get("discord_enabled", False)
    discord_bot_token = env_or(
        "NANOBOT_DISCORD_BOT_TOKEN", opts.get("discord_bot_token", "")
    )
    discord_channel_id = env_or(
        "NANOBOT_DISCORD_CHANNEL_ID", opts.get("discord_channel_id", "")
    )
    discord_allowed_raw = env_or(
        "NANOBOT_DISCORD_ALLOWED_USERS", opts.get("discord_allowed_users", "*")
    )
    discord_group_policy = env_or(
        "NANOBOT_DISCORD_GROUP_POLICY", opts.get("discord_group_policy", "open")
    )

    # If a discord token is present, enable discord even if options.json says false
    if discord_bot_token and discord_bot_token not in (
        "your-discord-bot-token-here",
        "",
    ):
        discord_enabled = True

    # -------------------------------------------------------------------------
    # Phase 1 — HA MCP Integration
    # -------------------------------------------------------------------------
    ha_mcp_enabled = env_bool(
        "NANOBOT_HA_MCP_ENABLED", opts.get("ha_mcp_enabled", False)
    )
    ha_mcp_url = env_or("NANOBOT_HA_MCP_URL", opts.get("ha_mcp_url", ""))
    ha_access_token = env_or("NANOBOT_HA_ACCESS_TOKEN", opts.get("ha_access_token", ""))
    ha_read_only = env_bool("NANOBOT_HA_READ_ONLY", opts.get("ha_read_only", True))

    # -------------------------------------------------------------------------
    # Phase 2 — OpenAI-compatible API
    # -------------------------------------------------------------------------
    api_enabled = env_bool("NANOBOT_API_ENABLED", opts.get("api_enabled", False))

    # -------------------------------------------------------------------------
    # Phase 3 — HA Event Streaming
    # -------------------------------------------------------------------------
    ha_events_enabled = env_bool(
        "NANOBOT_HA_EVENTS_ENABLED", opts.get("ha_events_enabled", False)
    )
    ha_event_types_raw = env_or(
        "NANOBOT_HA_EVENT_TYPES", opts.get("ha_event_types", "state_changed")
    )

    # -------------------------------------------------------------------------
    # Phase 4 — MQTT
    # -------------------------------------------------------------------------
    mqtt_enabled = env_bool("NANOBOT_MQTT_ENABLED", opts.get("mqtt_enabled", False))

    # =========================================================================
    # Build nanobot config structure
    # =========================================================================
    config: dict = {
        "agents": {
            "defaults": {
                "model": llm_model,
                "provider": llm_provider,
                "workspace": str(config_dir / "workspace"),
            }
        },
        "providers": {
            "custom": {
                "apiKey": llm_api_key,
                "apiBase": llm_base_url,
            }
        },
        "channels": {
            "sendProgress": True,
        },
        "gateway": {
            "host": "0.0.0.0",
            "port": 18790,
        },
    }

    # -------------------------------------------------------------------------
    # Discord configuration
    # -------------------------------------------------------------------------
    if discord_enabled:
        # allowFrom: list of Discord USER IDs (not channel IDs!)
        # Use ["*"] to allow all users (recommended for personal bots)
        if discord_allowed_raw == "*" or not discord_allowed_raw:
            allow_from: list = ["*"]
        else:
            # Comma-separated list of user IDs
            allow_from = [
                uid.strip() for uid in discord_allowed_raw.split(",") if uid.strip()
            ]

        discord_config = {
            "enabled": True,
            "token": discord_bot_token,
            "allowFrom": allow_from,
            "groupPolicy": discord_group_policy,
        }
        config["channels"]["discord"] = discord_config

    # -------------------------------------------------------------------------
    # Phase 1 — MCP server for Home Assistant (via ha-mcp)
    # -------------------------------------------------------------------------
    if ha_mcp_enabled and ha_mcp_url:
        mcp_server_config: dict = {
            "type": "streamableHttp",
            "url": ha_mcp_url,
        }

        # Add Bearer token header if a Long-Lived Access Token is provided.
        # (Not needed when ha-mcp runs as a local HA add-on — it manages auth itself.)
        if ha_access_token:
            mcp_server_config["headers"] = {
                "Authorization": f"Bearer {ha_access_token}"
            }

        # Read-only safety mode: restrict tools to query/read operations only.
        if ha_read_only:
            mcp_server_config["enabled_tools"] = HA_READ_ONLY_TOOLS

        config.setdefault("tools", {}).setdefault("mcp_servers", {})
        config["tools"]["mcp_servers"]["homeassistant"] = mcp_server_config

    elif ha_mcp_enabled and not ha_mcp_url:
        print(
            "WARNING: ha_mcp_enabled=true but ha_mcp_url is empty. "
            "Install the ha-mcp add-on and paste its URL into ha_mcp_url.",
            file=sys.stderr,
        )

    # -------------------------------------------------------------------------
    # Phase 2 — OpenAI-compatible API (for HA Conversation integration)
    # NOTE: The "api" config key is NOT written to config.json because
    # nanobot-ai v0.1.4.post6 doesn't include ApiConfig in its schema
    # and will reject it with "Extra inputs are not permitted".
    # Our standalone nanobot_api_server.py reads host/port from env vars.
    # -------------------------------------------------------------------------

    # =========================================================================
    # Ensure directories exist
    # =========================================================================
    config_dir.mkdir(parents=True, exist_ok=True)

    workspace = Path(config["agents"]["defaults"]["workspace"])
    workspace.mkdir(parents=True, exist_ok=True)

    # Events directory (used by ha_event_listener.py in Phase 3)
    if ha_events_enabled:
        events_dir = workspace / "events"
        events_dir.mkdir(parents=True, exist_ok=True)

    # =========================================================================
    # Write config.json
    # nanobot gateway reads from ~/.nanobot/config.json by default.
    # We write there as the primary location, and also write a copy to
    # /config/nanobot/config.json for user visibility via File Editor.
    # =========================================================================
    nanobot_home = Path.home() / ".nanobot"
    nanobot_home.mkdir(parents=True, exist_ok=True)
    home_config_path = nanobot_home / "config.json"

    config_json = json.dumps(config, indent=2, ensure_ascii=False)

    # Primary: ~/.nanobot/config.json (read by `nanobot gateway`)
    with open(home_config_path, "w") as f:
        f.write(config_json)

    # Secondary: /config/nanobot/config.json (user-visible copy)
    with open(config_path, "w") as f:
        f.write(config_json)

    # =========================================================================
    # Summary log
    # =========================================================================
    print(f"Generated nanobot config at {home_config_path} (gateway)")
    print(f"  User-visible copy: {config_path}")
    print(f"  Provider: {llm_provider}")
    print(f"  Model: {llm_model}")
    print(f"  API Base: {llm_base_url if llm_base_url else '(none)'}")

    if discord_enabled:
        print(f"  Discord: enabled (groupPolicy={discord_group_policy})")
    else:
        print("  Discord: disabled")

    if ha_mcp_enabled:
        mode = "read-only" if ha_read_only else "full-access"
        print(f"  HA MCP: enabled — {ha_mcp_url} [{mode}]")
    else:
        print("  HA MCP: disabled")

    if api_enabled:
        print("  OpenAI API: enabled on 0.0.0.0:8900")
    else:
        print("  OpenAI API: disabled")

    if ha_events_enabled:
        print(f"  HA Event Streaming: enabled (types: {ha_event_types_raw})")
    else:
        print("  HA Event Streaming: disabled")

    if mqtt_enabled:
        print("  MQTT: enabled")
    else:
        print("  MQTT: disabled")


if __name__ == "__main__":
    main()
