# 运维设计

## 1. 支持平台

核心采集流程支持 Linux 和 macOS，依赖 Python 3.11-3.14 与 uv。浏览器扫码登录是可选功能；不能成为 Linux 直接导入 Cookie 的前置条件。

## 2. 安装

```bash
uv sync --locked
uv run boss-zhipin --help
```

验收：锁文件无漂移、CLI 可启动、默认不发起网络请求。

## 3. 首次准备

```bash
uv run boss-zhipin auth import /path/to/cookies.json
uv run boss-zhipin auth check
uv run boss-zhipin config show
```

`auth check` 只执行能判断登录状态的最小请求，不写 Excel。若平台要求验证码或安全验证，立即停止并提示人工处理。

## 4. 执行采集

```bash
uv run boss-zhipin collect
```

成功摘要至少包含：`run_id`、请求页数、匹配数、新增数、输出路径和退出码。不得打印 Cookie 或 stoken。

## 5. 运行数据

```text
var/
├── secrets/cookies.json
├── cache/security-js/
├── logs/latest.log
├── logs/latest.exit
├── logs/run-<timestamp>.log
├── outputs/wuhan-frontend-jobs.xlsx
└── browser-profile/       # 可选
```

Excel 保存应使用同目录临时文件后原子替换，避免进程中断造成工作簿损坏。

## 6. 定时任务

核心命令保持跨平台；调度器只是包装层：

- Linux：提供示例 systemd user timer，默认不自动安装。
- macOS：保留 launchd 模板。
- 两者都调用同一个 `boss-zhipin collect`，不复制业务逻辑。

安装、卸载和修改调度必须显式执行。定时任务缺少有效 Cookie 时应快速失败，不自动打开浏览器。

## 7. 日志规范

建议结构化字段：

```text
run_id, timestamp, level, stage, page, http_status, business_code,
matched_count, new_count, duration_ms, error_type
```

默认 INFO；调试模式仍需脱敏。`latest.log` 便于排障，历史日志按天数或总容量轮转。

## 8. 故障处理

- **配置错误**：网络请求前退出，修正配置。
- **Cookie 失效**：执行人工登录或重新导入，不重复请求。
- **code=37**：同一 challenge 刷新一次；重试仍失败则中止。
- **验证码/安全检查**：停止并提示人工完成，不绕过。
- **中间页失败**：保存已获取结果，返回非零退出码并记录失败页。
- **Excel 损坏**：不覆盖原文件；报告恢复建议。
- **BOSS 响应字段变化**：保存脱敏契约诊断信息，更新 fixture 与解析器。

## 9. 现场验收

每次正式发布至少执行：

```bash
uv lock --check
uv run ruff check .
uv run pytest -q
uv run boss-zhipin config show
```

真实站点回归需人工明确批准并使用本人合法会话。验收报告区分离线测试与现场请求，不以历史日志冒充本次验证。

## 10. 回滚

每个最小任务独立 Git commit。阶段回滚优先使用 Git 恢复代码；运行数据不随代码回滚。Excel 格式变更前必须先有兼容测试，第一轮重构不改变现有表结构。
