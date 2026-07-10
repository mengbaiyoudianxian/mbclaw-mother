#!/usr/bin/env python3
"""QQBot Bridge — standalone WebSocket → Mother HTTP relay.

Connects to QQ Bot WebSocket, forwards messages to Mother's /gateway/web/chat
endpoint, and sends replies back via QQ Bot HTTP API.

Usage: python3 qqbot_bridge.py
Requires: QQ_BOT_APPID and QQ_BOT_SECRET in environment.
"""
import asyncio, json, os, sys, time

import requests

MOTHER_URL = os.environ.get('MOTHER_URL', 'http://127.0.0.1:8000').rstrip('/')
TOKEN_URL = 'https://bots.qq.com/app/getAppAccessToken'

APPID = os.environ.get('QQ_BOT_APPID', '')
SECRET = os.environ.get('QQ_BOT_SECRET', '')

# (1<<25)|(1<<27)|(1<<28) = GROUP_AND_C2C_EVENT | INTERACTION | MESSAGE_AUDIT
INTENTS = 436207616
SHARD = [0, 1]

MAX_RECONNECT_DELAY = 300
SESSION_FILE = '/tmp/mbclaw_qqbot_session.json'
STATE_FILE = '/tmp/mbclaw_qqbot_state.json'


def save_state(**kwargs):
    """Write current QQBot state to a JSON file for Mother's /health/qqbot."""
    try:
        state = {
            'websocket': kwargs.get('websocket', 'unknown'),
            'bot_name': kwargs.get('bot_name', ''),
            'session_id': kwargs.get('session_id', ''),
            'last_message_time': kwargs.get('last_message_time', ''),
            'last_error': kwargs.get('last_error', ''),
            'updated': time.time(),
        }
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f)
    except Exception:
        pass


def _api_prefix():
    return 'sandbox.' if os.environ.get('QQ_BOT_SANDBOX') == '1' else ''


def get_token() -> str:
    """Fetch a fresh QQ Bot access token."""
    try:
        r = requests.post(
            TOKEN_URL,
            json={'appId': APPID, 'clientSecret': SECRET},
            timeout=10,
        )
        data = r.json()
        return data.get('access_token', '')
    except Exception as e:
        print(f'[qqbot] token error: {e}', flush=True)
        return ''


def check_session_limit(token: str) -> dict:
    """Check WebSocket session_start_limit before connecting."""
    try:
        headers = {'Authorization': f'QQBot {token}'}
        r = requests.get(
            f'https://{_api_prefix()}api.sgroup.qq.com/gateway/bot',
            headers=headers,
            timeout=10,
        )
        data = r.json()
        return data.get('session_start_limit', {})
    except Exception:
        return {}


def save_session(session_id: str):
    """Save session ID for possible resume."""
    try:
        with open(SESSION_FILE, 'w') as f:
            json.dump({'session_id': session_id, 'time': time.time()}, f)
    except Exception:
        pass


def load_session() -> str | None:
    """Load previous session ID if still valid."""
    try:
        with open(SESSION_FILE) as f:
            data = json.load(f)
            if time.time() - data.get('time', 0) < 86400:
                return data.get('session_id')
    except Exception:
        pass
    return None


def send_reply(reply: str, msg_type: str, target_id: str, token: str, msg_id: str = ''):
    """Send a reply message back to QQ."""
    pref = _api_prefix()
    headers = {
        'Authorization': f'QQBot {token}',
        'Content-Type': 'application/json',
    }
    if msg_type == 'private':
        url = f'https://{pref}api.sgroup.qq.com/v2/users/{target_id}/messages'
        body = {'content': reply[:2000], 'msg_type': 0}
    else:
        url = f'https://{pref}api.sgroup.qq.com/v2/groups/{target_id}/messages'
        body = {'content': reply[:2000], 'msg_type': 0, 'msg_id': msg_id}
    try:
        requests.post(url, headers=headers, json=body, timeout=10)
    except Exception:
        pass


async def forward_to_mother(msg_text: str, user_id: str) -> str:
    """Forward a QQ message to Mother and get reply."""
    try:
        # Use hash of user_id as numeric session_id
        session_id = abs(hash(user_id)) % 100000
        loop = asyncio.get_running_loop()
        r = await loop.run_in_executor(
            None,
            lambda: requests.post(
                f'{MOTHER_URL}/gateway/web/chat',
                json={
                    'goal': msg_text,
                    'session_id': session_id,
                },
                timeout=60,
            ),
        )
        if r.status_code == 200:
            return r.json().get('reply', '')
    except Exception as e:
        print(f'[qqbot] mother error: {e}', flush=True)
    return '母体暂时无法回复'


async def connect_websocket():
    """Connect to QQ Bot WebSocket and relay messages."""
    import websockets

    gw = f'wss://{_api_prefix()}api.sgroup.qq.com/websocket'

    while True:
        try:
            # Rate-limit check
            token = get_token()
            if not token:
                print('[qqbot] no token, retrying in 30s', flush=True)
                await asyncio.sleep(30)
                continue

            limit = check_session_limit(token)
            remaining = limit.get('remaining', -1)
            if remaining <= 0:
                reset_ms = limit.get('reset_after', 60000)
                wait = max((reset_ms / 1000) + 5, 60)
                print(
                    f'[qqbot] session limit exhausted, '
                    f'waiting {wait:.0f}s (reset in {reset_ms/1000:.0f}s)',
                    flush=True,
                )
                await asyncio.sleep(wait)
                continue

            print(f'[qqbot] connecting (remaining sessions: {remaining})', flush=True)

            async with websockets.connect(gw, ping_interval=30) as ws:
                hello = json.loads(await ws.recv())
                interval = hello.get('d', {}).get('heartbeat_interval', 45000) / 1000

                identify = {
                    'op': 2,
                    'd': {
                        'token': f'QQBot {token}',
                        'intents': INTENTS,
                        'shard': SHARD,
                    },
                }
                await ws.send(json.dumps(identify))

                # Wait for READY
                p = json.loads(await ws.recv())
                if p.get('t') == 'READY':
                    sid = p['d'].get('session_id', '')
                    user = p['d'].get('user', {}).get('username', '?')
                    print(f'[qqbot] READY — user={user} session={sid}', flush=True)
                    save_session(sid)
                    save_state(websocket='connected', bot_name=user, session_id=sid)
                else:
                    print(f'[qqbot] unexpected identify response: {json.dumps(p)[:200]}', flush=True)
                    continue

                # Heartbeat
                async def heartbeat():
                    while True:
                        await asyncio.sleep(interval - 5)
                        try:
                            await ws.send(json.dumps({'op': 1, 'd': None}))
                        except Exception:
                            break

                hb_task = asyncio.create_task(heartbeat())

                # Message loop
                async for raw in ws:
                    p = json.loads(raw)
                    op = p.get('op', 0)

                    if op == 11:  # Heartbeat ACK
                        continue
                    if op == 7:  # Reconnect
                        print('[qqbot] server requested reconnect', flush=True)
                        break
                    if op != 0:  # Not a dispatch
                        continue

                    t = p.get('t', '')
                    d = p.get('d', {})

                    if t not in ('C2C_MESSAGE_CREATE', 'GROUP_AT_MESSAGE_CREATE'):
                        continue

                    is_private = t == 'C2C_MESSAGE_CREATE'
                    uid = d.get('author', {}).get('id', '') if is_private else d.get('author', {}).get('member_openid', '')
                    gid = '' if is_private else d.get('group_openid', '')
                    content = d.get('content', '')

                    print(f'[qqbot] {"PM" if is_private else "Group"} from {uid}: {content[:80]}', flush=True)
                    save_state(last_message_time=time.strftime('%Y-%m-%d %H:%M:%S'))

                    reply = await forward_to_mother(content, uid)
                    if reply:
                        target = uid if is_private else gid
                        msg_type = 'private' if is_private else 'group'
                        msg_id = '' if is_private else d.get('id', '')
                        loop = asyncio.get_running_loop()
                        await loop.run_in_executor(
                            None,
                            lambda: send_reply(reply, msg_type, target, token, msg_id),
                        )

                hb_task.cancel()
                try:
                    await hb_task
                except asyncio.CancelledError:
                    pass

        except Exception as e:
            print(f'[qqbot] connection error: {e}', flush=True)
            save_state(websocket='disconnected', last_error=str(e)[:200])
            await asyncio.sleep(5)


async def main():
    if not APPID or not SECRET:
        print('[qqbot] QQ_BOT_APPID or QQ_BOT_SECRET not set', flush=True)
        sys.exit(1)
    print(f'[qqbot] starting — appid={APPID[:4]}... mother={MOTHER_URL}', flush=True)
    await connect_websocket()


if __name__ == '__main__':
    asyncio.run(main())
