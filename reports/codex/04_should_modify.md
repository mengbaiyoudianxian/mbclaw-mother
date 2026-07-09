# 需要适配修改

## 1. 哪些代码可以直接借鉴？
Codex CLI的allow/deny/ask是文件系统命令审批。MBclaw需要设备命令审批(打开App/修改设置等)。

## 2. 哪些代码可以直接复制？
不复制。

## 3. 哪些需要改？
审批策略适配: 文件命令→设备命令+shell命令。白名单/黑名单内容从Codex的bash命令→MBclaw的device tool names。

## 4. 哪些不能用？
★★★☆☆

## 5. 迁移工作量
保留Compute现有结构。增加policy层。

## 6. 依赖模块
1天

## 7. 是否适合 MBclaw？
Compute

## 8. 推荐指数
适合
