# Web 默认展示实施路线

## 1. 目标

将默认结果链路从“采集 → Excel”演进为：

```text
采集 → SQLite → Web 服务端渲染
             └→ 显式 Excel 导出
```

现有 Excel 数据不迁移、不导入；SQLite 从空库开始。实施过程中保持 Cookie、BOSS Client、stoken 和领域筛选行为不变。

## 2. 执行规则

- 严格 TDD：每个行为先写失败测试，再实现。
- 每个 TASK 验收后创建独立 Git commit。
- 每个阶段完成后执行完整离线门禁并等待批准。
- 默认测试不访问 BOSS、不读取真实 Cookie。
- 真实请求、服务绑定到 Tailscale IP和调度器启用均需明确批准。
- 账号 `code=36` 属于外部风控，不通过代码绕过。

## 3. 阶段 A：SQLite 权威存储

### TASK A.1 数据模型和 schema

创建：

```text
src/boss_zhipin/infrastructure/sqlite_repository.py
tests/test_sqlite_repository.py
```

测试并实现：数据库初始化、WAL、busy timeout、`jobs`、`collection_runs` 和索引。

验收：临时空库创建成功，schema 和 pragma 正确，未读取旧 Excel。

### TASK A.2 采集批次生命周期

测试并实现：

- `begin_run()` 创建 `running`；
- 完整成功为 `completed`；
- 部分结果失败为 `partial`；
- 无结果失败为 `failed`；
- 错误消息脱敏。

### TASK A.3 职位 upsert

测试并实现：

- 首次插入设置 first/last seen；
- 再次出现只更新 last seen；
- 同一 run 内按 `job_id` 去重；
- 首次发现批次不可覆盖；
- 新增数计算正确；
- 一个 run 的写入使用事务。

### TASK A.4 切换采集主存储

修改：

```text
src/boss_zhipin/application/collect_jobs.py
src/boss_zhipin/cli.py
src/boss_zhipin/config.py
src/boss_zhipin/default.toml
config/default.toml
```

`collect` 默认写 SQLite，不创建 Excel。保留部分失败保存语义和明确退出码。

阶段验收：离线测试通过；经批准后执行一次真实采集，确认 SQLite run 和职位数据一致。

## 4. 阶段 B：查询应用服务

### TASK B.1 查询模型

创建：

```text
src/boss_zhipin/application/query_jobs.py
tests/test_query_jobs.py
```

定义类型化筛选、排序、分页和返回模型。输入验证：页码、page size、排序枚举和薪资范围。

### TASK B.2 SQLite 查询

实现关键词、薪资、经验、地点、新增、run、排序、count 和 LIMIT/OFFSET。所有 SQL 参数化。

验收：空库、组合筛选、分页越界和排序均有测试。

## 5. 阶段 C：服务端渲染 Web

### TASK C.1 Web 基础和健康检查

增加依赖：FastAPI、Uvicorn、Jinja2。

创建 `src/boss_zhipin/web/`，实现 app factory、静态文件、模板和 `/health`。健康检查不得访问 BOSS。

### TASK C.2 职位列表

实现 `/jobs` 的 GET 表单、服务端分页、筛选状态回填、默认排序和空状态。模板必须自动 HTML 转义。

### TASK C.3 职位详情和 404

实现 `/jobs/{job_id}`，不存在时返回 HTML 404。BOSS 链接使用安全的外部链接属性。

### TASK C.4 采集批次页面

实现 `/runs`，展示状态、页数、统计和脱敏错误信息。

### TASK C.5 Web CLI

增加：

```bash
boss-zhipin web --host 127.0.0.1 --port 8080
```

默认不绑定 `0.0.0.0`。CLI 参数可覆盖 TOML。

阶段验收：FastAPI TestClient 路由和 HTML 测试通过；浏览器本机访问正常。

## 6. 阶段 D：Excel 按需导出

### TASK D.1 重构 Excel Exporter

将现有 `ExcelJobRepository` 改为 `ExcelJobExporter`，只接收 SQLite 查询结果并生成文件，不参与采集事务。

### TASK D.2 导出 CLI

增加：

```bash
boss-zhipin export excel [--output PATH]
```

测试默认路径、自定义路径、15 列、超链接、空数据和原子保存。只有显式命令才生成 Excel。

阶段验收：正常 `collect` 后无新 Excel；显式导出后文件有效。

## 7. 阶段 E：部署与文档

### TASK E.1 Web systemd service

在 `deploy/systemd/` 增加 Web service 模板。采集 timer 与 Web service 分离，共享 SQLite。安装脚本仍不自动启用服务。

### TASK E.2 macOS 启动方式

为 launchd 增加可选 Web plist 模板；登录脚本不自动启动 Web。

### TASK E.3 文档同步

更新根 README、`scripts/README.md`、`deploy/README.md`、配置、运维、安全和测试文档。明确 Web 默认、Excel 按需、SQLite 空库起步。

## 8. 完整质量门禁

每个阶段至少执行：

```bash
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest
uv run pre-commit run --all-files
uv build
```

Web 阶段还需：

- TestClient 路由测试；
- HTML 转义/XSS 测试；
- `/health` 无外部网络测试；
- 临时 SQLite 并发读写测试；
- wheel 全新环境安装和模板/静态资源包含检查。

## 9. 完成定义

- `collect` 默认只写 SQLite；
- Web 默认显示 SQLite 中的新采集数据；
- 空数据库有友好页面；
- 筛选、排序和分页可用；
- 采集批次和错误状态可查看；
- Excel 只在显式 `export excel` 时生成；
- 当前旧 Excel 未迁移；
- Web 默认监听 `127.0.0.1`；
- Cookie、stoken 和敏感错误不出现在页面；
- 离线门禁、wheel 和本机 Web 验收通过。
