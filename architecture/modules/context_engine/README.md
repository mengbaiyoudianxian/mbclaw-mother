# Context Engine — 上下文管理

## 一句话定位
管理会话短期上下文（WorkingMemory），负责 Prompt 组装。

## 接口规范


## Prompt 组装顺序
1. system_prompt → 2. memory_recall → 3. recent_history[-20:] → 4. current_message

## 代码复用
从  WorkingMemory 类完整迁移。
