# 整体架构

## 1. 哪些代码可以直接借鉴？
FreeLLMAPI架构: app.ts→routes/(proxy/fallback/keys/analytics)→services/(router/ratelimit/health)→providers/(12家)。与MBclaw TokenPool架构完全一致(Python版)! router.ts(236行)是最核心的参考。

## 2. 哪些代码可以直接复制？
不复制TypeScript。router.ts的算法逻辑可以直接翻译为Python。

## 3. 哪些需要改？
TokenPool Scheduler增加动态429惩罚(FreeLLMAPI: 2分钟衰减)。Caller增加round-robin同分组轮询。

## 4. 哪些不能用？
★★★★★

## 5. 迁移工作量
Node.js技术栈(MBclaw是Python)。React前端(MBclaw是HTML Panel)。

## 6. 依赖模块
3-5天(Scheduler算法改进)

## 7. 是否适合 MBclaw？
TokenPool Scheduler/Caller

## 8. 推荐指数
非常适合。架构完全一致，TokenPool可直接借鉴router算法。
