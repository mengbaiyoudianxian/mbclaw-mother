# MBOS Kernel v0.2 — Cognitive Layer

> **Status**: Phase 2 — Production Release
> **Version**: v0.2.0
> **Date**: 2026-07-11
> **Base**: MBclaw Mother Runtime v0.1.1

---

## Architecture

```
                        User Request
                             │
                             ▼
                    ┌─────────────────┐
                    │    Gateway      │  (QQ/WeChat/Web — unchanged)
                    └────────┬────────┘
                             │ StandardMessage
                             ▼
                    ┌─────────────────┐
                    │  EventKernel    │  RequestEvent emitted
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   Governor v2   │  Constitution Check
                    │  (5 rules)      │  Token Leak / System Delete
                    └────────┬────────┘  Security / Permission / Critical
                             │ allowed?
                             ▼
                    ┌─────────────────┐
                    │   Planner v0.1  │  Goal → TaskGraph
                    │  (12 strategies)│  Dependency Analysis
                    └────────┬────────┘
                             │ TaskGraph
                             ▼
                    ┌─────────────────┐
                    │  Scheduler v2   │  Task → Worker + Model
                    │  (multi-factor) │  Capability Match + Priority
                    └────────┬────────┘
                             │ ScheduleResult
                             ▼
                    ┌─────────────────┐
                    │ ExecutionEngine │
                    │  + ToolRuntime  │  (unchanged)
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │     Audit       │  Full Event Log
                    └─────────────────┘
```

---

## Module Inventory

| Module | Path | Status | Key Classes |
|--------|------|--------|-------------|
| **Planner** | `app/planner/` | ✅ v0.1 | `Planner`, `TaskGraph`, `Task` |
| **Governor** | `app/governor/` | ✅ v2 | `Governor`, `Policy`, `ConstitutionRule` |
| **EventBus** | `app/runtime/` | ✅ v2 | `EventBus`, 10 Event types |
| **Worker** | `app/worker/` | ✅ v1 | `Worker`, `WorkerPool` |
| **TokenPool** | `app/token_pool/` | ✅ v2 | `ResourceManager`, `ProviderInfo`, `ModelInfo` |
| **Scheduler** | `app/scheduler/` | ✅ v2 | `Scheduler`, `ScheduleResult` |
| **Kernel** | `app/runtime/` | ✅ v0.2 | `MBOSKernel`, `PipelineResult` |

---

## Key Upgrades from v0.1

### 1. Planner Engine v0.1
- 12 pattern-based decomposition strategies
- TaskGraph with DAG validation
- Topological sort + cycle detection
- Tasks with: id, name, type, priority, dependency, required_capability, status

### 2. Governor → Constitution Layer
- 5 immutable safety rules:
  - `no_token_leak` — blocks API key/secret/token leakage
  - `no_delete_system` — blocks system file deletion
  - `no_modify_security` — blocks security config changes
  - `no_bypass_permission` — blocks privilege escalation
  - `critical_auto_deny` — blocks destructive commands (shutdown, fork bomb, etc.)

### 3. EventBus → Pub/Sub
- Type-based subscribe/publish
- 10 event types covering full pipeline lifecycle
- Handler isolation — one failure doesn't break others

### 4. Worker Capability Registry
- Workers declare: id, type, status, capabilities, current_task
- WorkerPool provides capability-based matching
- Prefers most specialized worker (fewest capabilities)

### 5. TokenPool → Resource Manager
- Provider/Model metadata: context, cost, latency, availability
- `select_model(task_requirement)` — capability-based model selection
- Quota tracking, failure counting, cost preference

### 6. Scheduler v2
- Multi-factor: Task.capability + Worker.capability + Model score + Priority
- Capability mapping: task_type → model capability
- ScheduleResult with worker, provider, model metadata

---

## Pipeline Flow

```
MBOSKernel.process(message, session_id)

Phase 0: EventKernel — RequestEvent
Phase 1: Governor — Constitution Check (5 rules)
Phase 2: Planner — Goal → TaskGraph (12 strategies)
Phase 3: Scheduler — Task → Worker + Model (capability match)
Phase 4: Audit — Full event log
```

---

## Test Results

| Test Suite | Tests | Status |
|-----------|-------|--------|
| TaskGraph | 10 | ✅ All Pass |
| Planner | 10 | ✅ All Pass |
| Governor | 19 | ✅ All Pass |
| EventBus | 11 | ✅ All Pass |
| Worker | 17 | ✅ All Pass |
| TokenPool | 16 | ✅ All Pass |
| Scheduler | 9 | ✅ All Pass |
| Integration | 12 | ✅ All Pass |
| **Total** | **104** | ✅ **All Pass** |

---

## Breaking Changes: None

All existing interfaces preserved:
- Gateway (QQ/WeChat/Web) — unchanged
- QQBot Bridge — unchanged
- Web API — unchanged
- ToolRuntime v1.2 — unchanged

---

## Directory Structure

```
app/
├── planner/
│   ├── __init__.py
│   ├── planner.py          # 12 decomposition strategies
│   └── task_graph.py       # Task, TaskGraph, DAG validation
├── governor/
│   ├── __init__.py
│   ├── governor.py         # Constitution check entry
│   ├── constitution.py     # 5 safety rules
│   ├── policy.py           # Rule evaluation engine
│   └── decision.py         # GovernorDecision, RiskLevel
├── runtime/
│   ├── __init__.py
│   ├── kernel.py           # MBOSKernel — full pipeline
│   ├── event.py            # 10 event types
│   └── event_bus.py        # Pub/sub EventBus
├── worker/
│   ├── __init__.py
│   ├── worker.py           # Worker, factory functions
│   └── pool.py             # WorkerPool
├── token_pool/
│   ├── __init__.py
│   └── resource_manager.py # Provider/Model management
├── scheduler/
│   ├── __init__.py
│   └── scheduler.py        # Multi-factor scheduling
└── __init__.py
```
