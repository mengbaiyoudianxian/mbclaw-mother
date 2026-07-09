# 可直接复用

## 1. 哪些代码可以直接借鉴？
P0: router.ts动态429惩罚+round-robin。P1: ratelimit.ts四轴滑动窗口。P2: health.ts自动禁用(3次失败)。

## 2. 哪些代码可以直接复制？
router.ts算法逻辑翻译为Python。ratelimit.ts的canMakeRequest/canUseTokens逻辑。

## 3. 哪些需要改？
翻译为Python后融入TokenPool Scheduler + Caller。不改变TokenPool API接口。

## 4. 哪些不能用？
★★★★★

## 5. 迁移工作量
Node.js runtime、React前端、better-sqlite3——不适用。

## 6. 依赖模块
3-5天(算法翻译+Scheduler升级)

## 7. 是否适合 MBclaw？
TokenPool Scheduler

## 8. 推荐指数
非常适合
