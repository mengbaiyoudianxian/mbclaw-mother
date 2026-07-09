# TODO清单

## 1. 哪些代码可以直接借鉴？
ContextEngine压缩升级: 重要性评分+按需保留。Governor checkpoint: WorkingMemory快照+restore。

## 2. 哪些代码可以直接复制？
设计参考。不引入Claude Code代码。

## 3. 哪些需要改？
ContextEngine.compress()升级。Governor增加checkpoint()/restore()。

## 4. 哪些不能用？
★★★★☆

## 5. 迁移工作量
不改变MBclaw整体架构。在现有模块内增强。

## 6. 依赖模块
2-3天

## 7. 是否适合 MBclaw？
ContextEngine + Governor

## 8. 推荐指数
适合
