# 需要适配修改

## 1. 哪些代码可以直接借鉴？
基于OpenHands设计需要适配的部分：Injector简化为工厂函数、Integrations合并到Capability、MCP仅对齐接口。

## 2. 哪些代码可以直接复制？
无需代码复制。仅设计对齐。

## 3. 哪些需要改？
MBclaw不需要泛型DI框架。不需要独立Integrations目录。不需要完整MCP协议。

## 4. 哪些不能用？
★★★☆☆

## 5. 迁移工作量
保留MBclaw现有设计，仅在接口层面参考OpenHands。

## 6. 依赖模块
1天(设计对齐)

## 7. 是否适合 MBclaw？
无

## 8. 推荐指数
适合
