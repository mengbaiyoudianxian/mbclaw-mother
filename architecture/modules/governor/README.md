# Governor — 编排层

## 一句话定位
Runtime 的最高指挥官，管理会话生命周期，协调所有模块。

## 职责
- 会话创建/获取/关闭
- 编排 Pipeline 四阶段：Ingress → Planning → Execution → Egress
- 模块间事件路由
- 错误处理和降级策略

## 接口规范

```python
class Governor:
    def create_session(user_id: str, channel: str) -> int: ...
    def get_session(session_id: int) -> Session: ...
    def close_session(session_id: int) -> CloseResult: ...
    def process_message(msg: StandardMessage) -> Reply: ...
    def reset_session(session_id: int) -> None: ...
```

## 生命周期
- 进程级单例
- Session 状态存储在 Context Engine 中

## 依赖
- Context Engine (获取/更新上下文)
- Planner (决策)
- Memory (记忆检索)
- Scheduler (LLM 调用)
- Gateway (消息收发)

## 代码复用
从 `mother_runtime.py` 的 `_get_session()` 和 `api.py` 的会话 CRUD 提取。
当前文件: `app/mother_runtime.py:176-188`, `app/api.py:90-137`
