# Router 核心逻辑

## 1. 哪些代码可以直接借鉴？
router.ts: routeRequest()→查可用Keys→动态priority排序(429惩罚 2分钟衰减)→round-robin同分组轮询→canMakeRequest(RPM/RPD)→canUseTokens(TPM/TPD)→isOnCooldown()→fallback。比TokenPool的顺序遍历candidates[:max_retries]更均衡。

## 2. 哪些代码可以直接复制？
router.ts的429动态惩罚+round-robin算法翻译为Python，融入TokenPool Scheduler。

## 3. 哪些需要改？
TokenPool当前顺序遍历→改为priority排序+round-robin。固定阶梯冷却→改为动态衰减惩罚。

## 4. 哪些不能用？
★★★★★

## 5. 迁移工作量
不复制TypeScript。算法用Python重写。

## 6. 依赖模块
3-5天

## 7. 是否适合 MBclaw？
TokenPool Scheduler

## 8. 推荐指数
非常适合。router.ts是TokenPool Scheduler升级的直接参考。
