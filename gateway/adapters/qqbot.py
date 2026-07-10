"""QQ官方Bot API v2 Adapter — AppID+Secret → AccessToken → WebSocket"""
from .. import AdapterBase
import asyncio, json, os, time, requests

class QQBotAdapter(AdapterBase):
    name = 'qq'
    _app_id: str = ''
    _secret: str = ''
    _token: str = ''
    _token_expires: float = 0
    _ws = None
    _heartbeat_task = None
    _seq: int = 0

    def _get_access_token(self) -> str:
        """用 AppID + AppSecret 换取 access_token (有效期2小时)"""
        if self._token and time.time() < self._token_expires - 60:
            return self._token
        try:
            _pref = 'sandbox.' if getattr(self, '_sandbox', False) else ''
            r = requests.post(f'https://{_pref}bots.qq.com/app/getAppAccessToken',
                json={'appId': self._app_id, 'clientSecret': self._secret}, timeout=10)
            data = r.json()
            self._token = data.get('access_token', '')
            self._token_expires = time.time() + int(data.get('expires_in', 7200))
            print(f'[qqbot] token refreshed, expires in {data.get("expires_in")}s', flush=True)
            return self._token
        except Exception as e:
            print(f'[qqbot] token error: {e}', flush=True)
            return ''

    async def start(self) -> None:
        self._app_id = os.environ.get('QQ_BOT_APPID', '')
        self._secret = os.environ.get('QQ_BOT_SECRET', '')
        self._sandbox = os.environ.get('QQ_BOT_SANDBOX', '1') == '1'
        print(f'[qqbot] DEBUG: appid={self._app_id[:4]}... secret_len={len(self._secret)} sandbox={self._sandbox}', flush=True)
        if not self._app_id or not self._secret:
            print('[qqbot] missing AppID or Secret, cannot start')
            return
        token = self._get_access_token()
        if not token:
            print('[qqbot] failed to get access token', flush=True)
            return
        try:
            import websockets
            _prefix = 'sandbox.' if self._sandbox else ''
            # 1. 获取Gateway
            gw = f'wss://{_prefix}api.sgroup.qq.com/websocket/'
            try:
                r = requests.get(f'https://{_prefix}api.sgroup.qq.com/gateway', timeout=5)
                gw = r.json().get('url', gw)
            except: pass
            # 2. 连接
            self._ws = await websockets.connect(gw, ping_interval=30)
            # 3. Hello
            hello = json.loads(await self._ws.recv())
            interval = hello.get('d', {}).get('heartbeat_interval', 45000)
            self._seq = hello.get('s', 0)
            # 4. Identify
            await self._ws.send(json.dumps({
                'op': 2, 'd': {
                    'token': f'QQBot {token}',
                    'intents': 402653184,  # original working value: INTERACTION | MESSAGE_AUDIT
                    'shard': [0, 1],
                    'properties': {},
                }
            }))
            # 5. 等待 READY
            async for raw in self._ws:
                p = json.loads(raw)
                if p.get('t') == 'READY':
                    print(f"[qqbot] ready! session={p['d'].get('session_id','')}", flush=True)
                    break
            # 6. 心跳
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(interval))
            # 7. 消息监听
            asyncio.create_task(self._listen())
        except Exception as e:
            print(f'[qqbot] start failed: {e}', flush=True)

    async def stop(self) -> None:
        if self._heartbeat_task: self._heartbeat_task.cancel()
        if self._ws:
            try: await self._ws.close()
            except: pass

    async def _heartbeat_loop(self, interval_ms: int):
        while True:
            await asyncio.sleep(interval_ms / 1000)
            try:
                await self._ws.send(json.dumps({'op': 1, 'd': self._seq}))
            except: break

    async def _listen(self):
        async for raw in self._ws:
            try:
                payload = json.loads(raw)
                op = payload.get('op', 0)
                if op == 11: continue  # Heartbeat ACK
                self._seq = payload.get('s', self._seq)
                if op == 7:  # Reconnect
                    print('[qqbot] server requested reconnect')
                    break
                if op != 0: continue
                t = payload.get('t', '')
                d = payload.get('d', {})

                if op == 0 and t:
                    print(f'[qqbot] event t={t}')
                if t in ('C2C_MESSAGE_CREATE', 'GROUP_AT_MESSAGE_CREATE'):
                    print(f'[qqbot] received {t} from {d.get("author",{}).get("id","?")} content={d.get("content","")[:100]}')
                if t == 'C2C_MESSAGE_CREATE':
                    msg = {
                        'channel': 'qq',
                        'message_type': 'private',
                        'user_id': d.get('author', {}).get('id', ''),
                        'raw_message': d.get('content', ''),
                        'msg_id': d.get('id', ''),
                    }
                    if self._on_message:
                        asyncio.create_task(self._process(msg, d))

                elif t == 'GROUP_AT_MESSAGE_CREATE':
                    msg = {
                        'channel': 'qq',
                        'message_type': 'group',
                        'user_id': d.get('author', {}).get('member_openid', ''),
                        'group_openid': d.get('group_openid', ''),
                        'raw_message': d.get('content', ''),
                        'msg_id': d.get('id', ''),
                    }
                    if self._on_message:
                        asyncio.create_task(self._process(msg, d))
            except Exception as e:
                print(f'[qqbot] listen error: {e}')

    async def _process(self, msg: dict, d: dict):
        try:
            reply = await self._on_message(msg)
            token = self._get_access_token()
            if msg['message_type'] == 'private':
                uid = d.get('author', {}).get('id', '')
                _pref = 'sandbox.' if self._sandbox else ''
                requests.post(f'https://{_pref}api.sgroup.qq.com/v2/users/{uid}/messages',
                    headers={'Authorization': f'QQBot {token}', 'Content-Type': 'application/json'},
                    json={'content': reply[:2000], 'msg_type': 0}, timeout=10)
            else:
                gid = d.get('group_openid', '')
                _pref = 'sandbox.' if self._sandbox else ''
                requests.post(f'https://{_pref}api.sgroup.qq.com/v2/groups/{gid}/messages',
                    headers={'Authorization': f'QQBot {token}', 'Content-Type': 'application/json'},
                    json={'content': reply[:2000], 'msg_type': 0, 'msg_id': d.get('id')}, timeout=10)
            print(f'[qqbot] replied to {msg["message_type"]}')
        except Exception as e:
            print(f'[qqbot] reply error: {e}')

    async def send(self, target: str, message: str, meta: dict = None) -> bool:
        token = self._get_access_token()
        msg_type = (meta or {}).get('message_type', 'private')
        try:
            path = f'/v2/groups/{target}/messages' if msg_type == 'group' else f'/v2/users/{target}/messages'
            _pref = 'sandbox.' if self._sandbox else ''
            r = requests.post(f'https://{_pref}api.sgroup.qq.com{path}',
                headers={'Authorization': f'QQBot {token}', 'Content-Type': 'application/json'},
                json={'content': message[:2000], 'msg_type': 0}, timeout=10)
            return r.status_code == 200
        except: return False
