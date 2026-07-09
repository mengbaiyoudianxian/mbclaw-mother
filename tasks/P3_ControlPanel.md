# P3_ControlPanel — 控制面板改造

## 目标
统一数据存储，增强安全性，整理代码结构。

## 子任务 (以后再拆)

### 3.1 数据存储统一
- [ ] 将 admin JSON 文件迁移到 SQLite
  - admin.json → admin_config 表
  - users.json → 与 Mother sessions 表合并或独立
  - stats.json → 使用 TokenPool call_log 或独立 stats 表
  - bugs.json / features.json → 独立表
- [ ] heartbeat_logs 保持 JSON（写入频率高，SQLite 不适合）

### 3.2 安全性增强
- [ ] /bridge/miclaw/* 增加鉴权
- [ ] 设备调试命令增加签名验证
- [ ] 上传 Token 支持配置多个
- [ ] Cookie SameSite 改为 Strict

### 3.3 代码整理
- [ ] 合并 admin/router.py 和 admin/admin_api.py
- [ ] 删除 14 个 .bak 备份文件
- [ ] 删除重复 HTML 文件（保留 panel_one.html）
- [ ] 前端 JS 模块化（panel.js 拆分）

### 3.4 API 清理
- [ ] 删除重复的 /api/mother/uploads/{code} 定义
- [ ] 统一 API 前缀规范
- [ ] 补充 API 文档

### 3.5 功能增强（可选）
- [ ] 增加只读管理员角色
- [ ] 增加操作审计日志
- [ ] 设备列表分页/搜索优化

## 依赖
- P1_Runtime（SQLite 迁移可能涉及 Mother 的数据模型）
- P2_TokenPool（TokenPool API 统计统一）

## 禁止
- 禁止重写前端（不用 React/Vue）
- 禁止修改 MotherRuntime 功能
- 禁止修改 TokenPool 服务
