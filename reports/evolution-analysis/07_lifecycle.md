# 任务七：Evolution 完整生命周期

```
[1] Task Complete
    Runtime 完成任务 (成功/失败)
    触发: 每 Session 结束时
    │
    ▼
[2] Collect Result
    ResultCollector.collect(session_id, result):
    ├── 成功: {status: success, turns, tools_used, latency, tokens}
    ├── 失败: {status: failure, error_type, error_msg, stack_info}
    └── 用户纠正: {status: corrected, original_reply, user_correction}
    写入: evolution_log 表
    状态: collecting
    │
    ▼
[3] Evaluate
    ImpactEvaluator 初步评估:
    ├── 正常 → 跳过
    ├── 单次失败 → 记录 → 等待更多数据
    └── 可疑模式 (≥3 次同类失败) → 触发 analyze [4]
    状态: evaluating
    │
    ▼
[4] Analyze (触发条件: ≥3 次同类失败)
    PatternAnalyzer.analyze(recent_results):
    识别:
    ├── 重复 429: provider=zhipu, 最近3次都是429
    │   pattern: "zhipu provider 频繁限流"
    ├── 重复超时: tool=export_wechat, 最近5次超时
    │   pattern: "export_wechat 工具默认timeout不足"
    ├── 重复纠正: 用户连续3次纠正输出格式
    │   pattern: "Prompt 格式说明不清晰"
    └── 成功率下降: tool=X 成功率从90%降到50%
        pattern: "工具X可靠性下降"
    状态: analyzing
    │
    ▼
[5] Extract Experience
    ExperienceLearner.learn(pattern):
    ├── 从模式中提取经验:
    │   title: "zhipu provider 429频繁 → 建议降优先级"
    │   kind: lesson
    │   content: "最近3次使用zhipu均返回429..."
    └── 写入 Memory: Memory.write_session_memory()
    状态: learning
    │
    ▼
[6] Generate Improvement
    Optimizer 针对模式生成方案:
    ├── 429 pattern → CooldownOptimizer
    │   proposal: 增加 zhipu cooldown 从30s→60s
    ├── timeout pattern → ToolParamOptimizer
    │   proposal: export_wechat timeout 从30s→120s
    └── correction pattern → PromptOptimizer
        proposal: 在系统提示中明确格式要求
    状态: optimizing
    │
    ▼
[7] Evaluate Impact
    ImpactEvaluator.evaluate(proposal):
    ├── 预期提升: "减少80%的429重试"
    ├── 风险等级: low (只改cooldown参数)
    ├── 影响范围: local (只影响zhipu provider)
    └── 置信度: 0.85
    状态: evaluating_impact
    │
    ▼
[8] Submit to Governor
    EvolutionEngine.submit_to_governor(proposal):
    ├── type=config_change + risk=low → AUTO_APPROVE
    ├── type=config_change + risk=medium → GOVERNOR_REVIEW
    ├── type=memory_update → AUTO_APPROVE
    ├── type=skill_update → NEED_HUMAN
    ├── type=policy_suggest → GOVERNOR_REVIEW
    └── type=core_code_change → HARD_DENY
    状态: pending_approval
    │
    ▼
[9] Governor Review
    Governor 审核:
    ├── HARD_DENY → REJECT (记录原因)
    ├── AUTO_APPROVE → APPROVE
    ├── GOVERNOR_REVIEW → 检查权限规则
    └── NEED_HUMAN → 通知管理员
    状态: reviewing
    │
    ▼
[10] Apply
    提案通过 → 应用改进:
    ├── cooldown 参数 → 写入 TokenPool 配置
    ├── tool timeout → 更新 Tool 定义
    ├── prompt template → 更新 Context Engine 模板
    └── provider priority → 更新 TokenPool 配置
    状态: applying
    │
    ▼
[11] Monitor
    EvolutionMonitor.track(proposal_id):
    对比:
    ├── 改进前: zhipu 429 rate = 40%
    ├── 改进后: zhipu 429 rate = 5%
    └── 结论: improvement ✅
    状态: monitoring
    │
    ▼
[12] Rollback (if regression)
    if monitor.check() == "regression":
      RollbackManager.rollback(proposal_id):
        ├── 恢复 cooldown 参数 → 30s
        ├── 记录: "cooldown 60s导致吞吐下降 > 预期"
        └── proposal.status = "rolled_back"
    状态: rolling_back
    │
    ▼
[13] Close
    改进完成 → proposal.status = "applied" | "rejected" | "rolled_back"
    写入 evolution_log
```

## 状态机

```
task_complete → collecting_result
                    │
                    ▼
                evaluating
                    │
            ┌───────┴───────┐
            ▼               ▼
        normal          pattern_detected
         (跳过)              │
                            ▼
                        analyzing
                            │
                            ▼
                      extracting_exp
                            │
                            ▼
                     generating_proposal
                            │
                            ▼
                     evaluating_impact
                            │
                    ┌───────┼───────┐
                    ▼       ▼       ▼
                auto_ap  gov_rev  need_hum
                    │       │       │
                    └───────┼───────┘
                            ▼
                        governor_review
                            │
                    ┌───────┴───────┐
                    ▼               ▼
                approved          rejected
                    │
                    ▼
                applying
                    │
                    ▼
                monitoring
                    │
            ┌───────┼───────┐
            ▼       ▼       ▼
        improved  neutral  regressed
                              │
                              ▼
                          rolling_back
```

## 关键参数

| 参数 | 值 | 说明 |
|------|-----|------|
| 触发阈值 | ≥3 次同类失败 | 避免单次异常触发 |
| 时间窗口 | 24 小时 | 只分析最近数据 |
| 监控周期 | 7 天 | 改进后观察一周 |
| Auto-approve 风险上限 | low | medium+ 需审批 |
| HARD_DENY 规则 | core_code_change / policy_suggest | 永不自动批 |
