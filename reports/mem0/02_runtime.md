# Memory Pipeline

## 1. 哪些代码可以直接借鉴？
Mem0 Pipeline: add(messages)→LLM提取事实→embedding向量化→vector store存储。search(query)→embedding→相似度搜索→top-k。对比MBclaw: close_session→LLM摘要+jieba→FTS5+jieba双路召回。

## 2. 哪些代码可以直接复制？
不复制。Mem0的提取→存储→检索三阶段Pipeline设计可以参考。

## 3. 哪些需要改？
Memory写入增加extract→store两阶段。检索保持FTS5+jieba，不引入embedding。

## 4. 哪些不能用？
★★★☆☆

## 5. 迁移工作量
embedding API调用(成本高)。外部向量DB(运维重)。

## 6. 依赖模块
0天(设计参考)

## 7. 是否适合 MBclaw？
无

## 8. 推荐指数
部分适合。Pipeline设计参考，不迁移实现。
