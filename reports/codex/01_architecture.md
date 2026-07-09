# Codex CLI — 整体架构

## 1. 哪些代码可以直接借鉴？
Codex CLI已从TypeScript迁移到Rust(codex-rs/)。核心: CLI入口+技能系统+Bubblewrap沙箱+跨平台执行策略。

## 2. 哪些代码可以直接复制？
不复制(Rust→Python)。参考执行策略: allow/deny/ask三级审批。技能编译注入: build.rs编译时注册。

## 3. 哪些需要改？
Compute增加命令审批级别: allow(白名单自动执行)/ask(用户确认)/deny(黑名单拒绝)。

## 4. 哪些不能用？
★★★☆☆

## 5. 迁移工作量
Rust运行时(Python不兼容)。Bubblewrap沙箱(移动设备不需要)。技能编译(.wasm)→Python不需要。

## 6. 依赖模块
1天(Compute安全增强)

## 7. 是否适合 MBclaw？
Compute

## 8. 推荐指数
部分适合。执行策略设计参考。
