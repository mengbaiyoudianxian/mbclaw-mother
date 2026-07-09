# 整体架构

## 1. 哪些代码可以直接借鉴？
SDK/Server分层 + Injector依赖注入 + Integrations适配器层。最值得参考的是SDK(Agent Runtime)/Server(平台)分离。

## 2. 哪些代码可以直接复制？
不复制代码。OpenHands是TypeScript-like Python，风格不同。仅参考设计模式。

## 3. 哪些需要改？
Injector用工厂函数代替泛型DI。Integrations适配器模式直接套用。

## 4. 哪些不能用？
★★★★☆

## 5. 迁移工作量
Sandbox(Docker/K8s)、多租户、前端、Workspace——MBclaw全部不需要。

## 6. 依赖模块
1-2天(纯设计参考)

## 7. 是否适合 MBclaw？
无

## 8. 推荐指数
适合。架构分层验证了MBclaw目标架构。
