# Control Panel API 分析

## API 总览

控制面板的 API 分散在 7 个路由文件中，共约 60+ 个端点。

## 按功能分类

### 认证相关（admin/router.py）
| 方法 | 路径 | 功能 |
|------|------|------|
| POST | /admin/api/login | 登录 |
| POST | /admin/api/logout | 登出 |
| POST | /admin/api/change-password | 修改密码 |

### Dashboard（admin/router.py）
| 方法 | 路径 | 功能 |
|------|------|------|
| GET | /admin/api/overview | 总览统计 |
| GET | /admin/api/users | 用户列表 |

### TokenPool 管理（admin/router.py）
| 方法 | 路径 | 功能 |
|------|------|------|
| GET | /admin/api/token-pool | Token 池列表（读 heartbeat_logs） |
| POST | /admin/api/token-pool/test-key | 单个 Key 测试（调 TokenPool API） |
| POST | /admin/api/token-pool/test-all | 全量检测（调 TokenPool API） |

### MiClaw 桥接（admin/bridge_manager.py）
| 方法 | 路径 | 功能 |
|------|------|------|
| POST | /bridge/miclaw/apply | 申请实例 |
| GET | /bridge/miclaw/login/{id} | 登录页面 |
| POST | /bridge/miclaw/login/{id} | 提交凭证 |
| GET | /bridge/miclaw/status | 轮询实例状态 |
| ANY | /bridge/miclaw/v1/{path} | LLM 代理转发 |
| POST | /bridge/miclaw/destroy | 销毁实例 |
| POST | /bridge/miclaw/stop | 暂停实例 |

### 设备管理（admin/debug_api_v2.py）
| 方法 | 路径 | 功能 |
|------|------|------|
| POST | /admin/client/debug/heartbeat | 设备心跳上报 |
| GET | /admin/client/debug/cmd | 设备拉取命令 |
| POST | /admin/client/debug/result | 设备上报命令结果 |
| POST | /admin/client/debug/send | 向设备下发命令 |
| POST | /admin/client/debug/send-collect | 向所有在线设备下发收集指令 |
| GET | /admin/client/debug/devices | 设备列表 |
| GET | /admin/client/debug/results | 命令结果列表 |

### 版本管理（admin/version_api.py）
| 方法 | 路径 | 功能 |
|------|------|------|
| GET | /admin/client/version | 客户端版本检测 |
| POST | /admin/client/version/set | 设置最新版本 |

### 统计 & 服务器（admin/admin_api.py）
| 方法 | 路径 | 功能 |
|------|------|------|
| GET | /api/admin/metrics | 服务器指标（磁盘/内存/网络） |
| GET | /api/admin/downloads | 下载统计 |
| POST | /api/admin/downloads/track | 记录下载 |

### Bugs / Features（admin/router.py）
| 方法 | 路径 | 功能 |
|------|------|------|
| GET | /admin/api/bugs | Bugs 列表 |
| POST | /admin/api/bugs | 提交 Bug |
| POST | /admin/api/bugs/{bid}/pin | 置顶 |
| POST | /admin/api/bugs/{bid}/resolve | 解决 |
| POST | /admin/api/bugs/{bid}/delete | 删除 |
| GET/POST | /admin/api/features | 同上 |

### 文件上传（admin/upload.py）
| 方法 | 路径 | 功能 |
|------|------|------|
| GET | /upload | 上传页面 |
| POST | /upload/api/upload | 上传文件 |

### 扩展（admin/extra.py）
| 方法 | 路径 | 功能 |
|------|------|------|
| POST | /admin/client/account/sync | 账号同步 |
| GET | /admin/client/account/lookup | 账号查找 |
| GET | /admin/client/tools/list | 工具市场列表 |
| POST | /admin/client/tools/upload | 工具上传 |
| GET | /admin/client/perm-template | 权限模板 |

### 外部入口（main.py）
| 方法 | 路径 | 功能 |
|------|------|------|
| GET | /admin, /admin2 | 管理面板首页 |
| GET | /gateway/wechat/link | 微信扫码登录页 |
| GET | /gateway/wechat/qr | 微信二维码 |
| GET | /gateway/wechat/poll | 扫码状态轮询 |
| POST | /gateway/wechat/login | 微信登录 |
| POST | /gateway/web/chat | Web 聊天 |

## 重复端点

1. **`/api/mother/uploads/{code}` 定义了两次**（api.py 第 292 行和第 316 行，完全相同）
2. **`/bridge/miclaw/{path}` 路由冲突**：bridge_manager.py 第 179 行和第 286 行都定义了 catch-all 路由
3. **TokenPool 端点重复**：admin/router.py 和 Mother 的 token_pool.py 都有 Token 列表/测试功能

## 鉴权覆盖

| API 组 | 鉴权方式 |
|--------|---------|
| /admin/api/* | Cookie mb_admin（require_admin 依赖） |
| /bridge/miclaw/* | 无鉴权（公开） |
| /admin/client/debug/* | 无鉴权（设备直接调用） |
| /upload | URL Token 参数 |
| /gateway/wechat/* | 无鉴权（公开） |

## 存在问题

1. **部分管理 API 无鉴权**：MiClaw 桥接端点全部公开
2. **TokenPool 管理 API 调外部服务**：`_tp_req` 调用 `http://8.147.69.152:8100`，硬编码地址
3. **路由冲突风险**：两个 catch-all 路由（/bridge/miclaw/{path}）
