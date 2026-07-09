# 不适合MBclaw的部分

## 1. 哪些代码可以直接借鉴？
向量DB(Chroma/Qdrant/...20+): 运维复杂。embedding API: 成本高。LLM提取事实: 每次写入额外LLM调用(贵)。

## 2. 哪些代码可以直接复制？
零复制。

## 3. 哪些需要改？
排除所有向量DB依赖。排除embedding API。保持SQLite+FTS5。

## 4. 哪些不能用？
★★☆☆☆

## 5. 迁移工作量
MBclaw是零外部依赖的设计。Mem0需要向量DB+embedding API——违背设计原则。

## 6. 依赖模块
0天(排除)

## 7. 是否适合 MBclaw？
无

## 8. 推荐指数
不适合底层实现
