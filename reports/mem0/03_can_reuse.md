# 可直接复用

## 1. 哪些代码可以直接借鉴？
P1: add/update/delete接口设计。P2: 记忆category分类。P3: user_id隔离(而非session_id)。远期: embedding作为B路召回补充。

## 2. 哪些代码可以直接复制？
不复制代码。接口设计参考。

## 3. 哪些需要改？
MemoryRepo增加update()方法。experiences表增加category字段。

## 4. 哪些不能用？
★★★☆☆

## 5. 迁移工作量
向量DB、embedding API——当前不需要。

## 6. 依赖模块
1-2天(接口+DB schema)

## 7. 是否适合 MBclaw？
Memory

## 8. 推荐指数
部分适合
