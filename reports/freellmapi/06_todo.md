# TODO清单

## 1. 哪些代码可以直接借鉴？
翻译router.ts动态429惩罚为Python。翻译round-robin逻辑。翻译ratelimit.ts四轴检查。融合TokenPool评分+动态惩罚。

## 2. 哪些代码可以直接复制？
算法翻译为Python。融入TokenPool Scheduler。

## 3. 哪些需要改？
TokenPool scheduler.py增加dynamic_429_penalty()。caller.py增加round_robin_select()。

## 4. 哪些不能用？
★★★★★

## 5. 迁移工作量
不改变TokenPool API。不改变数据库schema。

## 6. 依赖模块
5-7天

## 7. 是否适合 MBclaw？
TokenPool Scheduler/Caller

## 8. 推荐指数
非常适合
