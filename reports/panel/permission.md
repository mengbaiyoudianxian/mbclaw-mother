# Control Panel 权限分析

## 认证机制

### 管理员认证
- **算法**：SHA256(salt + password)
- **存储**：admin.json
- **默认密码**：admin（首次登录后提示修改）
- **会话**：Cookie `mb_admin`，值为 `secrets.token_urlsafe(32)`
- **过期**：7 天
- **HttpOnly**：是
- **SameSite**：Lax

### 鉴权函数
```python
def require_admin(mb_admin: Optional[str] = Cookie(default=None)):
    if not _check_session(mb_admin):
        raise HTTPException(401, "未登录")
    return True
```

## 权限模型

控制面板采用**单用户 + 全权限**模型：
- 只有一个管理员账号（默认 admin）
- 登录后拥有所有权限
- 无角色分级（admin/user/readonly）

## API 鉴权覆盖

| API 路径 | 鉴权 | 备注 |
|----------|------|------|
| /admin/api/* | Cookie `mb_admin` | 管理 API |
| /api/admin/* | Cookie `mb_admin` | 管理 API（admin_api.py） |
| /bridge/miclaw/* | **无鉴权** | ⚠️ 公开访问 |
| /admin/client/debug/* | **无鉴权** | 设备直接调用，仅验证 code 匹配 |
| /upload | URL Token 参数 `t=` | Token 写死在环境变量 |
| /gateway/wechat/* | **无鉴权** | 公开 |
| /gateway/web/chat | **无鉴权** | 公开 |
| /health | **无鉴权** | 健康检查 |
| /hotfix/* | **无鉴权** | 热修复文件下载 |

## 设备鉴权

设备通过以下方式标识：
- **调试码（code）**：格式 `mb-{hex}`，由客户端生成
- **心跳验证**：设备定期 POST 心跳到 `/admin/client/debug/heartbeat`
- **命令验证**：命令下发时通过 code 匹配设备，无额外鉴权

## 文件上传鉴权

- **Token 机制**：URL 参数 `t=mengbai`（环境变量 `MBCLAW_UPLOAD_TOKEN` 配置）
- **无用户关联**：所有上传使用同一个 Token
- **路径安全**：通过 `_safe_upload_path` 防止目录穿越

## 存在问题

1. **单用户无角色**：无法区分管理员和只读用户
2. **MiClaw Bridge 路由公开**：任何人可以创建实例、代理 LLM 请求
3. **设备调试 API 无鉴权**：知道调试码就能向设备下发命令
4. **上传 Token 写死**：`mengbai` 硬编码，泄露后无法快速吊销
5. **无审计日志**：管理操作无记录
6. **Cookie 无 SameSite=Strict**：存在 CSRF 风险（虽然影响小）

## 建议

1. 为 /bridge/miclaw/* 增加基础鉴权
2. 设备命令下发增加签名验证
3. 上传 Token 支持轮换和多 Token
4. 增加管理员操作日志
5. 考虑引入简单的角色系统（至少 admin + readonly）
