# Channels 消息系统

## 1. 哪些代码可以直接借鉴？
channels/核心: registry.ts(渠道注册)→session.ts(会话)→streaming.ts(流式)→turn/(轮次)→plugins/(渠道插件)→transport/(传输层)→message/(消息格式)。比MBclaw Gateway(7 adapter + thin forwarder)成熟得多。

## 2. 哪些代码可以直接复制？
不复制。参考registry.ts的normalizeChannelId()+listRegisteredChannelPluginIds()模式。

## 3. 哪些需要改？
Gateway适配器改为插件注册: register_adapter(name, adapter)→Gateway内部维护adapter注册表。

## 4. 哪些不能用？
★★★★★

## 5. 迁移工作量
thread-bindings(线程绑定)、cron(定时任务)——MBclaw不需要。

## 6. 依赖模块
2-3天(Gateway重构)

## 7. 是否适合 MBclaw？
无

## 8. 推荐指数
适合。100+文件channels/验证了Gateway独立模块的必要性。
