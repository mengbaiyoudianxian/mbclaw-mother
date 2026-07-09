# 任务五：TokenPool 职责设计

> 明确边界，不与任何模块重复

---

## TokenPool 核心定位

TokenPool = 母体的"资源池"，存储和管理所有 LLM 调用资源。

```
           ┌──────────┐
           │TokenPool │  ← 数据层（存储 Provider/Key/指标）
           └────┬─────┘
                │
    ┌───────────┼───────────┐
    ▼           ▼           ▼
 Scheduler   Governor    Admin Panel
 (路由选择)  (权限控制)   (管理界面)
```

---

## TokenPool 职责范围

### ✅ TokenPool 负责

| 职责 | 说明 |
|------|------|
| **Provider 管理** | CRUD: 增删改查 Provider |
| **Key 管理** | CRUD: 增删改查 ProviderKey |
| **Key 发现** | 从心跳文件/miclaw_instances 自动发现新 Key |
| **Key 测试** | 真实 API 调用测试 Key 可用性 |
| **Health Score** | 综合评分 (latency + success_rate + penalty) |
| **Health Check** | 定期全量健康检查 |
| **Key 状态** | healthy/degraded/error/disabled 状态管理 |
| **Usage 记录** | 每 Key 每模型每日期使用统计 |
| **Yesterday Usage** | 昨日 Token 消耗统计 |
| **贡献比例** | 用户贡献 Token 的比例配置 (5%/10%/20%) |
| **预算限制** | 每 Key 日/月 Token 限额 |
| **自动熔断** | 连续 3 次失败 → disabled |
| **自动恢复** | penalty 时间衰减 → 恢复 healthy |
| **Cooldown 状态存储** | 记录 cooldown 状态，供 Scheduler 读取 |
| **数据持久化** | Provider/Key/Metrics 全部落 DB |

### ✅ Scheduler 负责（从 TokenPool 读取）

| 职责 | 说明 |
|------|------|
| **路由选择** | 从 TokenPool 读取 Key 列表，按策略选择 |
| **Rate Limit 检查** | 读 TokenPool 的 limit 配置 + 当前计数判断 |
| **Cooldown 执行** | 读 TokenPool 的 cooldown 状态，决定跳过 |
| **429 惩罚写入** | 调用失败后写入 penalty 到 TokenPool |
| **Sticky Session** | Scheduler 内存管理，不存 TokenPool |

### ✅ Governor 负责（控制 TokenPool 的权限）

| 职责 | 说明 |
|------|------|
| **Provider 权限** | 哪些 Provider 可用（黑白名单） |
| **Key 类型限制** | 商业 Key / 用户 Key 的访问策略 |
| **Budget 审批** | 超出预算后是否允许继续 |

### ❌ TokenPool 不负责

| 职责 | 归属 | 原因 |
|------|------|------|
| HTTP 调用 | Scheduler | TokenPool 是数据层 |
| 响应解析 | Scheduler | TokenPool 不处理响应 |
| 重试逻辑 | Scheduler | TokenPool 不执行调用 |
| Rate Limit 决策 | Scheduler | TokenPool 只存储限额 |
| Permission | Governor | TokenPool 不判权 |

---

## 数据流

```
1. 用户心跳 → heartbeat_logs/mb-xxx.json
2. TokenPool Loader → 解析 → upsert ProviderKey
3. TokenPool Health → 定期测试 → 更新 status/health_score
4. Scheduler 请求 → TokenPool.get_keys(filter) → [ProviderKey]
5. Scheduler 路由 → 选择 Key → 调用 → 返回结果
6. Scheduler 回调 → TokenPool.record_metrics(key_id, result)
7. Admin Panel → 读取 TokenPool 统计 → 展示
```

---

## 商业 Token Pool 特殊设计

> 以下分析"商业化中转站"能力如何融入 TokenPool

### 用户贡献 Token 机制

```
规则:
  - 用户设备心跳上报 api_key/base_url/model
  - TokenPool 自动发现 → upsert ProviderKey(key_type=user_contributed)
  - 管理员配置 contribution_ratio (5%/10%/20%)
  - Scheduler 选择 Key 时:
    * user_contributed Key 的 usage 不能超过 contribution_ratio * daily_total_token
    * 超出 → 自动跳过（熔断不超额）
```

### 多 Provider / 多 Model / 多 Base URL 支持

```
ProviderKey 表已支持:
  provider_id → Provider 表
  model → 任意模型名
  base_url → 任意 API Base URL
  → 天然支持多 Provider + 多 Model + 多 Base URL
```

### Key 隔离

```
owner_code 字段:
  user_contributed Key 有 owner_code
  admin_private Key 有 owner="admin"
  → 管理面板可按 owner_code 筛选
  → 统计可按 owner 分组
```

### 速率限制（防封号）

```
ProviderKey.rpm_limit + tpm_limit:
  管理员可配置每 Key 的 RPM/TPM 限制
  Scheduler 调用前检查: can_proceed(key_id, estimated_tokens)
  → 确保不触发上游封号
```

### 昨日统计

```
KeyMetrics 表:
  每日自动汇总 → date=昨天
  Admin API: GET /tokenpool/stats?date=2026-07-08
  → 返回每 Key 每 Model 用量
```

### 后台实时状态

```
Admin Panel API:
  GET /tokenpool/keys → 所有 Key 实时状态
  GET /tokenpool/keys/{id}/metrics → 每 Key 细粒度指标
  GET /tokenpool/stats/daily → 日统计
  GET /tokenpool/stats/provider → 每 Provider 统计
```

### 商业化中转站流程

```
用户注册 → 分配 API Key
    ↓
用户调 MBclaw API (付费)
    ↓
TokenPool 选择最优 Provider/Key
    ↓
Scheduler 转发请求
    ↓
TokenPool 记录用量
    ↓
月底结算 (按用量)
```

**建议**: 商业化放在单独的 `commercial/` 模块，TokenPool 只管资源层。
