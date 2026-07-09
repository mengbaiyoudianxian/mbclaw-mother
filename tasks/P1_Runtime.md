# P1_Runtime — Mother Runtime 改造

## 目标
统一 Mother 的 LLM 调用层，删除重复代码，建立清晰的模块边界。

## 子任务 (以后再拆)

### 1.1 删除废弃代码
- [ ] 删除 `app/agent.py`（功能被 mother_runtime.py 覆盖）
- [ ] 删除 `app/llm_router.py`（功能被 llm.py 覆盖）
- [ ] 删除 `app/tool_runtime.py`（功能被 tools.py 覆盖）
- [ ] 删除 `app/mbos_core.py`（早期原型）
- [ ] 删除 `app/output_sanitizer.py`（仅 MBOSCore 用）
- [ ] 删除 `app/capabilities/`（仅数据模型，无消费者）
- [ ] 删除 `app/providers.py`（功能被 TokenPool 覆盖）
- [ ] 清理 `app/admin/` 中的 .bak 文件和重复 HTML

### 1.2 统一 LLM Provider 层
- [ ] 创建 `app/llm/provider.py` — 统一 LLM 调用入口
- [ ] 封装 TokenPool HTTP 客户端
- [ ] 保留本地环境变量 Key fallback
- [ ] MotherRuntime._build_candidates() 改为通过 Provider 层调用
- [ ] LLMClient 改为通过 Provider 层调用
- [ ] 删除 Mother 内置的 `app/token_pool.py`

### 1.3 统一工具注册
- [ ] 创建 `app/tools/registry.py` — 统一工具注册中心
- [ ] 迁移 tools.py 的 BUILTIN_TOOLS 到 registry
- [ ] 迁移 skills.py 的 GitHub/SSH 技能到 registry
- [ ] MotherRuntime._execute_tool() 改为通过 registry dispatch
- [ ] 工具定义从 system prompt 中分离为独立配置

### 1.4 Session 增强
- [ ] WorkingMemory 增加序列化/反序列化能力
- [ ] 考虑在数据库增加 working_memory 表 (可选)

### 1.5 测试基础设施
- [ ] 搭建 pytest 基础框架
- [ ] MotherRuntime 单元测试 (mock LLM)
- [ ] MemoryRepo 单元测试 (SQLite in-memory)
- [ ] Tool 执行单元测试

## 依赖
- 无外部依赖
- 纯 Mother 内部改造

## 禁止
- 禁止新增 Runtime 实现
- 禁止新增 EventBus/Gateway/Worker
- 禁止修改 TokenPool 服务
- 禁止修改控制面板
