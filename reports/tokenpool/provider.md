# TokenPool Provider 分析

## 作用

Provider 层管理 LLM API Key 的存储、加密、选择和调用。TokenPool 通过 Registry 持久化 Key，通过 Caller 实现统一调用与故障转移。

## 核心组件

### Registry (registry.py)
- SQLite 持久化，线程安全（threading.Lock）
- **加密存储**：AES-256-GCM 加密 api_key，内存中解密为明文
- **数据模型**：ProviderKey dataclass + (keys, key_stats, users, user_shared_keys, miclaw_accounts 等 10+ 表)
- **内置 Key**：7 个默认 Key (openai-gpt4o, openai-gpt4o-mini, anthropic-sonnet, deepseek-chat, qwen-plus, miclaw-bridge, local-ollama)
- **schema 自动升级**：ALTER TABLE 兼容旧数据库
- **schema 校验**：dataclass 字段与 DB 列一致性检查

### Caller (caller.py)
- **统一调用接口**：call_with_fallback(payload, task, budget, require_model, max_retries)
- **Token 估算**：hybrid rough (len/4) + content-type correction (Chinese 1.3x, code 1.5x)
- **模型过滤**：context 窗口检查、vision 能力检查、tool_use 能力检查
- **Provider 适配**：OpenAI-compatible 和 Anthropic 格式自动转换
- **故障转移**：按序尝试候选 Key，成功后清除冷却+记录metrics，失败后设置冷却+自学习
- **Key 脱敏**：日志中自动脱敏 sk- 前缀 Key
- **诊断报告**：全部失败时输出每个模型跳过原因

### Encryption (encryption.py)
- AES-256-GCM 加密
- encrypt() → (ciphertext, iv, tag)，decrypt(ciphertext, iv, tag) → 明文
- 基于 cryptography 库

## 调用流程

```
call_with_fallback(payload)
    ↓
1. pick_all(task) → scheduler.filter_candidates()
    ├── GuardRail: Quota → RateLimit → Circuit
    └── TASK_ROUTING 预排序
    ↓
2. estimate_tokens(messages, max_out)
    ├── rough = len(json) // 4
    ├── _detect_content_type(text)
    └── estimated = int(rough × factor) + max_out
    ↓
3. _filter_model() 逐模型检查
    ├── context 窗口是否够
    ├── 有图片 → vision >= 1
    └── 有工具 → tool_use >= 1
    ↓
4. 故障转移循环 (max_retries)
    ├── anthropic → _call_anthropic()
    ├── 其他 → _call_openai_compat()
    ├── 成功 → rl.clear_cooldown() + hub.record() + tracker.record()
    └── 失败 → rl.set_cooldown() + rl.learn_from_error()
    ↓
5. 返回 (response_dict, alias_used)
```

## 存在问题

1. **Caller 做了太多事**：token 估算、模型过滤、故障转移、metrics 记录全在一个函数中
2. **Context 窗口检查依赖硬编码画像**：BUILTIN_CAPABILITIES 只覆盖约 30 个模型
3. **Anthropic 适配不完整**：不支持 streaming、vision 格式转换、tool_use 格式转换
4. **Token 估算是粗略近似**：字符/4 对于中英文混合场景误差大
5. **无请求队列/优先级调度**：所有请求同等对待

## 以后是否保留

**保留核心设计，但需模块化**：
- Registry → 保留
- Caller → 拆分为 Caller + Filter + Adapter
- Encryption → 保留
