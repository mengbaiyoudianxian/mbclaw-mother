# 不适合MBclaw的部分

## 1. 哪些代码可以直接借鉴？
移动端App(Android/iOS/macOS): MBclaw已有独立APK。Docker部署: 单进程即可。daemon/cron: 不需要。

## 2. 哪些代码可以直接复制？
零复制。

## 3. 哪些需要改？
排除channels/中100+文件的大部分。只保留核心设计: registry+session+streaming。

## 4. 哪些不能用？
★★☆☆☆

## 5. 迁移工作量
OpenClaw是全栈平台，MBclaw是轻量Runtime。定位不同。

## 6. 依赖模块
0天

## 7. 是否适合 MBclaw？
无

## 8. 推荐指数
部分不适合
