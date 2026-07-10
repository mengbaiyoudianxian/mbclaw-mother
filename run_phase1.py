#!/usr/bin/env python3
"""MBclaw Phase 1 — production entry point.

Imports the existing main.py app and runs uvicorn.
Avoids the 'mother-server' hyphenated module path issue.
"""
import sys, os
sys.path[:0] = [
    '/opt/mbclaw/mother-server/phase1_app',
    '/opt/mbclaw/mother-server',
    '/opt/mbclaw',
]
os.environ.setdefault('TOKEN_POOL_URL', 'http://127.0.0.1:8100')
os.environ.setdefault('MBCLAW_LLM_MOCK', '0')

# Load .env — manual parser (no dotenv dependency)
for _env_path in ['/opt/mbclaw/.env', '/opt/mbclaw/mother-server/.env']:
    try:
        with open(_env_path) as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith('#') and '=' in _line:
                    _k, _v = _line.split('=', 1)
                    _k, _v = _k.strip(), _v.strip()
                    if _k not in os.environ:
                        os.environ[_k] = _v
    except FileNotFoundError:
        pass

import uvicorn
# Import main.py from the mother-server directory
_mp = os.path.join(os.path.dirname(__file__), 'main.py')
import importlib.util
spec = importlib.util.spec_from_file_location('mother_server_main', _mp)
mother_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mother_main)

uvicorn.run(mother_main.app, host='0.0.0.0', port=8000, reload=False)
