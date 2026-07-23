# 架构设计

## 1. 目标

项目现已整理为可安装、可测试、跨平台运行的 Python 模块化单体。保持现有范围：读取 BOSS 职位列表、处理 `code=37`、按规则筛选并增量写入 Excel；不实现自动沟通、简历投递或验证码绕过。

## 2. 当前问题

- HTTP、stoken、解析、筛选、Excel 和流程编排集中在单文件中。
- 源码与 `.browser-profile/`、Cookie、日志、逆向缓存、截图和输出混放。
- 搜索参数、UA 和路径硬编码。
- 重构前的每日脚本、登录脚本和 Chrome 路径偏向 macOS，Linux 不能作为一等运行环境。
- 测试主要覆盖纯函数，尚未覆盖 API 契约、`code=37` 重试和错误路径。

## 3. 设计原则

- **模块化单体**：一个 Python 包、一个 CLI、一个进程。
- **依赖向内**：领域层不依赖 requests、iv8、openpyxl。
- **端口与适配器**：应用层定义所需能力，基础设施层实现 BOSS HTTP、认证和 Excel 存储。
- **YAGNI**：暂不引入数据库、ORM、DI 容器、消息队列、Web UI 或插件系统。
- **行为兼容**：重构前后对同一 fixture 的筛选、去重和输出含义一致。

## 4. 目标目录

```text
boss-zhipin-jobs/
├── README.md
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .env.example
├── src/boss_zhipin/
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── models.py
│   ├── application/
│   │   └── collect_jobs.py
│   ├── domain/
│   │   ├── filtering.py
│   │   └── salary.py
│   ├── infrastructure/
│   │   ├── boss_client.py
│   │   ├── auth.py
│   │   ├── stoken.py
│   │   └── excel_repository.py
│   └── utils/
│       ├── iv8_silent.py
│       └── logging.py
├── tests/
│   ├── unit/
│   ├── contract/
│   ├── integration/
│   └── fixtures/
├── config/default.toml
├── scripts/
│   ├── setup.sh
│   ├── run-daily.sh
│   └── macos/
├── deploy/
│   ├── systemd/
│   └── launchd/
├── docs/
└── var/
    ├── cache/
    ├── logs/
    └── outputs/
```

`var/` 是默认运行数据根目录并排除版本控制；Cookie 文件默认位于 `var/secrets/cookies.json`，权限必须为 `0600`。浏览器 Profile 若保留，放在 `var/browser-profile/`。

## 5. 分层职责

### CLI：`cli.py`

解析命令和参数，加载配置，构造依赖并调用应用服务。不得包含请求、筛选或 Excel 业务逻辑。

建议命令：

```text
boss-zhipin collect
boss-zhipin auth import <file>
boss-zhipin auth check
boss-zhipin config show
```

### 应用层：`application/collect_jobs.py`

编排一次采集：创建会话、逐页请求、解析、筛选、去重、持久化并返回 `CollectionResult`。负责“做什么”，不负责具体 HTTP 或 Excel 实现。

### 领域层：`domain/`

包含薪资、经验和职位筛选规则，以及稳定的数据模型。函数应保持纯粹，可直接用 fixture 测试。

核心模型建议：

- `SearchCriteria`：关键词、城市、薪资、经验和分页。
- `Job`：标准化职位数据。
- `CollectionResult`：页数、匹配数、新增数、失败页和输出路径。

### 基础设施层：`infrastructure/`

- `boss_client.py`：HTTP Session、请求构造、响应状态和 JSON 契约。
- `stoken.py`：识别 `code=37`、下载安全 JS、调用 iv8、替换四个安全 Cookie并重试。
- `auth.py`：Cookie 导入、校验、权限和最小登录检查；浏览器扫码作为可选适配器。
- `excel_repository.py`：工作簿兼容、职位去重、旧行迁移、超链接和原子保存。

## 6. 依赖方向

```text
CLI → Application → Domain
          ↓
   Infrastructure → external libraries/services
```

应用层通过小型接口使用 `BossClient` 和 `JobRepository`。领域层不得导入 `requests`、`iv8`、`openpyxl` 或文件系统代码。

## 7. 采集时序

```text
CLI
  → 加载并校验配置
  → 安全加载 Cookie
  → Application.collect()
      → BossClient.request_page(page)
      → 若 code=37：StokenService.refresh() → 原请求只重试一次
      → ResponseParser → list[Job]
      → JobFilter
      → JobRepository.upsert()
  → 输出 CollectionResult 和退出码
```

同一次 challenge 的 `seed/name/ts` 必须配套使用；刷新后仍非成功业务码则中止，保存已经取得的部分结果并返回非零退出码。

## 8. 错误模型与退出码

建议定义明确异常和 CLI 退出码：

- `0`：完整成功。
- `2`：配置或参数错误。
- `3`：Cookie 缺失或登录失效。
- `4`：人工验证码/安全验证必需。
- `5`：远端协议或风控恢复失败。
- `6`：本地存储失败。

日志中记录异常类型、阶段、页码和业务码，不记录 Cookie、stoken、完整请求头或安全 JS 内容。

## 9. 数据兼容

第一版继续以 `encryptJobId` 为主键，保留现有 Excel 表名“职位”、15 列表头和旧 `securityId` 行迁移。重构阶段不同时更换存储格式；SQLite 仅在真实需求出现后另立方案。

## 10. 非目标

- 自动投递、自动聊天或批量账号。
- 验证码识别、绕过安全验证或规避平台限制。
- 高频并发抓取。
- 微服务、容器编排、消息队列、数据库和 Web 管理后台。
