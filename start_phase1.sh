#!/bin/bash
# MBclaw Phase 1 Mother startup — production deployment
set -e
cd /opt/mbclaw/mother-server
export PYTHONPATH=/opt/mbclaw/mother-server/phase1_app:/opt/mbclaw/mother-server:/opt/mbclaw:$PYTHONPATH
export TOKEN_POOL_URL="${TOKEN_POOL_URL:-http://127.0.0.1:8100}"
export MBCLAW_LLM_MOCK="${MBCLAW_LLM_MOCK:-0}"
[ -f /opt/mbclaw/.env ] && set -a && source /opt/mbclaw/.env && set +a
exec python3 -c "
import sys
sys.path[:0] = [
    '/opt/mbclaw/mother-server/phase1_app',
    '/opt/mbclaw/mother-server',
    '/opt/mbclaw',
]
import uvicorn
uvicorn.run('mother-server.main:app', host='0.0.0.0', port=8000, reload=False)
"
