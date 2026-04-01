#!/usr/bin/env bash
# ==============================================================================
# NanoBot HA Add-on - Development Environment Setup Script
# ==============================================================================
# Starts the dev environment via docker compose.
# nanobot-ai is installed from PyPI inside the container.
#
# Usage: ./dev/setup.sh [--reset]
#   --reset  Remove existing volumes and start fresh
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[OK]${NC} $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $*"; }

# ==============================================================================
# Check prerequisites
# ==============================================================================
check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v docker &>/dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi

    if ! docker info &>/dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi

    log_success "Prerequisites OK"
}

# ==============================================================================
# Setup config files
# ==============================================================================
setup_env() {
    if [ ! -f "${SCRIPT_DIR}/.env" ]; then
        log_info "Creating .env from .env.example..."
        cp "${SCRIPT_DIR}/.env.example" "${SCRIPT_DIR}/.env"
        log_warn ".env created from example. Edit dev/.env to customize settings."
    else
        log_success ".env already exists"
    fi

    if [ ! -f "${SCRIPT_DIR}/options.json" ]; then
        log_info "Creating options.json from options.json.example..."
        cp "${SCRIPT_DIR}/options.json.example" "${SCRIPT_DIR}/options.json"
        log_warn "options.json created from example. Edit dev/options.json with your real credentials."
    else
        log_success "options.json already exists"
    fi
}

# ==============================================================================
# Start the dev environment
# ==============================================================================
start_environment() {
    local reset="${1:-false}"

    cd "${SCRIPT_DIR}"

    if [ "${reset}" = "true" ]; then
        log_warn "Resetting environment (removing volumes)..."
        docker compose down -v 2>/dev/null || true
    fi

    log_info "Building and starting NanoBot dev environment..."
    log_info "(First build downloads nanobot-ai from PyPI — takes ~2 min)"
    docker compose up --build -d

    log_info "Waiting for NanoBot to start..."

    local max_wait=120
    local waited=0
    while [ ${waited} -lt ${max_wait} ]; do
        if docker logs nanobot-dev-addon 2>&1 | grep -q "nanobot gateway"; then
            break
        fi
        sleep 3
        waited=$((waited + 3))
        echo -n "."
    done
    echo ""

    echo ""
    echo "============================================================"
    echo -e "${GREEN}NanoBot Dev Environment Ready!${NC}"
    echo "============================================================"
    echo ""
    echo "  NanoBot Gateway: http://localhost:18790"
    echo "  NanoBot API:     http://localhost:18790/api/v1"
    echo ""
    echo "  Config:          dev/options.json"
    echo ""
    echo "  To view logs:"
    echo "  docker logs -f nanobot-dev-addon"
    echo ""
    echo "  To stop:"
    echo "  docker compose -f ${SCRIPT_DIR}/docker-compose.yml down"
    echo "============================================================"
}

# ==============================================================================
# Main
# ==============================================================================
main() {
    local reset=false

    for arg in "$@"; do
        case "${arg}" in
            --reset) reset=true ;;
            --help|-h)
                echo "Usage: $0 [--reset]"
                echo "  --reset  Remove existing volumes and start fresh"
                exit 0
                ;;
        esac
    done

    echo ""
    echo "============================================================"
    echo "  NanoBot HA Add-on - Dev Environment Setup"
    echo "============================================================"
    echo ""

    check_prerequisites
    setup_env
    start_environment "${reset}"
}

main "$@"
