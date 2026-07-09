# 可直接复用

## 1. 哪些代码可以直接借鉴？
Tool Definition格式作为CapabilityDef标准。tools/list作为CapabilityRegistry.list()参考。

## 2. 哪些代码可以直接复制？
不复制。格式对齐。

## 3. 哪些需要改？
CapabilityDef增加inputSchema字段。registry.list()返回MCP兼容格式。

## 4. 哪些不能用？
★★★☆☆

## 5. 迁移工作量
MCP协议其他部分(initialize/shutdown/transport)

## 6. 依赖模块
0.5-1天

## 7. 是否适合 MBclaw？
Capability

## 8. 推荐指数
部分适合
