#!/usr/bin/env bash
# ── MBclaw 总控制面板 启动脚本 ───────────────────────────────
# Usage: ./start.sh [--host HOST] [--port PORT] [--mock]
set -euo pipefail

HOST="0.0.0.0"
PORT="8080"
MOCK=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --host) HOST="$2"; shift 2 ;;
        --port) PORT="$2"; shift 2 ;;
        --mock) MOCK="1"; shift ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ── Load .env ───────────────────────────────────────────────
if [ -f .env ]; then
    echo "[start] Loading .env ..."
    set -a; source .env; set +a
elif [ -f .env.example ]; then
    echo "[start] No .env found, using .env.example defaults ..."
    set -a; source .env.example; set +a
fi

# ── Mock mode ───────────────────────────────────────────────
if [ "$MOCK" = "1" ]; then
    export MBCLAW_LLM_MOCK=1
    echo "[start] Mock mode enabled (MBCLAW_LLM_MOCK=1)"
fi

# ── Validate ────────────────────────────────────────────────
if [ "${MBCLAW_LLM_MOCK:-}" != "1" ] && [ -z "${MBCLAW_LLM_API_KEY:-}" ]; then
    echo "[start] WARNING: MBCLAW_LLM_API_KEY not set and mock mode is off."
    echo "[start] LLM calls will fail. Start with --mock for testing, or set API key in .env"
fi

# ── Data dir ────────────────────────────────────────────────
if [ -n "${MBCLAW_DATA:-}" ]; then
    mkdir -p "$MBCLAW_DATA"
    echo "[start] Data dir: $MBCLAW_DATA"
fi

# ── DB ──────────────────────────────────────────────────────
DB_PATH="${MBCLAW_DB_PATH:-data/mbclaw.db}"
mkdir -p "$(dirname "$DB_PATH")"
echo "[start] DB path: $DB_PATH"

# ── Start ───────────────────────────────────────────────────
echo "[start] Starting MBclaw on http://${HOST}:${PORT} ..."
exec uvicorn app.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --log-level info \
    --timeout-keep-alive 65
