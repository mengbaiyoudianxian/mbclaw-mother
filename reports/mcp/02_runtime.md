# Tool Schema & 生命周期

## 1. 哪些代码可以直接借鉴？
MCP Tool定义: {name, description, inputSchema: {type: object, properties: {...}}}。生命周期: initialize→tools/list→tools/call→shutdown。

## 2. 哪些代码可以直接复制？
不复制。参考Tool Schema作为CapabilityDef的字段标准。

## 3. 哪些需要改？
CapabilityDef增加inputSchema(JSON Schema格式)。考虑capability_type字段对齐(我们已有tool/skill/prompt_skill)。

## 4. 哪些不能用？
★★★☆☆

## 5. 迁移工作量
MCP协议的initialize/shutdown生命周期——Capability是静态注册，不需要。

## 6. 依赖模块
0.5天(格式对齐)

## 7. 是否适合 MBclaw？
Capability

## 8. 推荐指数
部分适合
