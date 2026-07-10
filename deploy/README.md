# MBclaw Mother — Production Deployment

## Services

| Service | Systemd Unit | Port | Path |
|---------|-------------|------|------|
| Mother Phase 1 | mbclaw-mother | 8000 | /opt/mbclaw/mother-server |
| TokenPool | mbclaw-token-pool | 8100 | /opt/mbclaw/token_pool |
| QQBot Bridge | mbclaw-qqbot | — | /opt/mbclaw/mother-server |
| Admin Panel | (manual) | 8001 | /opt/mbclaw/admin-panel |

## Startup

```bash
# 1. TokenPool (must start first)
systemctl start mbclaw-token-pool

# 2. Mother Phase 1
systemctl start mbclaw-mother

# 3. QQBot Bridge
systemctl start mbclaw-qqbot

# 4. Admin Panel (manual)
cd /opt/mbclaw/admin-panel && \
  nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8001 \
  > /var/log/admin-panel.log 2>&1 &
```

## Config

- Environment: `/opt/mbclaw/.env`
- TokenPool URL: `TOKEN_POOL_URL=http://127.0.0.1:8100`
- QQ Bot: `QQ_BOT_APPID`, `QQ_BOT_SECRET` in `.env`

## Health Check

```bash
curl http://127.0.0.1:8000/health   # Mother
curl http://127.0.0.1:8100/health   # TokenPool
curl http://127.0.0.1:8001/health   # Admin Panel
```
