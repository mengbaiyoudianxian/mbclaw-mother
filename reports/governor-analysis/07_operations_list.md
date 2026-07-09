# 任务七：所有需要 Governor 接管的操作

> 结合 MBclaw 当前规则分类

---

## LOW — 只读/查询类（risk 0-20）

| 操作 | 工具 | 当前状态 | Governor 接管后 |
|------|------|---------|---------------|
| 读文件 | read_file | 无条件执行 | allow (whitelist)，记录审计 |
| 列目录 | list_directory | 无条件执行 | allow |
| 搜索记忆 | search_memory | 无条件执行 | allow |
| 列出会话 | list_sessions | 无条件执行 | allow |
| 查看会话 | get_session | 无条件执行 | allow |
| 设备信息 | get_device_info | 无条件执行 | allow |
| 设备状态 | device_status | 检查心跳+收集开关 | allow (保持检查) |
| 内容分类 | classify_content | 无条件执行 | allow |
| 关键词提取 | extract_keywords | 无条件执行 | allow |
| 文本摘要 | summarize_text | 无条件执行 | allow |
| 网络搜索 | web_search | 无条件执行 | allow |
| 读剪贴板 | get_clipboard | 无条件执行 | allow |
| 获取电池 | get_battery | 设备端 | allow |
| 获取系统信息 | get_system_info | 设备端 | allow |
| 获取通知 | get_notifications | 设备端 | allow |
| 列出 WiFi | list_wifi_networks | 设备端 | allow |
| WiFi 信息 | wifi_info | 设备端 | allow |
| 列出 App | list_apps | 设备端 | allow |
| **GitHub 读操作** | github_search_code, github_list_repos, github_get_pr, github_list_issues, github_get_file, github_list_workflows, github_workflow_runs, github_pr_diff, github_compare | 无条件执行 | allow (whitelist) |
| SSH 执行 | ssh_exec | 无条件执行 | **ask** (远程执行需谨慎) |

---

## NORMAL — 写入/修改类（risk 20-50）

| 操作 | 工具 | 当前状态 | Governor 接管后 |
|------|------|---------|---------------|
| 写文件 | write_file | 无条件执行 | ask (gateway 用户)，allow (admin) |
| 编辑文件 | edit_file | 无条件执行 | ask (gateway 用户)，allow (admin) |
| 执行命令 | run_command | 无条件执行 (仅 tool_runtime 黑名单 6 条) | **风险评分**：简单命令 allow，危险命令 ask/deny |
| 打开 URL | open_url | 无条件执行 | allow |
| 截图 | take_screenshot | 无条件执行 | allow |
| 写剪贴板 | set_clipboard | 无条件执行 | allow |
| 查询 LLM Provider | 修改 Provider 配置 | admin 面板 | allow (admin only) |
| 安装依赖 | run_command(pip install) | 无条件执行 | ask |
| Git 操作 | run_command(git commit/push) | 无条件执行 | ask |
| **GitHub 写操作** | github_create_pr, github_create_issue, github_pr_review, github_create_release | 无条件执行 | ask (影响外部仓库) |
| 设备切换 WiFi | toggle_wifi, connect_wifi, disconnect_wifi, switch_wifi | 设备在线+收集开关 | allow (保持设备检查) |
| 设备控制 | toggle_bluetooth, toggle_flashlight, toggle_airplane_mode | 设备在线 | allow |
| 设备调节 | set_brightness, set_volume | 设备在线 | allow |
| 设备 UI | click_at, long_press_at, swipe, input_text, press_key | 设备在线 | allow |
| 打开 App | open_app | 设备在线 | allow |
| 屏幕录制 | screen_record | 设备在线 | ask |
| 发送短信 | send_sms | 设备在线 | **ask** (可能产生费用) |
| 读短信 | read_sms | 设备在线 | **ask** (涉及隐私) |
| 拨打电话 | make_call | 设备在线 | **ask** (可能产生费用) |
| 收集微信数据 | collect_wechat_data | 设备在线+收集开关 | allow (保持检查) |

---

## CRITICAL — 高风险操作（risk 50-100）

| 操作 | 工具 | 当前状态 | Governor 接管后 |
|------|------|---------|---------------|
| rm -rf / | run_command | tool_runtime 黑名单 | **DENY (hard block)** |
| rm -rf 非/tmp 目录 | run_command | 无检查 | **DENY** |
| shutdown / reboot | run_command | tool_runtime 黑名单 | **DENY** |
| dd if= / mkfs | run_command | tool_runtime 黑名单 | **DENY** |
| fork bomb | run_command | tool_runtime 黑名单 | **DENY** |
| 修改 /etc 配置 | write_file / edit_file | 无检查 | **DENY** (非 /tmp 路径) |
| 写 ~/.ssh/authorized_keys | write_file | 无检查 | **DENY** |
| 修改 Mother 代码 | write_file / edit_file | 无检查 | **DENY** (路径在黑名单) |
| 修改 Runtime 文件 | write_file / edit_file | 无检查 | **DENY** |
| 删除数据库 | run_command(sqlite/drop) | 无检查 | **DENY** |
| 删除 TokenPool 配置 | write_file | 无检查 | **DENY** |
| 删除 Memory 数据 | run_command | 无检查 | **DENY** |
| 导出设备相册 | export_photos | 设备在线+收集开关 | ask (大量数据传输) |
| 导出微信数据库 | export_wechat | 设备在线+收集开关+Root | ask (高度敏感) |
| 导出 AI 对话 | export_conversations | 设备在线+收集开关 | ask (隐私数据) |
| 卸载 App | uninstall_app | 设备在线 | **ask** |
| 强制停止 App | force_stop_app | 设备在线 | allow (可逆) |
| 修改密码 | API | admin 面板 | allow (admin only) |
| 升级 Mother | run_command(git pull) | 无检查 | ask (自动备份后允许) |

---

## 不存在的操作用黑名单

以下路径/模式硬编码拒绝，不允许任何配置绕过：

```python
HARD_DENY = [
    # 系统破坏
    "rm -rf /", "shutdown", "reboot", "mkfs", "dd if=", ":(){ :|:& };:",
    # 敏感路径写入
    "/etc/", "/boot/", "/root/", "~/.ssh/",
    # Mother 自毁
    "/opt/mbclaw/", "app/main.py", "app/agent.py",
    "app/mother_runtime.py", "app/tools.py",
    # 数据库
    "mbclaw.db", "pool.db",
]
```
