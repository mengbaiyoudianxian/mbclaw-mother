# 不适合MBclaw的部分

## 1. 哪些代码可以直接借鉴？
MCP Client/Server远程协议: MBclaw Capability是进程内调用，不需要网络协议。JSON-RPC传输层: 增加复杂度。

## 2. 哪些代码可以直接复制？
零复制。

## 3. 哪些需要改？
排除MCP Client/Server实现。排除JSON-RPC传输。仅保留Tool Schema格式。

## 4. 哪些不能用？
★★☆☆☆

## 5. 迁移工作量
MCP是远程协议，MBclaw是进程内——架构不匹配。

## 6. 依赖模块
0天

## 7. 是否适合 MBclaw？
无

## 8. 推荐指数
不适合
