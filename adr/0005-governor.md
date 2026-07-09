## ADR-005: Governor 单一入口

Status: Accepted (2026-07-09)

### 决策
Governor.process_message() 作为所有渠道消息的唯一入口，编排四阶段 Pipeline。

### 替代方案
保持多入口(当前) -> 拒绝: 分散不利于维护和测试。
