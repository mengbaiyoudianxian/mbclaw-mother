## ADR-002: HTTP 调用 TokenPool

Status: Accepted (2026-07-09)

### 决策
Mother 通过 POST http://tokenpool:8100/v1/chat/completions 调用 TokenPool。不再直接读文件系统。

### Fallback
TokenPool 不可用 -> 本地 MBCLAW_LLM_* 环境变量。
