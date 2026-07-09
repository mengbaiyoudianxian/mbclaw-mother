# 整体架构

## 1. 哪些代码可以直接借鉴？
MCP协议: Server(提供tools/resources/prompts)→Client(发现+调用)。JSON-RPC 2.0传输。关键概念: tools/list, tools/call, resources/read, prompts/get。

## 2. 哪些代码可以直接复制？
不复制。参考Tool Definition格式(name, description, inputSchema)作为CapabilityDef标准。

## 3. 哪些需要改？
CapabilityDef增加inputSchema字段。CapabilityRegistry.list()对齐tools/list格式。

## 4. 哪些不能用？
★★★☆☆

## 5. 迁移工作量
MCP Client/Server协议——MBclaw的Capability是进程内，不需要远程协议。

## 6. 依赖模块
1天(接口对齐)

## 7. 是否适合 MBclaw？
Capability

## 8. 推荐指数
部分适合。参考格式，不实现协议。
