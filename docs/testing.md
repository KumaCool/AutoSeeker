# 测试策略

## 1. 目标

重构前先建立行为安全网，证明模块迁移没有改变解析、筛选、风控恢复、去重和 Excel 输出语义。

## 2. 测试层次

### 单元测试：`tests/unit/`

不访问网络和文件系统（临时目录除外），覆盖：

- 薪资区间、单值、面议和异常文本。
- 经验不限、应届、区间、“以内”和未知文本。
- 最低薪资与最大经验边界。
- `encryptJobId` URL、字段标准化和职位身份键。
- 配置覆盖、类型和范围校验。
- Cookie 域名、必要字段、权限和脱敏函数。

### 契约测试：`tests/contract/`

使用脱敏 fixture 固定远端结构：

- 正常 `code=0` 职位列表。
- `code=37` 与完整 `zpData.seed/name/ts`。
- 空列表、字段缺失、非 JSON 和未知业务码。

fixture 不含真实 Cookie、stoken、账号标识或可复用 challenge。

### 集成测试：`tests/integration/`

使用 mock HTTP 与临时文件系统，覆盖：

1. 正常多页采集与请求间隔。
2. 第一请求 `code=37`，刷新 stoken 后成功。
3. challenge 刷新后仍为 `code=37`，只重试一次。
4. 安全 JS 下载或 iv8 失败。
5. 中间页失败后保存部分结果并返回失败。
6. Cookie 失效映射到明确退出码。
7. Excel 新增、更新、旧 `securityId` 迁移、超链接和原子保存。
8. 工作簿损坏或工作表缺失时不覆盖原文件。

### 真实站点验收

默认关闭、CI 禁止执行。只有人工明确批准且提供本人合法 Cookie 时运行：

- 最小登录检查。
- 一页试运行。
- 完整配置运行。
- 核对 HTTP/业务结果、匹配数、Excel 新增标记和链接。
- 若命中 `code=37`，核对安全 JS 下载、非空 stoken 和重试业务码。

报告必须明确标注“本次现场验证”或“仅离线测试”。

## 3. 测试工具

建议采用：

- `pytest`：fixture、参数化和临时目录。
- `pytest-cov`：观察覆盖盲区，不把单一覆盖率数字当质量目标。
- `responses` 或 `pytest-httpserver`：HTTP 边界模拟，二选一即可。
- `ruff`：格式和静态检查。
- `pyright`：类型检查。

不同时引入多套同类工具。

## 4. 质量门禁

默认验证命令：

```bash
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest -q
```

阶段完成时还需：

- 比较重构前后同一 fixture 的标准化职位结果。
- 比较已有 Excel fixture 的行数、主键、首次发现和新增标记。
- 确认测试期间没有读取项目真实 `cookies.json`。
- 确认没有真实网络请求泄漏到离线测试。

## 5. 测试数据规则

- 原始真实响应若用于建 fixture，必须删除账号、Cookie、token、招聘者个人标识和可复用安全参数。
- fixture 应小而明确，每个文件只表达一种契约。
- 对响应结构的兼容策略必须通过测试体现，不在解析器中无依据地吞掉所有错误。
