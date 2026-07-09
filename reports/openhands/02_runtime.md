# Runtime / Agent Loop

## 1. 哪些代码可以直接借鉴？
Agent Loop: Condenser压缩→LLM调用→Tool执行→循环。与MotherRuntime.run()流程几乎相同。Condenser(智能压缩)是我们缺少的。

## 2. 哪些代码可以直接复制？
不复制。流程已对齐。参考Condenser的压缩策略。

## 3. 哪些需要改？
不必修改。MotherRuntime已正确实现Agent Loop。

## 4. 哪些不能用？
★★★★★

## 5. 迁移工作量
Sandbox Agent、Task Agent(子任务分解)——太复杂。

## 6. 依赖模块
0天(流程已对齐)

## 7. 是否适合 MBclaw？
无

## 8. 推荐指数
适合。验证了MotherRuntime设计的正确性。
