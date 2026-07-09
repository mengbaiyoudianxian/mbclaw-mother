# 任务六：Evolution 目录设计

```
evolution/
├── __init__.py          Evolution Engine 入口
│   class EvolutionEngine:
│       collect(result: ExecutionResult)
│       analyze() → [AnalysisReport]
│       propose() → [OptimizationProposal]
│       submit_to_governor(proposal) → approved/rejected
│       职责: Evolution 总控
│
├── collector.py         结果收集器
│   class ResultCollector:
│       collect(session_id, result) → 写入 evolution_log
│       get_recent(limit) → [ExecutionResult]
│       get_failures(since) → [ExecutionResult]
│       职责: 收集每轮/每 Session 执行结果
│       数据源: Runtime 回调 + Memory experiences
│
├── analyzer.py          分析引擎
│   class PatternAnalyzer:
│       analyze(results) → [Pattern]
│       识别:
│         - 重复 429 (同一个 provider)
│         - 重复超时 (同一个 tool)
│         - 用户频繁纠正 (同类型内容)
│         - 工具使用成功率下降
│       职责: 从数据中识别模式
│
├── evaluator.py         评估引擎
│   class ImpactEvaluator:
│       evaluate(proposal) → ImpactScore
│       维度:
│         - 预期提升 (estimated_improvement)
│         - 风险等级 (low/medium/high/critical)
│         - 影响范围 (local/global)
│       职责: 评估改进建议的预期效果和风险
│
├── learner.py           学习引擎
│   class ExperienceLearner:
│       learn_from_success(result) → best_practice
│       learn_from_failure(result) → lesson
│       extract_rule(pattern) → rule_suggestion
│       职责: 从经验中提取可复用知识
│
├── optimizer.py         优化建议生成器
│   class Optimizer:
│       optimize_cooldown(pattern) → cooldown_proposal
│       optimize_provider_priority(pattern) → priority_proposal
│       optimize_tool_params(pattern) → tool_proposal
│       optimize_prompt(pattern) → prompt_proposal
│       职责: 针对具体模式生成改进方案
│
├── proposal.py          建议模型
│   @dataclass
│   class OptimizationProposal:
│       id, type, target, current_value, proposed_value
│       reason, evidence, impact_score, status
│       职责: 标准化改进建议格式
│
├── monitor.py           效果监控
│   class EvolutionMonitor:
│       track(proposal_id) → 开始监控
│       check(proposal_id) → improvement | no_change | regression
│       职责: 监控改进效果
│
├── rollback.py          回滚引擎
│   class RollbackManager:
│       rollback(proposal_id) → 恢复到改进前
│       get_history() → 所有历史变更
│       职责: 回滚失败的改进
│
├── experiment.py        实验引擎 (远期)
│   class ABExperiment:
│       start(proposal, traffic_pct)
│       evaluate() → winner
│       职责: AB 测试改进效果
│
└── store.py             存储层
    class EvolutionStore:
        save_result(result)
        save_pattern(pattern)
        save_proposal(proposal)
        get_proposals(status) → [OptimizationProposal]
        职责: Evolution 数据的持久化
```

## 各模块职责精简

| 模块 | 职责 | 依赖 |
|------|------|------|
| collector.py | 收集执行结果 | Runtime 回调 |
| analyzer.py | 识别模式 | collector |
| evaluator.py | 评估影响 | analyzer |
| learner.py | 提取经验 | analyzer |
| optimizer.py | 生成方案 | evaluator + learner |
| proposal.py | 标准化建议 | — |
| monitor.py | 效果监控 | Runtime |
| rollback.py | 回滚 | monitor |
| experiment.py | AB测试 (远期) | — |
| store.py | 持久化 | SQLite |
