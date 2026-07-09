# Memory — 长期记忆

## 一句话定位
双路召回长期记忆系统 (FTS5 + jieba)。

## 接口规范


## 数据库模型 (5表+FTS5)
sessions, messages, summaries, keywords, experiences + messages_fts, experiences_fts

## 双路召回
A路(FTS5, 权重0.6): MATCH查询 | B路(jieba, 权重0.4): 关键词匹配 → 加权合并 → top_n

## 代码复用: 95%
完整复用  +  + 
