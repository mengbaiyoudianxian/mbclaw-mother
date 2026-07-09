# TokenPool Database 分析

## 作用

TokenPool 使用两个 SQLite 数据库存储 Key 配置、运行时统计、用户数据和调用日志。

## 数据库架构

### pool.db (主数据库) — 10+ 张表

| 表名 | 用途 | 关键字段 |
|------|------|---------|
| keys | 管理员配置的 Provider Key | alias(UNIQUE), encrypted_key, provider, model, priority, rpm_limit |
| key_stats | Key 运行时统计 | alias(PK), status, success_count, fail_count, total_tokens |
| users | 用户认证 | username(UNIQUE), password_hash, token, role, balance |
| user_shared_keys | 用户心跳贡献的共享 Key | user_code, encrypted_key, yesterday_usage, allowed_ratio |
| miclaw_accounts | MiClaw 账号池 | username, encrypted_password, login_status, qps_limit, owner_user_code |
| free_shared_keys | 免费营销 Key | code(UNIQUE), device_code, ip_address, total_limit, daily_limit |
| sold_keys | 售出 Key | user_id, key_alias(UNIQUE), encrypted_key, key_multiplier, balance |
| sold_key_models | 售出 Key 模型倍率 | key_alias, model_name, model_multiplier |
| sold_key_usage | 售出 Key 用量 | key_alias, model_name, tokens_used, cost |
| call_log | 调用日志 | key_alias, ts, latency_ms, total_tokens, cost, success |

### ratelimit.db (独立)

| 表名 | 用途 |
|------|------|
| cooldowns | 冷却状态持久化 |
| learned_limits | 自学习限制值 |

## 加密存储

- **加密算法**：AES-256-GCM
- **存储格式**：每行三个字段 (encrypted_key, key_iv, key_tag)
- **解密时机**：Registry._row_to_key() 中按需解密
- **覆盖范围**：keys.encrypted_key, user_shared_keys.encrypted_key, sold_keys.encrypted_key, miclaw_accounts.encrypted_password

## Schema 管理

- **自动建表**：Registry._init_db() 使用 CREATE TABLE IF NOT EXISTS
- **兼容升级**：ALTER TABLE ADD COLUMN + try/except "duplicate column"
- **Schema 校验**：Registry._validate_schema() 检查 dataclass 字段与 DB 列一致性
- **无迁移工具**：没有 Alembic 或版本化管理

## Key 类型分类

| 类型 | 存储表 | 来源 |
|------|--------|------|
| 管理员 Key | keys | 内置 BUILTIN + 手动添加 |
| 用户共享 Key | user_shared_keys | 心跳上报自动收集 |
| MiClaw 账号 | miclaw_accounts | 手动添加 + Bridge 登录 |
| 免费 Key | free_shared_keys | 设备注册自动发放 |
| 售出 Key | sold_keys | 手动添加（商业化） |

## 存在问题

1. **两套独立 SQLite 文件**：pool.db 和 ratelimit.db 各自管理
2. **无迁移工具**：ALTER TABLE 加 try/except 是脆弱的方式
3. **Schema 校验在每次 Registry 初始化时运行**：可能影响启动速度
4. **用户密码存储**：users.password_hash 字段命名但未见实际的哈希实现
5. **miclaw_accounts 的 cookie 存储**：明文 cookie 存数据库有安全风险
6. **INDEX 创建在 _init_db 中**：如果表已存在，索引可能未创建（IF NOT EXISTS 不支持 INDEX）

## 建议

1. 合并 ratelimit.db 到 pool.db
2. 引入 Alembic 做 schema 迁移
3. 为所有外键和常用查询列显式创建索引
4. 敏感字段（cookie、password）统一使用加密存储

## 以后是否保留

**保留核心表结构**，但需：
- 迁移到统一数据库
- 引入 schema 版本管理
- 完善索引
