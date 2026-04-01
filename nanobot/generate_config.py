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
"""

import json
import os
import sys
from pathlib import Path


def env_or(env_key: str, fallback):
    """Return env var value if set and non-empty, else fallback."""
    val = os.environ.get(env_key, "").strip()
    return val if val else fallback


def main():
    options_path = Path("/data/options.json")
    config_dir = Path.home() / ".nanobot"
    config_path = config_dir / "config.json"

    # Load options.json (may contain placeholder values)
    opts = {}
    if options_path.exists():
        with open(options_path) as f:
            opts = json.load(f)
    else:
        print("WARNING: /data/options.json not found, using env vars only", file=sys.stderr)

    # Resolve values: env vars take precedence over options.json
    llm_provider  = env_or("NANOBOT_LLM_PROVIDER",  opts.get("llm_provider", "custom"))
    llm_api_key   = env_or("NANOBOT_LLM_API_KEY",   opts.get("llm_api_key", ""))
    llm_base_url  = env_or("NANOBOT_LLM_BASE_URL",  opts.get("llm_base_url", ""))
    llm_model     = env_or("NANOBOT_LLM_MODEL",      opts.get("llm_model", "claude-4.5"))

    discord_enabled     = opts.get("discord_enabled", False)
    discord_bot_token   = env_or("NANOBOT_DISCORD_BOT_TOKEN",   opts.get("discord_bot_token", ""))
    discord_channel_id  = env_or("NANOBOT_DISCORD_CHANNEL_ID",  opts.get("discord_channel_id", ""))
    discord_allowed_raw = env_or("NANOBOT_DISCORD_ALLOWED_USERS", opts.get("discord_allowed_users", "*"))
    discord_group_policy = env_or("NANOBOT_DISCORD_GROUP_POLICY", opts.get("discord_group_policy", "open"))

    # If a discord token is present, enable discord even if options.json says false
    if discord_bot_token and discord_bot_token not in ("your-discord-bot-token-here", ""):
        discord_enabled = True

    # Build nanobot config structure
    config = {
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

    # Discord configuration
    if discord_enabled:
        # allowFrom: list of Discord USER IDs (not channel IDs!)
        # Use ["*"] to allow all users (recommended for personal bots)
        if discord_allowed_raw == "*" or not discord_allowed_raw:
            allow_from = ["*"]
        else:
            # Comma-separated list of user IDs
            allow_from = [uid.strip() for uid in discord_allowed_raw.split(",") if uid.strip()]

        discord_config = {
            "enabled": True,
            "token": discord_bot_token,
            "allowFrom": allow_from,
            "groupPolicy": discord_group_policy,
        }
        config["channels"]["discord"] = discord_config

    # Ensure config directory exists
    config_dir.mkdir(parents=True, exist_ok=True)

    # Also ensure workspace exists
    workspace = Path(config["agents"]["defaults"]["workspace"])
    workspace.mkdir(parents=True, exist_ok=True)

    # Write config
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"Generated nanobot config at {config_path}")
    print(f"  Provider: {llm_provider}")
    print(f"  Model: {llm_model}")
    print(f"  API Base: {llm_base_url}")
    if discord_enabled:
        print(f"  Discord: enabled (allowFrom={allow_from}, groupPolicy={discord_group_policy})")
    else:
        print(f"  Discord: disabled")


if __name__ == "__main__":
    main()
