# Context & Checkpoint 设计

## 1. 哪些代码可以直接借鉴？
Claude Code压缩: 保留关键决策/文件修改摘要/TODO→丢弃中间工具输出/已解决错误。/compact命令手动触发。Checkpoint: 每轮工具执行前Git级文件快照+对话状态快照→失败回退。

## 2. 哪些代码可以直接复制？
不复制。参考压缩算法: 按重要性评分而非时间排序保留/丢弃。

## 3. 哪些需要改？
ContextEngine.compress(): token预算→按重要性排序→保留top-N消息+摘要→丢弃其余。Governor.checkpoint(): 保存WorkingMemory快照→失败时restore。

## 4. 哪些不能用？
★★★★☆

## 5. 迁移工作量
Git级文件快照(MBclaw无文件系统)。/compact命令(MBclaw自动触发)。

## 6. 依赖模块
2-3天

## 7. 是否适合 MBclaw？
ContextEngine + Governor

## 8. 推荐指数
适合
