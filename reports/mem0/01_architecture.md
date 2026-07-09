# 整体架构

## 1. 哪些代码可以直接借鉴？
Mem0架构: memory/main.py→add(LLM提取+向量化)→search(embedding语义搜索)→update/delete。依赖embedding API + 外部向量DB(Chroma/Qdrant/...)。与MBclaw Memory(FTS5+jieba)走不同路线。

## 2. 哪些代码可以直接复制？
不复制代码。Mem0的add/update/delete接口设计和记忆分类(category标签)值得参考。

## 3. 哪些需要改？
MemoryRepo增加update()方法(而非覆盖)。增加category字段(preference/fact/instruction)。

## 4. 哪些不能用？
★★★☆☆

## 5. 迁移工作量
向量DB依赖——MBclaw当前不需要。embedding API成本——不适合免费场景。

## 6. 依赖模块
1天(接口设计对齐)

## 7. 是否适合 MBclaw？
无

## 8. 推荐指数
部分适合。接口设计参考，但不迁移底层存储。
