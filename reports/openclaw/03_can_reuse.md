# 可直接复用

## 1. 哪些代码可以直接借鉴？
P0: channels/registry.ts插件注册模式。P1: context-engine/模块化设计。P2: .agents/skills/声明式技能。P3: streaming.ts流式回复控制。

## 2. 哪些代码可以直接复制？
不复制TypeScript。参考设计: 渠道ID规范化、插件元数据、流式draft控制。

## 3. 哪些需要改？
Gateway: 增加ChannelRegistry类。ContextEngine: 拆分为init/registry/delegate/runtime-settings。

## 4. 哪些不能用？
★★★★★

## 5. 迁移工作量
移动端App、daemon守护进程、cron定时任务——不适用。

## 6. 依赖模块
5-7天(设计参考+Gateway重构)

## 7. 是否适合 MBclaw？
无

## 8. 推荐指数
适合。channels/是Gateway的最佳参考。
