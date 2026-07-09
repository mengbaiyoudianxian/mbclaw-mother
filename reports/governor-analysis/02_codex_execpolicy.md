# 任务二：Codex CLI ExecPolicy 分析

> 精确到文件、类、函数

---

## Codex CLI ExecPolicy 架构

```
execpolicy-legacy/src/
├── lib.rs             模块入口 → Policy, ExecCall, MatchedExec, Forbidden
├── policy.rs          Policy 类: check(exec_call) → MatchedExec
├── program.rs         ProgramSpec: 程序定义 + 允许/禁止规则
├── exec_call.rs       ExecCall { program, args }  输入模型
├── arg_matcher.rs     ArgMatcher: 参数匹配
├── arg_resolver.rs    PositionalArg: 参数解析
├── arg_type.rs        ArgType 枚举
├── valid_exec.rs      ValidExec: 合法的执行定义
├── policy_parser.rs   PolicyParser: 策略文件解析
├── sed_command.rs     sed 命令特殊处理
└── error.rs           错误类型
```

## 核心模型

### Policy.check() → MatchedExec

```rust
// 1. 检查 forbidden_program_regexes (禁止程序正则)
// 2. 检查 forbidden_substrings   (禁止子串)
// 3. 匹配 allowed programs       (允许的程序定义)
// 4. 验证参数 (arg_patterns)
// 返回: MatchedExec::Allowed | MatchedExec::Forbidden{cause}
```

### 返回类型

```rust
MatchedExec::Allowed { ... }        → allow
MatchedExec::Forbidden { cause }   → deny
// 无 "ask" — Codex CLI 由沙箱层处理 ask
```

---

## 可直接借鉴

| Codex CLI 文件 | 类/函数 | 借鉴什么 | 翻译为 Python |
|---------------|---------|---------|-------------|
| `policy.rs` | `Policy.check()` | 统一的策略检查入口 | `PolicyEngine.check(action) → Decision` |
| `exec_call.rs` | `ExecCall {program, args}` | 标准化的操作输入模型 | `Action {tool, params, user, channel}` |
| `program.rs` | `MatchedExec::Allowed/Forbidden` | 决策结果枚举 | `Decision.ALLOW/DENY/ASK` |
| `program.rs` | `ProgramSpec` | 每条规则的定义结构 | `PolicyRule {name, program, allow_args, forbid_args}` |
| `lib.rs` | `Forbidden{cause}` | 拒绝原因 | `DenyReason {rule, detail}` |

## 不要的

| Codex CLI | 原因 |
|-----------|------|
| `arg_matcher.rs` | Rust 专用的参数匹配器，Python 用 JSON Schema 更合适 |
| `policy_parser.rs` | Rust 策略文件解析器，MBclaw 用 YAML |
| `sed_command.rs` | sed 特殊处理，MBclaw 不需要 |
| `execv_checker.rs` | Rust execv 系统调用检查，Python 不需要 |

## MBclaw 应用方案

```
PolicyEngine.check(action):
  1. 遍历 deny_rules ← forbidden_program_regexes
     匹配 → return DENY(reason)
  2. 遍历 ask_rules
     匹配 & 不在 whitelist → return ASK(reason)
  3. 遍历 allow_rules
     匹配 → return ALLOW
  4. 默认: DENY (安全优先)
```
