#!/usr/bin/env python3
"""Standalone NanoBot OpenAI-compatible API server.

The `nanobot serve` CLI command is not available in nanobot-ai<=0.1.4.post6
(it exists only in unreleased upstream source). This script provides the same
functionality: a minimal aiohttp server exposing /v1/chat/completions,
/v1/models, and /health.

Usage:
    python3 /app/nanobot_api_server.py

Reads NanoBot config from /config/nanobot/config.json (same as gateway).
Binds to the host/port from config.api (default 0.0.0.0:8900).
"""

import asyncio
import json
import os
import time
import uuid
import sys
from pathlib import Path
from typing import Any

from aiohttp import web
from loguru import logger


# ---------------------------------------------------------------------------
# Response helpers (same as upstream nanobot.api.server)
# ---------------------------------------------------------------------------


def _error_json(
    status: int, message: str, err_type: str = "invalid_request_error"
) -> web.Response:
    return web.json_response(
        {"error": {"message": message, "type": err_type, "code": status}},
        status=status,
    )


def _chat_completion_response(content: str, model: str) -> dict[str, Any]:
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def _response_text(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "content"):
        return str(getattr(value, "content") or "")
    return str(value)


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------

API_SESSION_KEY = "api:default"
API_CHAT_ID = "default"


async def handle_chat_completions(request: web.Request) -> web.Response:
    """POST /v1/chat/completions — OpenAI-compatible chat endpoint."""
    try:
        body = await request.json()
    except Exception:
        return _error_json(400, "Invalid JSON body")

    messages = body.get("messages")
    if not isinstance(messages, list) or len(messages) != 1:
        return _error_json(400, "Only a single user message is supported")

    if body.get("stream", False):
        return _error_json(400, "stream=true is not supported yet")

    message = messages[0]
    if not isinstance(message, dict) or message.get("role") != "user":
        return _error_json(400, "Only a single user message is supported")

    user_content = message.get("content", "")
    if isinstance(user_content, list):
        user_content = " ".join(
            part.get("text", "") for part in user_content if part.get("type") == "text"
        )

    agent_loop = request.app["agent_loop"]
    timeout_s: float = request.app.get("request_timeout", 120.0)
    model_name: str = request.app.get("model_name", "nanobot")

    session_key = (
        f"api:{body['session_id']}" if body.get("session_id") else API_SESSION_KEY
    )
    session_locks: dict[str, asyncio.Lock] = request.app["session_locks"]
    session_lock = session_locks.setdefault(session_key, asyncio.Lock())

    logger.info("API request session_key={} content={}", session_key, user_content[:80])

    _FALLBACK = "I've completed processing but have no response to give."

    try:
        async with session_lock:
            try:
                response = await asyncio.wait_for(
                    agent_loop.process_direct(
                        content=user_content,
                        session_key=session_key,
                        channel="api",
                        chat_id=API_CHAT_ID,
                    ),
                    timeout=timeout_s,
                )
                response_text = _response_text(response)

                if not response_text or not response_text.strip():
                    response_text = _FALLBACK

            except asyncio.TimeoutError:
                return _error_json(504, f"Request timed out after {timeout_s}s")
            except Exception:
                logger.exception("Error processing request for session {}", session_key)
                return _error_json(
                    500, "Internal server error", err_type="server_error"
                )
    except Exception:
        logger.exception("Unexpected API error for session {}", session_key)
        return _error_json(500, "Internal server error", err_type="server_error")

    return web.json_response(_chat_completion_response(response_text, model_name))


async def handle_models(request: web.Request) -> web.Response:
    """GET /v1/models"""
    model_name = request.app.get("model_name", "nanobot")
    return web.json_response(
        {
            "object": "list",
            "data": [
                {
                    "id": model_name,
                    "object": "model",
                    "created": 0,
                    "owned_by": "nanobot",
                }
            ],
        }
    )


async def handle_health(request: web.Request) -> web.Response:
    """GET /health"""
    return web.json_response({"status": "ok"})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    from nanobot.agent.loop import AgentLoop
    from nanobot.bus.queue import MessageBus
    from nanobot.config.loader import load_config, set_config_path
    from nanobot.session.manager import SessionManager
    from nanobot.utils.helpers import sync_workspace_templates

    # Load config from the same path as gateway
    config_path = Path("/config/nanobot/config.json")
    if not config_path.exists():
        print(f"[api_server] ERROR: {config_path} not found", file=sys.stderr)
        sys.exit(1)

    set_config_path(config_path)
    config = load_config(config_path)

    # API settings — hardcoded defaults since nanobot v0.1.4.post6
    # doesn't have ApiConfig in its schema (would cause validation error).
    api_host = os.environ.get("NANOBOT_API_HOST", "0.0.0.0")
    api_port = int(os.environ.get("NANOBOT_API_PORT", "8900"))
    api_timeout = float(os.environ.get("NANOBOT_API_TIMEOUT", "120.0"))
    model_name = config.agents.defaults.model

    # Build provider (same logic as CLI commands)
    from nanobot.providers.registry import find_by_name

    provider_name = config.get_provider_name(model_name)
    p = config.get_provider(model_name)
    spec = find_by_name(provider_name) if provider_name else None
    backend = spec.backend if spec else "openai_compat"

    from nanobot.providers.base import GenerationSettings

    if backend == "anthropic":
        from nanobot.providers.anthropic_provider import AnthropicProvider

        provider = AnthropicProvider(
            api_key=p.api_key if p else None,
            api_base=config.get_api_base(model_name),
            default_model=model_name,
            extra_headers=p.extra_headers if p else None,
        )
    elif backend == "azure_openai":
        from nanobot.providers.azure_openai_provider import AzureOpenAIProvider

        provider = AzureOpenAIProvider(
            api_key=p.api_key if p else "",
            api_base=p.api_base if p else "",
            default_model=model_name,
        )
    else:
        from nanobot.providers.openai_compat_provider import OpenAICompatProvider

        provider = OpenAICompatProvider(
            api_key=p.api_key if p else None,
            api_base=config.get_api_base(model_name),
            default_model=model_name,
            extra_headers=p.extra_headers if p else None,
            spec=spec,
        )

    defaults = config.agents.defaults
    provider.generation = GenerationSettings(
        temperature=defaults.temperature,
        max_tokens=defaults.max_tokens,
        reasoning_effort=defaults.reasoning_effort,
    )

    sync_workspace_templates(config.workspace_path)

    bus = MessageBus()
    session_manager = SessionManager(config.workspace_path)

    agent_loop = AgentLoop(
        bus=bus,
        provider=provider,
        workspace=config.workspace_path,
        model=model_name,
        max_iterations=defaults.max_tool_iterations,
        context_window_tokens=defaults.context_window_tokens,
        web_search_config=config.tools.web.search,
        web_proxy=config.tools.web.proxy or None,
        exec_config=config.tools.exec,
        restrict_to_workspace=config.tools.restrict_to_workspace,
        session_manager=session_manager,
        mcp_servers=config.tools.mcp_servers,
        channels_config=config.channels,
        timezone=defaults.timezone,
    )

    # Build aiohttp app
    app = web.Application()
    app["agent_loop"] = agent_loop
    app["model_name"] = model_name
    app["request_timeout"] = api_timeout
    app["session_locks"] = {}

    app.router.add_post("/v1/chat/completions", handle_chat_completions)
    app.router.add_get("/v1/models", handle_models)
    app.router.add_get("/health", handle_health)

    async def on_startup(_app):
        await agent_loop._connect_mcp()

    async def on_cleanup(_app):
        await agent_loop.close_mcp()

    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    print(f"[api_server] Starting OpenAI-compatible API on {api_host}:{api_port}")
    print(f"[api_server] Model: {model_name}")
    print(f"[api_server] Endpoint: http://{api_host}:{api_port}/v1/chat/completions")

    web.run_app(app, host=api_host, port=api_port, print=lambda msg: logger.info(msg))


if __name__ == "__main__":
    main()
