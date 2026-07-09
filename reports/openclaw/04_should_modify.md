# 需要适配修改

## 1. 哪些代码可以直接借鉴？
OpenClaw的channels/有100+文件，MBclaw只需要5个渠道(QQ/微信/Web/CLI/飞书)。需要大幅简化。

## 2. 哪些代码可以直接复制？
不复制。

## 3. 哪些需要改？
MBclaw Gateway改为: ChannelRegistry(20行)→5个Adapter→1个normalize→1个dispatcher。不需要100+文件。

## 4. 哪些不能用？
★★★★☆

## 5. 迁移工作量
transport/多协议(我们只需要HTTP/WebSocket)。thread-bindings(不需要跨渠道绑定)。

## 6. 依赖模块
2-3天

## 7. 是否适合 MBclaw？
无

## 8. 推荐指数
适合
