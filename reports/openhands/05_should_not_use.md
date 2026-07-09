# 不适合MBclaw的部分

## 1. 哪些代码可以直接借鉴？
明确排除这些组件以避免过度设计。

## 2. 哪些代码可以直接复制？
零复制。

## 3. 哪些需要改？
Sandbox(Docker/K8s)、Workspace、多租户、BrowserAgent、前端React SPA、Recaptcha、Analytics——全部明确排除。

## 4. 哪些不能用？
★★☆☆☆

## 5. 迁移工作量
这些组件要么太重(BrowserAgent)，要么不适用(多租户)，要么已有替代(前端Panel)。

## 6. 依赖模块
0天(排除项)

## 7. 是否适合 MBclaw？
无

## 8. 推荐指数
部分不适合
