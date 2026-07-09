# 执行策略 & 沙箱

## 1. 哪些代码可以直接借鉴？
Codex CLI执行策略: 每命令需审批→allow/deny/ask三级。沙箱: bwrap(Linux容器隔离)+windows-sandbox-rs(Windows沙箱)。技能系统: .codex/skills目录→build.rs编译时注入。

## 2. 哪些代码可以直接复制？
不复制。参考command审批模式: 白名单自动+黑名单拒绝+其余询问。

## 3. 哪些需要改？
Compute.run_command(): 命令→白名单匹配→直接执行/黑名单匹配→拒绝/其余→检查ask策略→执行或拒绝。

## 4. 哪些不能用？
★★★☆☆

## 5. 迁移工作量
沙箱隔离(bwrap/windows-sandbox)——MBclaw移动设备场景不需要。Rust编译技能——Python不需要。

## 6. 依赖模块
1天

## 7. 是否适合 MBclaw？
Compute

## 8. 推荐指数
部分适合
