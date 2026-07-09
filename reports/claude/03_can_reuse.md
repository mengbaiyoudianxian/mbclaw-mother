# 可直接复用

## 1. 哪些代码可以直接借鉴？
压缩策略(重要性评分)。Checkpoint(context快照)。插件注册(marketplace.json模式)。

## 2. 哪些代码可以直接复制？
不复制(闭源)。参考设计。

## 3. 哪些需要改？
ContextEngine增加消息重要性评分。Governor增加checkpoint/restore。

## 4. 哪些不能用？
★★★★☆

## 5. 迁移工作量
核心Agent代码(闭源)。文件快照。

## 6. 依赖模块
2-3天

## 7. 是否适合 MBclaw？
ContextEngine + Governor

## 8. 推荐指数
适合
