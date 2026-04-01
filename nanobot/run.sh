#!/usr/bin/env bash
# ==============================================================================
# NanoBot AI Assistant - Home Assistant Add-on Entrypoint
# ==============================================================================
# Called via: /usr/bin/with-contenv /run.sh
# with-contenv ensures s6-overlay exports NANOBOT_* env vars into this script.
set -euo pipefail

# Detect if running under HA Supervisor (real token vs dev dummy)
# In dev mode, SUPERVISOR_TOKEN is set to "dev-token" or not set at all
IS_HA_SUPERVISOR=false
if [ -n "${SUPERVISOR_TOKEN:-}" ] && [ "${SUPERVISOR_TOKEN}" != "dev-token" ]; then
    # Try to source bashio
    if [ -f /usr/lib/bashio/bashio.sh ]; then
        # shellcheck source=/dev/null
        source /usr/lib/bashio/bashio.sh
        IS_HA_SUPERVISOR=true
    fi
fi

if [ "${IS_HA_SUPERVISOR}" = "true" ]; then
    # HA Supervisor environment — use bashio
    LOG_LEVEL=$(bashio::config 'log_level' 'info')
    bashio::log.info "Starting NanoBot AI Assistant..."
    bashio::log.info "Log level: ${LOG_LEVEL}"
    bashio::log.info "Generating NanoBot configuration..."
else
    # Standalone Docker environment (dev mode)
    LOG_LEVEL=$(python3 -c "import json; d=json.load(open('/data/options.json')); print(d.get('log_level','info'))" 2>/dev/null || echo "info")
    echo "[INFO] Starting NanoBot AI Assistant (standalone/dev mode)..."
    echo "[INFO] Log level: ${LOG_LEVEL}"
    echo "[INFO] Generating NanoBot configuration..."
fi

# Generate nanobot config.json from HA options
python3 /app/generate_config.py

if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to generate NanoBot configuration!"
    exit 1
fi

echo "[INFO] Configuration generated successfully."

# Set NANOBOT log level via environment
case "${LOG_LEVEL}" in
    trace)   export LOGURU_LEVEL="TRACE" ;;
    debug)   export LOGURU_LEVEL="DEBUG" ;;
    info)    export LOGURU_LEVEL="INFO" ;;
    warning) export LOGURU_LEVEL="WARNING" ;;
    error)   export LOGURU_LEVEL="ERROR" ;;
    *)       export LOGURU_LEVEL="INFO" ;;
esac

echo "[INFO] Starting NanoBot gateway on port 18790..."

# Start nanobot gateway
exec nanobot gateway
