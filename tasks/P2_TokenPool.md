# P2_TokenPool — TokenPool 改造

## 目标
让 Mother 通过 HTTP API 正确使用 TokenPool 服务，消除 Mother 内置 TokenPool 副本，建立清晰的服务边界。

## 子任务 (以后再拆)

### 2.1 TokenPool 服务增强
- [ ] 统一 API 响应格式
- [ ] 增加 `/v1/chat/completions` 端点（作为 Mother 的主要调用入口）
- [ ] 增加 Key 选择建议 API（供 Mother 做最终决策）
- [ ] 修复路由冲突（bridge_manager.py 两个 catch-all）

### 2.2 Mother 接入 TokenPool
- [ ] 创建 `app/llm/tokenpool_client.py` — TokenPool HTTP 客户端
- [ ] 支持 base_url 配置（默认 localhost:8100）
- [ ] 支持 fallback 到本地环境变量
- [ ] 替换 Mother 内置 token_pool.py 的所有调用点

### 2.3 限流 & 熔断统一
- [ ] 合并 ratelimit.py 和 user_ratelimit.py
- [ ] 统一冷却状态存储到一个数据库

### 2.4 统计统一
- [ ] 合并 MetricsHub 和 MetricsTracker
- [ ] 关键指标持久化

### 2.5 测试
- [ ] call_with_fallback 单元测试
- [ ] GuardRail 单元测试
- [ ] 评分算法单元测试

## 依赖
- P1_Runtime (TokenPool HTTP 客户端在 P1 中创建)

## 禁止
- 禁止新增调度算法
- 禁止新增 Provider 类型
- 禁止修改控制面板
