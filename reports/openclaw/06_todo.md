# TODO清单

## 1. 哪些代码可以直接借鉴？
Gateway增加ChannelRegistry(插件注册模式)。5个Adapter改为注册模式。ContextEngine参考openclaw/context-engine/模块化。Capability参考skills/声明式。

## 2. 哪些代码可以直接复制？
设计对齐任务。

## 3. 哪些需要改？
Gateway重构为插件模式。ContextEngine从单类拆分为多模块。

## 4. 哪些不能用？
★★★★☆

## 5. 迁移工作量
不引入OpenClaw代码。仅参考设计。

## 6. 依赖模块
5-7天

## 7. 是否适合 MBclaw？
Gateway + ContextEngine

## 8. 推荐指数
适合
