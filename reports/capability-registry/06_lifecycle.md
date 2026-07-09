# 6. Tool 生命周期设计

```
                    ┌──────────────────────────────────────┐
                    │          Capability 生命周期           │
                    └──────────────────────────────────────┘

  安装 (install)
    │  来源: YAML 声明 / API 注册 / Plugin 包
    │  写入: DB 中 capability 表
    │  状态: enabled=False (安装后默认禁用, 需手动启用)
    │
    ▼
  校验 (validate)
    │  name 唯一性检查 (跨所有 capability)
    │  input_schema 合法性 (JSON Schema 规范)
    │  executor 存在性 (函数引用可解析)
    │  runtime 标签正确性
    │  通过 → 进入下一步 | 失败 → install_error
    │
    ▼
  注册 (register)
    │  REGISTRY[name] = capability
    │  状态: enabled=True
    │  DB 状态: active
    │  此时对 LLM 可见 (publisher.to_openai_tools())
    │
    ▼
  发现 (discover)
    │  GET /capabilities?category=file&tag=read
    │  GET /capabilities/search?q=文件
    │  publisher.to_llm_tools() → System Prompt 注入
    │
    ▼
  执行 (execute)
    │  1. registry.get(name)
    │  2. validator.validate(params, input_schema)
    │  3. security_policy.check(name, params)
    │      → allow: 直接执行
    │      → deny: 返回 blocked
    │      → ask: 请求用户确认
    │  4. runtime.check(name)
    │      → server: 服务器工具 (读文件/搜索记忆)
    │      → admin: 管理员工具 (写文件/执行命令)
    │      → device-remote: 设备远程工具 (需设备在线)
    │      → planned: 计划中 (返回 not_implemented)
    │  5. result = capability.executor(**params)
    │
    ▼
  统计 (metrics)
    │  usage_count++
    │  last_used_at = now()
    │  error_count (如果失败)
    │  avg_latency (平均执行时间)
    │
    ▼
  升级 (upgrade)
    │  相同 name:
    │  version 比较 → version_new > version_old
    │  替换 executor + input_schema
    │  DB 中更新 version 字段
    │  注意: 执行中的调用不受影响
    │
    ▼
  禁用 (disable)
    │  enabled=False
    │  REGISTRY[name] 仍保留但不可 execute()
    │  publisher.to_llm_tools() 排除 disabled
    │  可重新启用
    │
    ▼
  卸载 (uninstall)
    │  REGISTRY.pop(name)
    │  DB 中删除记录 或 标记 deleted_at
    │  builtins 内置工具不可卸载 (protected flag)
```

## 状态机

```
install_error ──→ installing ──→ validating ──→ registered ──→ executing ──→ metrics_updated
                      ↑              │                │              │
                      │              ↓                │              ↓
                      │         validation_error      │         execution_error
                      │                              │
                      ├────────── disabled ←─────────┤
                      │              │                │
                      │              ↓                │
                      └────────── uninstalled ←──────┘
```

## API 端点对应生命周期

```
POST   /capabilities/install     → install
GET    /capabilities/{name}/validate → validate
POST   /capabilities/{name}/enable   → register (enable)
GET    /capabilities              → discover (list)
GET    /capabilities/search       → discover (search)
POST   /capabilities/{name}/execute   → execute
GET    /capabilities/{name}/stats → metrics
POST   /capabilities/{name}/upgrade   → upgrade
POST   /capabilities/{name}/disable   → disable
DELETE /capabilities/{name}       → uninstall
```
