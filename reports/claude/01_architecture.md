# Claude Code — 整体架构(闭源)

## 1. 哪些代码可以直接借鉴？
Claude Code核心闭源。公开内容仅为插件市场(TypeScript)。核心设计(基于文档): Agent Loop(thinking<->tool_use交替)+智能上下文压缩+Checkpoint+插件系统。

## 2. 哪些代码可以直接复制？
不复制(闭源)。参考设计理念: 智能压缩(按重要性保留而非时间截断)、Checkpoint(对话状态快照)、插件注册(marketplace.json)。

## 3. 哪些需要改？
ContextEngine压缩策略: 从80%阈值截断→重要性评分保留。Governor: 增加lightweight checkpoint()(context快照)。

## 4. 哪些不能用？
★★★★☆

## 5. 迁移工作量
核心Agent(闭源)。文件Checkpoint(MBclaw是设备场景不需要)。插件市场(MBclaw不需要)。

## 6. 依赖模块
2-3天(压缩策略升级+checkpoint)

## 7. 是否适合 MBclaw？
ContextEngine + Governor

## 8. 推荐指数
适合。Claude Code的上下文压缩是行业最佳实践。
