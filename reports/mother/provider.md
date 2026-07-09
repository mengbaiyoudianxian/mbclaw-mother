# Mother Provider 分析

## 作用

Provider 层负责 LLM 调用的 Key 管理和路由。Mother 中有三个不同层次的 LLM 调用入口，各自有独立的 Key 获取逻辑。

## 当前实现

涉及文件：`app/llm.py`、`app/llm_router.py`、`app/providers.py`、`app/token_pool.py`

### LLMClient（llm.py）— 会话摘要用
- OpenAI-compatible 客户端
- 构造函数支持手动传入 base_url/api_key/model
- **fallback 优先级**：构造函数参数 → 环境变量（MBCLAW_LLM_*）→ TokenPool.get_best_for_llm()
- 两个方法：chat()（简单对话）、summarize_session()（结构化摘要，含 retry）
- 默认 model: gpt-4o-mini，默认 base_url: api.openai.com

### LLMRouter（llm_router.py）— MBOS Core 用
- 三模式：mock / env key / tokenpool
- call() 统一入口
- 被 MBOSCore 调用
- 与 LLMClient 完全独立，功能重复

### providers.py — 数据库模型级 Provider 管理
- 基于 ModelProfile 表管理多个 Provider
- 内置 3 个默认：openai-gpt4o、openai-gpt4o-mini、local-ollama
- get_best_client() 按 priority 降序查找第一个可用 Provider
- 几乎不被调用（api.py 中有 /providers 端点）

### TokenPool（token_pool.py）— 用户贡献 Key 池
- 从 heartbeat_logs 加载用户 Key
- 从 miclaw_instances.json 加载 MiClaw 实例 Key
- 测试 Key 可用性（真实对话测试）
- pick() 选择策略：MiClaw 实例优先 → 使用次数少的优先
- 全局单例
- 状态持久化到 /var/lib/mbclaw/token_pool.json

## LLM 调用链路图

```
API请求
├── MotherRuntime.run() → _build_candidates() → TokenPool.get_pool().keys (直接遍历)
├── agent_run() → httpx 直接调用 LLMClient 的 base_url/api_key (不走任何路由)
├── MBOSCore.handle() → LLMRouter.call() → TokenPool.get_pool()
├── gateway_agent → MotherRuntime
└── pipeline/close_session → LLMClient.summarize_session()
```

## 存在问题

1. **三层 Key 管理各自为政**：LLMClient 的 fallback、LLMRouter 的路由、MotherRuntime 的 _build_candidates 是三套独立逻辑
2. **TokenPool 与 LLMClient 循环依赖风险**：LLMClient fallback 调 TokenPool，TokenPool 的 test_key 用 httpx 调 API
3. **providers.py 几乎不被使用**：ModelProfile 表有 CRUD 但无消费方
4. **LLMRouter 几乎不被使用**：MBOSCore 是独立组件，实际运行不走这条路径
5. **TokenPool 没有抽象层**：直接操作心跳文件，与部署环境强耦合
6. **LLMClient 异常处理不一致**：chat() 吞异常返回字符串，summarize_session() 抛 LLMError

## 建议

1. 合并 LLMClient、LLMRouter 为一个统一的 ProviderManager
2. ProviderManager 应作为唯一 LLM 调用入口，所有模块通过它调用
3. TokenPool 应作为 ProviderManager 的一个 Backend 实现
4. 废弃 providers.py（或合并入 ProviderManager 的静态配置部分）
5. 增加统一的熔断/重试/降级策略

## 以后是否保留

- **LLMClient**：保留但重构，作为统一客户端基础
- **LLMRouter**：废弃，合并入 LLMClient
- **providers.py**：废弃或合并
- **TokenPool**：保留设计思路，但需要重构为 Provider Backend 实现
