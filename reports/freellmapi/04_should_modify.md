# 需要适配修改

## 1. 哪些代码可以直接借鉴？
FreeLLMAPI是TypeScript(236行router.ts)→TokenPool是Python。需要翻译算法+适配TokenPool的评分系统。

## 2. 哪些代码可以直接复制？
不复制。用Python重写算法。

## 3. 哪些需要改？
router.ts→scheduler.py(新增dynamic_priority)。ratelimit.ts→合并入TokenPool ratelimit.py。

## 4. 哪些不能用？
★★★★☆

## 5. 迁移工作量
TokenPool的评分为主(三维) vs FreeLLMAPI的priority为主。两者可以融合: 评分决定初始优先级的，429惩罚动态调整。

## 6. 依赖模块
5-7天(Python重写+融合)

## 7. 是否适合 MBclaw？
TokenPool

## 8. 推荐指数
适合
