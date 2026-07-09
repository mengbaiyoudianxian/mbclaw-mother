# 5. 最终目录设计

```
capabilities/
│
├── registry.py          # 核心: 注册/查找/列表/启用/禁用
│   1. CapabilityDef dataclass
│   2. CapabilityRegistry 类 (单例)
│      register(def)  → REGISTRY[name] = def
│      get(name)      → REGISTRY[name] or KeyError
│      list(cat, tag) → [def for def in REGISTRY if match]
│      search(q)      → FTS5 搜索
│      enable(name)   → REGISTRY[name].enabled = True
│      disable(name)  → REGISTRY[name].enabled = False
│      execute(name)  → REGISTRY[name].executor(**validated_params)
│
├── models.py            # SQLAlchemy ORM 模型
│   class Capability(Base):
│       id, name, type, category, tags,
│       description, input_schema, examples,
│       runtime, enabled, version, usage_count,
│       created_at, updated_at
│
├── loader.py            # 启动加载 + 热加载
│   load_builtins()   → 扫描 builtins/*.yml → 注册
│   load_from_db()    → 从数据库加载动态注册的
│   hot_reload()      → 文件变更检测 → 重新加载
│   seed_first_run()  → 首次启动写入数据库
│
├── executor.py          # 执行 + 安全
│   execute(name, params):
│     1. registry.get(name)
│     2. validator.validate(params, input_schema)
│     3. security.check(name, params)
│     4. runtime.check(name)
│     5. result = capability.executor(**params)
│     6. bump_usage(name)
│     7. return result
│
│   class SecurityPolicy:
│       whitelist: list  (自动允许)
│       blacklist: list  (永远拒绝)
│       asklist: list    (询问用户)
│
├── search.py            # 搜索 (替换 LIKE)
│   search(query)     → FTS5 全文搜索 (name+description+tags)
│   suggest(query)    → jieba 分词 → 模糊匹配
│
├── publisher.py         # 对外格式化
│   to_openai_tools() → [{"type":"function","function":{name,description,parameters}}]
│   to_mcp_tools()    → MCP tools/list 格式
│   to_system_prompt()→ 将所有 prompt_skill 拼入 System Prompt
│   to_api_list()     → API GET /capabilities 返回格式
│
├── validator.py         # 参数校验
│   validate_schema(schema: dict, params: dict) → (valid, errors)
│   validate_name(name: str) → (valid, reason)
│   validate_capability(cap: CapabilityDef) → errors
│
├── runtime.py           # 运行时状态判断
│   RUNTIME_MATRIX = {
│       "server": ["read_file","list_directory","search_memory",...],
│       "admin":  ["write_file","edit_file","run_command",...],
│       "device-remote": ["export_photos","export_wechat",...],
│       "planned": ["dream_memory","collision_think",...],
│   }
│   check(name) → current runtime supports this?
│
├── installer.py         # 安装/卸载/升级
│   install(def)     → 写入 DB + 注册
│   uninstall(name)  → 标记 enabled=False + 可选删除
│   upgrade(name, v) → 更新 version 字段
│
└── builtins/            # YAML 声明 (非代码)
    ├── files.yml
    │   - name: read_file
    │     type: tool
    │     category: file
    │     runtime: server
    │     description: 读取文件内容
    │     input_schema:
    │       type: object
    │       properties:
    │         path: {type: string, description: 文件绝对路径}
    │       required: [path]
    │     executor: _builtin_read_file
    │
    ├── shell.yml
    ├── memory.yml
    ├── web.yml
    ├── device.yml
    ├── device_collect.yml
    └── skills/
        ├── github.yml
        │   - name: github_search_code
        │     type: skill
        │     ...
        ├── ssh.yml
        └── prompts.yml
            - name: code-review
              type: prompt_skill
              description: ... (LLM 自动理解)
              prompt: "你是代码审查专家..." (注入 System Prompt)
```
