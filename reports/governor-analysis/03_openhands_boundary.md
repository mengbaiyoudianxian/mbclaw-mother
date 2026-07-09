# 任务三：OpenHands Action/Permission/Recovery 分析

## 属于 Governor 的设计

| OpenHands 组件 | 说明 | 为什么属于 Governor |
|---------------|------|-------------------|
| `AppConversationStartTaskService` | Task 生命周期: search/count/get/save/delete | Task 状态管理 → Governor 的 Task 追踪 |
| `Injector` 依赖注入 | 服务实例管理 | Governor 的模块调度 |
| `conversation_secret_enricher.py` | 密钥注入 | Governor 的敏感数据管控 |
| `hook_loader.py` | 生命周期钩子 | Governor 的 before/after 钩子 |
| `skill_loader.py` | 技能加载 | Governor 的 Capability 注册管理 |

## 属于 Runtime 的设计（不属于 Governor）

| OpenHands 组件 | 说明 | 为什么属于 Runtime |
|---------------|------|-------------------|
| `app_conversation_service.py` | 会话 CRUD | Session 管理 → Runtime session.py |
| `live_status_app_conversation_service.py` | 实时状态 | 状态推送 → Runtime stream.py |
| `app_conversation_router.py` | HTTP 路由 | API 层 → 不属于 Governor |
| `app_conversation_models.py` | 数据模型 | Model → 不属于 Governor |
| `sandbox/` | 沙箱 | 隔离执行 → Compute (独立模块) |

## Governor vs Runtime 边界

```
Governor 职责:
  - 权限决策: 这个操作允不允许？
  - 风险评估: 这个操作有多危险？
  - 执行策略: allow/deny/ask？
  - 恢复策略: 失败了怎么办？
  - 审计追踪: 谁做了什么？

Runtime 职责:
  - 执行流程: 消息→LLM→工具→回复
  - 会话管理: Session 创建/恢复/关闭
  - 上下文构建: Prompt 拼接
  - 工具分发: 调用 CapabilityRegistry
```

## 迁移成本

0 天（设计参考，不迁移代码）

## 推荐指数

★★★☆☆ — Injector/Hook/Skill 加载模式值得参考
