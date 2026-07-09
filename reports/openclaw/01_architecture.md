# 整体架构

## 1. 哪些代码可以直接借鉴？
OpenClaw是全栈Agent平台(21k+文件)。核心: channels/多渠道系统(100+文件)、context-engine/上下文引擎、.agents/skills/技能系统。MBclaw应重点参考channels/的插件注册模式。

## 2. 哪些代码可以直接复制？
不复制TypeScript代码。参考channels/registry.ts的插件注册、context-engine/的模块化、.agents/skills/的声明式技能定义。

## 3. 哪些需要改？
Gateway改为插件注册模式(参考registry.ts)。Context Engine从单一类改为独立模块。Capability参考skills/的声明式。

## 4. 哪些不能用？
★★★★☆

## 5. 迁移工作量
移动端App(Android/iOS/macOS)、Docker部署、website——MBclaw不需要。

## 6. 依赖模块
3-5天(设计对齐，Gateway重构)

## 7. 是否适合 MBclaw？
无(Gateway是MBclaw自研)

## 8. 推荐指数
适合。channels/插件化是最值得参考的设计。
