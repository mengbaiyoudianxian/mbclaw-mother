# Scheduler — LLM 调度层

## 一句话定位
LLM Provider 调度的唯一入口，封装 TokenPool HTTP 交互。

## 职责
- 调用 TokenPool HTTP API 获取 LLM 响应
- 管理 Provider fallback 策略
- TokenPool 不可用时本地降级

## 接口规范

```python
class Scheduler:
    def request_llm(
        messages: list[dict],
        task_type: str = "chat",
        strategy: str = "balanced",
    ) -> LLMResponse: ...

@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    tokens_used: int
    latency_ms: float
```

## TokenPool HTTP 调用

```
POST http://${TOKENPOOL_HOST}:8100/v1/chat/completions
Headers: Authorization: Bearer ${MBCLAW_TP_KEY}
Body: {"model": "...", "messages": [...], "max_tokens": 2048, "temperature": 0.3}
```

## Fallback 策略

```
TokenPool 可用 → 使用 TokenPool
TokenPool 不可达 → 本地环境变量 MBCLAW_LLM_*
本地也无 → 抛出 LLMError
```

## 依赖
- TokenPool 服务 (HTTP, 端口 8100)
- 环境变量 (fallback)

## 代码复用
从 `mother_runtime.py:_build_candidates()` 提取，改为 HTTP 调用。
删除: `app/token_pool.py`, `app/llm_router.py`
