# 需要适配修改

## 1. 哪些代码可以直接借鉴？
CapabilityDef增加inputSchema是可选的。不影响现有register()调用。渐进式对齐。

## 2. 哪些代码可以直接复制？
不复制。渐进式格式对齐。

## 3. 哪些需要改？
新增inputSchema字段(optional)。现有CapabilityDef不受影响。新注册的工具逐步补齐inputSchema。

## 4. 哪些不能用？
★★★☆☆

## 5. 迁移工作量
无

## 6. 依赖模块
0.5天

## 7. 是否适合 MBclaw？
Capability

## 8. 推荐指数
适合
