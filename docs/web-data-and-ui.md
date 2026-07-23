# Web 数据与页面设计

## 1. 数据原则

- SQLite 是唯一权威业务数据源。
- 不迁移现有 Excel；新功能上线时创建空数据库。
- 下一次成功采集开始积累数据。
- Excel 只从 SQLite 查询结果按需生成。
- 采集程序不再默认生成或更新 Excel。

首次启动流程：

```text
创建空 SQLite → Web 显示“尚无采集数据”
              → collect 成功后写入 jobs/runs
              → 页面刷新后显示结果
```

## 2. 数据库位置

```text
var/data/boss-zhipin.sqlite3
```

`var/` 整体排除版本控制。数据库连接初始化：

```sql
PRAGMA foreign_keys=ON;
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;
```

## 3. 数据表

### 3.1 `jobs`

```sql
CREATE TABLE jobs (
    job_id TEXT PRIMARY KEY,
    job_name TEXT NOT NULL,
    company TEXT NOT NULL,
    salary TEXT NOT NULL,
    salary_low REAL NOT NULL,
    salary_high REAL NOT NULL,
    experience TEXT NOT NULL,
    degree TEXT NOT NULL,
    location TEXT NOT NULL,
    boss TEXT NOT NULL,
    skills TEXT NOT NULL,
    url TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    first_seen_run_id INTEGER NOT NULL,
    last_seen_run_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

索引：

```sql
CREATE INDEX idx_jobs_last_seen ON jobs(last_seen_at DESC);
CREATE INDEX idx_jobs_salary_low ON jobs(salary_low DESC);
CREATE INDEX idx_jobs_first_run ON jobs(first_seen_run_id);
CREATE INDEX idx_jobs_last_run ON jobs(last_seen_run_id);
```

`job_id` 继续使用 `encryptJobId`。`first_seen_at` 首次写入后不得覆盖；每次再次出现只更新 `last_seen_at` 和 `last_seen_run_id`。

### 3.2 `collection_runs`

```sql
CREATE TABLE collection_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL CHECK(status IN ('running', 'completed', 'partial', 'failed')),
    pages_requested INTEGER NOT NULL,
    pages_completed INTEGER NOT NULL DEFAULT 0,
    matched_count INTEGER NOT NULL DEFAULT 0,
    new_count INTEGER NOT NULL DEFAULT 0,
    error_type TEXT,
    error_message TEXT
);
```

采集开始即插入 `running`。完整成功改为 `completed`；取得部分结果后失败为 `partial`；未取得任何结果为 `failed`。

错误信息必须脱敏，不记录 Cookie、stoken、请求头或安全 JS 内容。`code=36` 可映射为“平台风控，需要人工处理”。

## 4. Repository 接口

应用层使用存储接口，不直接操作 SQLite：

```python
class JobRepository(Protocol):
    def begin_run(self, criteria, pages_requested) -> int: ...
    def save_jobs(self, run_id: int, jobs: list[Job]) -> int: ...
    def complete_run(self, run_id: int, result) -> None: ...
    def fail_run(self, run_id: int, result, error, partial: bool) -> None: ...
```

实现：

```text
SQLiteJobRepository
```

现有 `ExcelJobRepository` 不再充当主 Repository，重构为：

```text
ExcelJobExporter
```

## 5. 新增职位定义

数据库不保存会被每次重置的“是否新增”字符串。

Web 动态判断：

```text
job.first_seen_run_id == latest_completed_run.id
```

列表页面默认：

```text
新增优先 → 最后发现时间倒序 → 最低薪资倒序
```

一次搜索中未出现不能证明职位下架，第一版不维护 `active/inactive` 状态，只显示首次与最后发现时间。

## 6. Web 页面

### 6.1 职位列表

```text
GET /jobs
```

字段：新增、职位、公司、薪资、经验、学历、地点、技能、招聘者、首次发现、最后发现、BOSS 链接。

GET 参数：

```text
q                  职位/公司/技能关键词
minimum_salary     最低薪资
maximum_experience 最大经验
location           地点
new_only           仅新增
run_id             采集批次
sort               newest/salary_desc/last_seen
page               页码
page_size           20/50/100，默认 50
```

示例：

```text
/jobs?q=vue&minimum_salary=20&new_only=1&page=2
```

筛选使用 HTML GET 表单，URL 可复制、收藏并支持浏览器前进/后退。

### 6.2 职位详情

```text
GET /jobs/{job_id}
```

显示标准职位字段、首次/最后发现时间、首次/最近批次和 BOSS 原始链接。不存在时返回服务端渲染的 404 页面。

### 6.3 采集批次

```text
GET /runs
```

显示开始/结束时间、状态、完成页数、匹配数、新增数和脱敏错误摘要。

### 6.4 健康检查

```text
GET /health
```

只检查 Web 应用与数据库：

```json
{"status": "ok", "database": "ok"}
```

不得访问 BOSS，也不得检查 Cookie 是否有效。

## 7. Web 目录

```text
src/boss_zhipin/web/
├── __init__.py
├── app.py
├── dependencies.py
├── view_models.py
├── routes/
│   ├── jobs.py
│   ├── runs.py
│   └── health.py
├── templates/
│   ├── base.html
│   ├── jobs/list.html
│   ├── jobs/detail.html
│   ├── runs/list.html
│   └── errors/404.html
└── static/
    ├── app.css
    └── app.js
```

第一版使用原生 CSS；`app.js` 只做体验增强，核心查看和筛选功能不能依赖 JavaScript。第一版不引入 HTMX；若以后整页刷新确实影响体验，再按页面局部引入。

## 8. Excel 按需导出

CLI：

```bash
boss-zhipin export excel
boss-zhipin export excel --output ~/Downloads/jobs.xlsx
```

默认：

```text
var/exports/wuhan-frontend-jobs.xlsx
```

导出保持现有 15 列与超链接语义，但数据来源改为 SQLite。默认采集不生成 Excel。

第一版先实现 CLI 导出，不实现 Web 动态下载。若后续需要，可增加只读路由 `GET /exports/jobs.xlsx`，但不得把大型导出放入普通列表请求。

## 9. 配置目标

```toml
[storage]
database = "var/data/boss-zhipin.sqlite3"

[web]
host = "127.0.0.1"
port = 8080
page_size = 50

[export.excel]
path = "var/exports/wuhan-frontend-jobs.xlsx"
```

Excel 没有 `enabled=true` 的自动导出开关；第一版只允许显式执行导出命令，避免重新把 Excel 绑定到采集流程。
