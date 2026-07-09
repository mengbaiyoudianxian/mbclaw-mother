# 需要适配修改

## 1. 哪些代码可以直接借鉴？
Mem0基于向量DB，MBclaw基于FTS5。适配改的是接口层(update/category/user_id)，不改底层存储。

## 2. 哪些代码可以直接复制？
不复制。仅接口对齐。

## 3. 哪些需要改？
MemoryRepo增加update()。experiences表加category列。考虑user_id(session owner)替代session_id。

## 4. 哪些不能用？
★★★☆☆

## 5. 迁移工作量
保持FTS5+jieba底层不变。

## 6. 依赖模块
1-2天

## 7. 是否适合 MBclaw？
Memory

## 8. 推荐指数
部分适合
