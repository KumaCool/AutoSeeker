# 配置设计

## 1. 目标

将搜索条件、请求参数和输出路径从源码中移出，同时保证敏感信息不进入普通配置、日志或命令历史。

## 2. 配置来源与优先级

从高到低：

1. CLI 参数（仅适合本次运行的非敏感覆盖）。
2. `AUTOSEEKER_*` 环境变量。
3. 用户指定的 TOML 文件。
4. `config/default.toml`。
5. 程序内安全默认值。

程序应提供 `autoseeker config show` 显示最终配置来源，但所有敏感值只显示 `<redacted>`。

## 3. 建议配置文件

以下为 Web 下一阶段的目标配置结构，当前发布版尚未实现 `storage`、`web` 和 `export.excel` 配置段：

```toml
[search]
keyword = "前端"
city_code = "101200100"
start_page = 1
page_count = 5
page_size = 30
minimum_salary_k = 15
maximum_experience_years = 3

[request]
interval_seconds = 1.5
timeout_seconds = 30
max_security_refreshes = 1

[storage]
database = "var/data/autoseeker.sqlite3"

[web]
host = "127.0.0.1"
port = 8080
page_size = 50

[export.excel]
path = "var/exports/wuhan-frontend-jobs.xlsx"

[runtime]
log_dir = "var/logs"
cache_dir = "var/cache"
```

## 4. 敏感配置

Cookie 不写入 TOML，也不建议直接存入环境变量。仅配置 Cookie 文件路径：

```bash
export AUTOSEEKER_COOKIE_FILE="$PWD/var/secrets/cookies.json"
```

Cookie 文件要求：

- JSON 对象或浏览器导出的 JSON 数组。
- Cookie 域必须属于 `zhipin.com`。
- 必须包含非空 `zp_at`。
- 文件权限必须是 `0600`；导入命令使用临时文件加原子替换。
- `auth import` 不输出任何 Cookie 值。

## 5. 路径规则

相对路径统一相对项目根目录或显式 `data_dir` 解析，不依赖当前 shell 工作目录。运行时目录按需创建，源码目录不可写不是错误前提。

## 6. 校验规则

- 页码、页数、page size、超时和间隔必须大于零。
- 薪资和经验上限不得为负。
- `max_security_refreshes` 第一版固定为 `1`，防止无限挑战循环。
- SQLite 数据库路径必须可创建，Web 端口必须位于 `1..65535`。
- Web 默认 host 必须是 `127.0.0.1`；绑定其他地址需显式配置。
- Excel 只允许通过显式 `export excel` 命令生成，不配置自动导出开关。
- 配置错误在任何网络请求前失败，退出码为 `2`。

## 7. 命令示例

```bash
uv run autoseeker collect
uv run autoseeker web
uv run autoseeker export excel
uv run autoseeker collect --keyword 前端 --city-code 101200100 --page-count 5
uv run autoseeker --config config/default.toml config show
uv run autoseeker auth import ~/Downloads/cookies.json
uv run autoseeker auth check
```

CLI 不能接收 Cookie 原文参数，以免进入 shell history 和进程列表。
