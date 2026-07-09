# 任务七：TokenPool 生命周期

## Key 完整生命周期

```
[1] Discover
    发现新 Key:
    ├── 心跳文件: /var/lib/mbclaw/heartbeat_logs/mb-*.json
    ├── MiClaw 实例: /var/lib/mbclaw/miclaw_instances.json
    ├── 管理员手动添加: POST /tokenpool/keys
    └── FreeLLMAPI 源: (未来)
    输出: ProviderKey (status=unknown)
    │
    ▼
[2] Register
    注册到 TokenPool:
    ├── 检查去重 (相同 base_url + api_key 跳过)
    ├── 分类: commercial / user_contributed / admin_private / free_proxy
    ├── 写入 DB (ProviderKey 表)
    └── status = unknown
    │
    ▼
[3] Initial Test
    首次健康检查:
    ├── HTTP POST /chat/completions "hi" max_tokens=5
    ├── 200 + 有内容 → status=healthy, health_score=1.0
    ├── 401/403 → status=invalid, enabled=False
    ├── 5xx/timeout → status=error, retry later
    └── 写入 tested_at + health_score
    │
    ▼
[4] Health Monitoring
    定期健康检查 (每 5 分钟):
    ├── healthy → 验证仍可用 → 更新 health_score
    ├── degraded → 测试是否恢复 → 降分或恢复
    ├── error → 重试 3 次 → 仍失败 → disabled
    └── unknown → 与 initial test 相同
    自动 disable: 连续 3 次 invalid → enabled=False
    │
    ▼
[5] Scoring
    计算 health_score:
    health_score = latency_score(0.3) + success_rate(0.5) + penalty_decay(0.2)
    每次健康检查后更新
    每次 Scheduler 调用后更新 (影响 success_rate)
    │
    ▼
[6] Scheduler 请求
    Scheduler 调用 TokenPool.get_keys(filter):
    ├── filter: enabled=True, status in (healthy, degraded, unknown)
    ├── 排除: cooldown 中 + rate limit 超限
    ├── 排序: provider.priority + health_score DESC + Round-Robin
    └── 返回: 候选 Key 列表
    │
    ▼
[7] Key 使用
    Scheduler 选定 Key 后调用:
    ├── TokenPool.allocate_budget(key_id, estimated_tokens)
    │   └── 检查剩余预算 → ok/insufficient
    ├── Scheduler 执行 HTTP 调用
    └── TokenPool.record_metrics(key_id, result):
        ├── success → usage_count++, success_rate↑, latency↓
        ├── 429 → penalty +3, cooldown 30s
        ├── 5xx → error_count++, cooldown 30s, success_rate↓
        ├── timeout → no penalty, no cooldown, retry
        └── 4xx → error_count++, 不重试
    │
    ▼
[8] Cooldown
    Key 被 cooldown 后:
    ├── Scheduler 跳过该 Key
    ├── Cooldown 到期 → penalty 衰减 → 恢复可用
    └── 连续 cooldown → penalty 累积 → disabled
    │
    ▼
[9] 429 惩罚
    Penalty Manager:
    ├── 429 命中 → penalty += 3 (max 10)
    ├── 成功一次 → penalty -= 1
    ├── 2 分钟无 429 → penalty -= 1 (时间衰减)
    └── penalty = 0 → 完全恢复
    │
    ▼
[10] Auto Disable
    自动禁用条件:
    ├── 连续 3 次 invalid (401/403) → enabled=False
    ├── penalty = 10 持续 10 分钟 → enabled=False
    ├── 连续 10 次 5xx → enabled=False
    └── 手动禁用: POST /tokenpool/keys/{id}/disable
    │
    ▼
[11] Recovery
    恢复:
    ├── 手动启用: POST /tokenpool/keys/{id}/enable
    ├── auto-recovery: penalty 衰减到 0 → degraded → 测试通过 → healthy
    └── 重新测试: POST /tokenpool/keys/{id}/test
    │
    ▼
[12] Metrics
    每日统计:
    ├── 每日汇总: KeyMetrics 表 (按 key_id + date)
    ├── 昨日统计: get_yesterday()
    ├── Provider 统计: get_provider_stats()
    └── 管理员查看: GET /tokenpool/stats/*
```

## Key 状态机

```
                    ┌─────────────┐
                    │   unknown   │  ← 新发现
                    └──────┬──────┘
                           │ initial test
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         ┌────────┐  ┌──────────┐  ┌───────┐
         │ healthy │  │ degraded │  │ error │
         └───┬────┘  └────┬─────┘  └───┬───┘
             │            │            │
             │  success   │  3次失败   │ 连续3次
             │  ────────► │  ────────► │ ────────► disabled
             │            │            │
             │  恢复      │  penalty=0 │
             │ ◄────────  │ ◄────────  │ ◄── 手动启用
             │            │            │
             └────────────┴────────────┘
                  429 cooldown
                  → degraded (temporary)
```

## Scheduler 与 TokenPool 交互时序

```
Scheduler                    TokenPool
    │                            │
    │── get_keys(filter) ──────► │
    │                            │── 查询 DB + 评分
    │◄─ [ProviderKey, ...] ────  │
    │                            │
    │── allocate_budget(kid) ──► │
    │◄─ ok ────────────────────  │
    │                            │
    │── HTTP call ────────────── │  (Scheduler 自己发起)
    │                            │
    │── record_metrics(kid, r)─► │
    │                            │── 更新 health_score/penalty/cooldown
    │◄─ done ──────────────────  │
```
