# Control Panel 页面分析

## 页面列表

控制面板是单页应用 (SPA)，通过前端 JS 切换 Tab 实现多页面。主文件：`panel_one.html` + `panel.js` + `panel_auth.js`。

### 1. 登录页 (`/admin/login`)
- 内联 HTML（main.py 中硬编码）
- 表单：账号(mengbai) + 密码
- POST `/admin/api/login` → Set-Cookie `mb_admin`
- 登录成功 → 跳转 `/admin2`

### 2. Dashboard（概览）
- **统计卡片**：总请求数、总 Token、总用户数、在线设备、今日新增、Root 用户、Key 可用数、错误数、Provider 配置数、运行时间
- **服务器状态**：多台服务器在线状态（母体机、工具池、跳板机、备用站、母体、云电脑、小米手机）
- **调用管理**：用户调用记录表格（用户ID、调用次数、最后在线、IP、操作）
- **API**：`GET /admin/api/overview` + `GET /admin/api/users`

### 3. 设备管理
- **设备列表**：从 heartbeat_logs 读取所有设备
- **设备详情**：调试码、QQ、型号、品牌、IP、版本、权限(root/无障碍/悬浮窗)、收集开关、最后心跳
- **设备操作**：封禁/解封、发送收集指令(照片/微信/对话)
- **调试命令**：向指定设备下发命令、查看结果
- **API**：`GET /admin/client/debug/devices` + `POST /admin/client/debug/send`

### 4. TokenPool 管理
- **Key 列表**：显示所有用户贡献的 Key（从 heartbeat_logs 读取）
- **Key 测试**：单个测试、全量检测
- **Key 状态**：在线/离线、测试结果(OK/Fail)
- **Token 池统计**：总量、可用数、失败数
- **API**：`GET /admin/api/token-pool` + `POST /admin/api/token-pool/test-key`

### 5. MiClaw Bridge 管理
- **实例列表**：所有 MiClaw 实例（ID、用户、设备、状态、模型、Token 用量）
- **实例操作**：销毁、暂停
- **登录状态**：等待登录 / 已就绪 / 备用模式
- **API**：`GET /admin/api/miclaw-instances` + `POST /admin/api/miclaw-instances/{iid}/destroy`

### 6. 统计 & 日志
- **请求统计**：按天/按 Provider 的请求量、Token 量、错误率
- **下载统计**：APK 下载次数
- **服务器指标**：磁盘、内存、网络、CPU、运行时间、DB 大小
- **日志查看**：系统运行日志
- **API**：`GET /api/admin/metrics` + `GET /api/admin/downloads`

### 7. Bugs / Features 反馈
- **Bugs 列表**：状态(open/resolved)、优先级、投票数
- **Features 列表**：状态(pending/resolved)、优先级、投票数
- **操作**：Pin/Resolve/Delete/SetVotes
- **API**：`GET /admin/api/bugs` + `POST /admin/api/bugs/{bid}/pin`

### 8. 文件上传
- **上传页**：`/upload` (token 鉴权)
- **功能**：拖拽/选择/粘贴上传，支持目录结构
- **大小限制**：200MB

### 9. Settings
- **改密码**：`POST /admin/api/change-password`
- **版本管理**：设置客户端最新版本、下载地址
- **API**：`POST /admin/client/version/set`

## 前端架构

```
panel_one.html (主 SPA)
├── panel.js (核心逻辑)
│   ├── 登录/认证管理
│   ├── Tab 切换
│   ├── 数据加载/渲染
│   └── API 调用封装
└── panel_auth.js (认证模块)
```

## 存在问题

1. **前端代码量极大**：panel_one.html + panel.js 估计数千行，无模块化
2. **JSON 文件并发写入无锁**：多 Tab 同时操作可能数据不一致
3. **设备管理依赖 heartbeat_logs 目录扫描**：设备多时性能下降
4. **无分页或虚拟滚动**：设备列表全量渲染
5. **Bugs/Features 数据存储为 JSON 文件**：无可视化面板，纯管理后台
