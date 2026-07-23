# 工程化重构实施路线

## 1. 总目标

在不改变现有业务范围和 Excel 语义的前提下，将项目重构为模块化、跨平台、有稳定 CLI、可离线测试和可运维的 Python 应用。

## 2. 执行约束

- 当前文档阶段不实施任何代码变更。
- 后续按完整阶段连续实施；每个 TASK 验收后立即创建独立 Git commit。
- 阶段完成后做一次整体回归并汇报，等待明确“继续”。
- 明确、局部、低风险失败只自主修复一次；仍失败则停止。
- 方案切换、真实站点请求、人工验证或高风险动作必须先获批准。
- 不使用历史成功日志冒充当前现场验收。

## 3. 阶段 1：仓库基线与运行数据隔离

**目标**：建立可回滚基线，不改变抓取行为。

### TASK 1.1 初始化 Git 基线

- 初始化仓库，检查作者配置。
- 审核待提交文件，确认 Cookie、Profile、日志、缓存、Excel、`.venv` 未被跟踪。
- 运行现有 6 个离线测试和语法校验。
- 创建初始提交。

**验收**：`git status` 干净；敏感/运行数据均未跟踪；现有测试通过。

### TASK 1.2 统一运行数据目录

- 建立 `var/{secrets,cache,logs,outputs,browser-profile}` 约定。
- 先增加兼容路径测试，再迁移路径常量。
- 保持现有 Excel 格式和 Cookie JSON 格式。

**验收**：旧文件可迁移或显式读取；源码根目录不再生成新运行数据。

### TASK 1.3 整理仓库卫生

- 完善 `.gitignore`、`.env.example` 和开发命令说明。
- 清理被误放入源码边界但已忽略的临时目录，只在用户批准后执行实际删除。

**阶段回归**：离线测试全部通过；经批准后真实运行一次并对比结果。

## 4. 阶段 2：Python 包、配置和 CLI

**目标**：建立 `src/boss_zhipin/` 和唯一稳定入口，暂不深拆业务。

### TASK 2.1 建立 src 包和 CLI 骨架

- 配置 `pyproject.toml` 的 console script。
- 实现 `boss-zhipin --help`、版本和明确退出码。
- 旧脚本暂作为兼容入口调用新 CLI。

### TASK 2.2 引入类型化配置

- 创建 `config.py` 和 `config/default.toml`。
- 测试 TOML、环境变量和 CLI 覆盖顺序。
- 将搜索参数、请求超时和路径从源码移出。

### TASK 2.3 建立认证子命令

- `auth import`：域名过滤、`zp_at` 校验、`0600`、原子写入。
- `auth check`：单独命令；真实请求需批准。
- `config show`：敏感字段脱敏。

**阶段回归**：旧命令和新 CLI 对同一配置产生相同筛选结果和 Excel 路径。

## 5. 阶段 3：职责拆分与测试安全网

**目标**：把单文件职责拆为领域、应用和基础设施模块。

### TASK 3.1 提取领域模型与纯函数

- 创建 `models.py`、`domain/salary.py`、`domain/filtering.py`。
- 先迁移并扩展薪资、经验、身份键测试。

### TASK 3.2 提取 BOSS 客户端和响应解析

- 创建 `infrastructure/boss_client.py`。
- 加入正常、空列表、缺字段、非 JSON 和未知业务码 fixture。

### TASK 3.3 提取 stoken 服务

- 创建 `infrastructure/stoken.py`。
- 固化同一 challenge 参数、四个 Cookie 替换和最多一次重试。
- mock 安全 JS 和 iv8 边界，不依赖真实站点。

### TASK 3.4 提取 Excel Repository

- 创建 `infrastructure/excel_repository.py`。
- 保持现有 15 列、工作表名、主键、旧行迁移和超链接。
- 增加临时文件原子保存和损坏文件保护测试。

### TASK 3.5 建立应用编排

- 创建 `application/collect_jobs.py`。
- 覆盖多页、部分失败保存、结果统计和退出码。

**阶段回归**：同一脱敏 fixture 的标准化数据完全一致；真实回归需用户批准。

## 6. 阶段 4：跨平台运维与质量门禁

**目标**：Linux/macOS 共用核心命令，调度器只做包装。

### TASK 4.1 跨平台脚本

- 移除核心流程对 zsh 和固定 macOS Chrome 路径的依赖。
- 保留 macOS 浏览器登录为可选适配器。
- Linux 直接 Cookie 导入作为一等路径。

### TASK 4.2 调度模板

- 增加 systemd user timer 示例。
- 整理 launchd 模板，两者统一调用 CLI。
- 默认不自动安装或启用。

### TASK 4.3 工程质量

- 加入 ruff、pyright、pytest 和 pre-commit。
- 增加 CI：锁文件、格式、lint、类型和离线测试。
- CI 不加载真实 Cookie、不访问 BOSS。

### TASK 4.4 README 与运维文档同步

- README 只保留快速开始、命令、项目边界和文档链接。
- 根据最终实现更新本目录文档，删除失效设计。

**阶段回归**：Linux 与 macOS 安装/CLI 验证；离线质量门禁全部通过。

## 7. 阶段 5：真实站点最终验收

需要用户明确批准后执行：

1. 校验 Cookie 文件格式和权限，不输出值。
2. 执行 `auth check`。
3. 先执行一页试运行，检查业务码和输出。
4. 执行完整 5 页采集。
5. 核对匹配数、新增数、Excel 行、超链接和日志脱敏。
6. 若命中 `code=37`，核对安全 JS、非空 stoken、Cookie 替换和重试结果。
7. 比较重构前后行为差异；任何差异必须解释或修复。

## 8. 暂不实施

- SQLite/ORM、Web UI、Docker、队列、微服务和依赖注入容器。
- 自动投递、自动聊天、多账号和验证码处理。
- 与当前需求无关的插件化、抽象基类或通用爬虫框架。

## 9. 完成定义

- 项目可通过 `uv sync --locked` 安装。
- `boss-zhipin` CLI 是唯一推荐入口。
- Linux 与 macOS 核心采集路径一致。
- 默认测试完全离线且不读取真实 Cookie。
- Cookie、缓存、日志和输出与源码隔离且不被 Git 跟踪。
- 领域、应用、HTTP/stoken 和 Excel 职责清晰。
- 文档与实际命令一致。
- 经批准的真实站点回归成功，并有现场输出作为依据。
