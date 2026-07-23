# BOSS 直聘职位筛选

模块化 Python CLI：查询 BOSS 直聘职位，按薪资和经验筛选，并增量写入 Excel。

项目只读取职位列表；不投递简历、不发起沟通，也不绕过验证码或人工安全验证。

## 快速开始

要求 Python 3.11-3.14 和 [uv](https://docs.astral.sh/uv/)。

```bash
./setup.sh
.venv/bin/boss-zhipin --help
```

导入本人合法登录会话的 BOSS Cookie：

```bash
.venv/bin/boss-zhipin auth import /path/to/cookies.json
.venv/bin/boss-zhipin auth check
```

运行采集：

```bash
.venv/bin/boss-zhipin collect
```

临时覆盖搜索条件：

```bash
.venv/bin/boss-zhipin collect \
  --keyword 前端 \
  --city-code 101200100 \
  --page-count 5
```

查看生效配置（Cookie 路径会脱敏）：

```bash
.venv/bin/boss-zhipin config show
```

## 配置与输出

默认配置：`config/default.toml`

运行数据统一位于 `var/`：

- `var/secrets/cookies.json`
- `var/cache/security-js/`
- `var/logs/`
- `var/outputs/wuhan-frontend-jobs.xlsx`
- `var/browser-profile/`（可选，仅 macOS 浏览器登录）

以上内容均排除版本控制。旧运行数据迁移完成后，正式项目只使用 `var/`。

## 定时任务

Linux systemd user timer 模板位于 `systemd/`。生成用户单元但不自动启用：

```bash
./systemd/install-user-timer.sh
```

macOS launchd：

```bash
./install_launchd.sh
```

两者都调用相同的 `run_daily.sh` 和 `boss-zhipin collect`。

## 开发验证

```bash
uv sync --locked --all-groups
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest
uv run pre-commit run --all-files
```

CI 只执行离线质量检查，不读取真实 Cookie，也不访问 BOSS。

## 文档

完整架构、配置、运维、安全、测试与实施路线见 [`docs/`](docs/README.md)。
