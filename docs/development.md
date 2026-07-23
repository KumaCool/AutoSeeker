# 开发指南

## 当前开发环境

- Python 3.11-3.14
- uv
- 测试框架：pytest（兼容现有 unittest 测试）
- 质量工具：ruff、pyright、pre-commit
- 当前代码已落地模块化分层，结构见 [architecture.md](architecture.md)

## 建立环境

```bash
uv sync --locked --all-groups
```

可执行 `./scripts/setup.sh` 建立环境。Linux 开发环境直接使用 uv 和 Python 入口，不依赖 zsh 或 macOS Chrome。

## 离线质量检查

```bash
uv lock --check
.venv/bin/python -m py_compile \
  src/auto_seeker/*.py \
  src/auto_seeker/domain/*.py \
  src/auto_seeker/infrastructure/*.py \
  src/auto_seeker/application/*.py
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest
uv run pre-commit run --all-files
git diff --check
```

默认测试不得读取真实 Cookie 或访问 BOSS。

## 运行数据

新运行数据统一写入：

```text
var/
├── secrets/cookies.json
├── cache/security-js/
├── logs/
├── outputs/
└── browser-profile/
```

运行数据只保存在 `var/`；根目录不再保留旧 Cookie、Excel、日志、逆向缓存或浏览器 Profile。

## Git 提交规则

1. 每个最小 TASK 独立提交。
2. 修改行为前先写失败测试并确认 RED。
3. 实现最小改动，确认目标测试和完整测试均通过。
4. 提交前检查 staged 文件，禁止 Cookie、Profile、日志、缓存、Excel 和虚拟环境进入仓库。
5. 阶段结束后执行离线回归；真实站点回归必须有明确授权。

## 敏感信息检查

```bash
git status --short
git ls-files
git check-ignore -v \
  var cookies.json .browser-profile .venv logs js_reverse_cache outputs work
```

任何 Cookie、stoken 或账号会话值都不能出现在提交、日志、fixture 或文档中。