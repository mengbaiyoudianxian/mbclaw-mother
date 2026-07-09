# 可直接复用

## 1. 哪些代码可以直接借鉴？
P0: SDK/Server分层 + Injector模式。P1: Integrations适配器 + MCP接口。P2: Sandbox机制(远期)。

## 2. 哪些代码可以直接复制？
不复制代码。参考设计模式即可。

## 3. 哪些需要改？
Injector→工厂函数DI、Integrations→CapabilityRegistry、MCP→ToolDefinition对齐。

## 4. 哪些不能用？
★★★★☆

## 5. 迁移工作量
Sandbox、多租户、BrowserAgent、Analytics——全部排除。

## 6. 依赖模块
1-2天(设计对齐)

## 7. 是否适合 MBclaw？
Architecture Spec

## 8. 推荐指数
适合
