# Compute — 执行层

## 一句话定位
底层执行引擎 — shell/HTTP/设备命令。

## 接口规范


## 安全策略
BLOCKED: rm -rf /, shutdown, reboot, mkfs, dd if=, fork bomb

## 代码复用: 60%
从  execute() 提取 shell/device/file 逻辑
