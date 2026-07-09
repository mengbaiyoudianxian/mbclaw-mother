# TODO清单

## 1. 哪些代码可以直接借鉴？
Compute增加CommandPolicy(allow/deny/ask)。定义设备命令白名单+黑名单。Capability注册参考skills目录结构。

## 2. 哪些代码可以直接复制？
设计参考。Python实现。

## 3. 哪些需要改？
Compute增加policy模块。不改变现有run_command接口。

## 4. 哪些不能用？
★★★☆☆

## 5. 迁移工作量
不引入Rust。不引入沙箱。Python原生实现。

## 6. 依赖模块
1-2天

## 7. 是否适合 MBclaw？
Compute

## 8. 推荐指数
部分适合
