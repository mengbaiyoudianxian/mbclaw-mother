# TODO清单

## 1. 哪些代码可以直接借鉴？
MemoryRepo增加update()方法。experiences表增加category字段。考虑user_id隔离(ADR新增)。远期评估embedding作为B路。

## 2. 哪些代码可以直接复制？
接口设计对齐。

## 3. 哪些需要改？
MemoryRepo接口增强。DB schema增加category。

## 4. 哪些不能用？
★★★☆☆

## 5. 迁移工作量
不改变FTS5底层。不引入向量DB。

## 6. 依赖模块
1-2天

## 7. 是否适合 MBclaw？
Memory

## 8. 推荐指数
部分适合
