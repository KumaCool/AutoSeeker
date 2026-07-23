# Source Code

正式 Python 包位于 `src/boss_zhipin/`。

- `domain/`：职位模型、薪资与经验筛选规则。
- `application/`：采集流程编排。
- `infrastructure/`：BOSS HTTP、stoken 和 Excel 适配器。
- `cli.py`、`config.py`、`auth.py`：命令行、配置和 Cookie 管理。

该目录不存放 Cookie、日志、缓存或 Excel。
