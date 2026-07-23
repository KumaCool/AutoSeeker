# BOSS 直聘职位筛选

本地 Python 项目，每天查询 BOSS 直聘武汉“前端”职位，保留最低月薪不低于
15K、经验要求不超过 3 年的岗位，并增量写入 Excel。

项目只读取职位信息，不投递简历、不发起沟通、不发送消息。

## 环境要求

- macOS 14+
- Python 3.11-3.14
- [uv](https://docs.astral.sh/uv/)
- 本人合法登录的 BOSS 直聘账号 Cookie

## 安装

```bash
chmod +x setup.sh login.sh run_daily.sh install_launchd.sh
./setup.sh
```

`setup.sh` 使用 `pyproject.toml` 创建 `.venv`、解析依赖并生成 `uv.lock`。`iv8`
使用官方 PyPI 包，macOS 需要 0.1.4 或更高版本。

## 登录与 Cookie

首次使用或登录失效时运行：

```bash
./login.sh
```

脚本会打开项目专属 Chrome，并通过本机 Chrome DevTools Protocol 检查登录状态。
需要登录时只需扫码；检测到登录成功后会自动导出
`zhipin.com` Cookie 到 `cookies.json`，关闭浏览器并继续生成 Excel。验证码或安全验证
仍需人工完成，脚本不会绕过。

浏览器登录状态保存在 `.browser-profile/`，不会读取日常 Chrome 的密码或其他站点
数据。该目录和 `cookies.json` 均已从版本控制中排除。

## 运行

```bash
./run_daily.sh
```

如果项目专属浏览器会话存在，脚本会先在后台刷新 Cookie。登录失效时任务停止并提示
执行 `./login.sh`；不会继续使用已确认失效的会话。

输出文件：

- `outputs/wuhan-frontend-jobs.xlsx`：增量职位表
- `logs/latest.log`：最近一次完整日志
- `logs/latest.exit`：最近一次退出码
- `logs/run-YYYYMMDD-HHMMSS.log`：历史运行日志

## 每日任务

安装 macOS `launchd` 任务，默认每天 09:00 执行：

```bash
./install_launchd.sh
```

修改运行时间后，重新执行安装命令：

```xml
<!-- launchd.plist.template -->
<key>Hour</key><integer>9</integer>
<key>Minute</key><integer>0</integer>
```

## 配置

搜索参数位于 `boss_jobs.py` 顶部：

| 配置 | 默认值 | 说明 |
| --- | --- | --- |
| `KEYWORD` | `前端` | 搜索关键词 |
| `CITY_CODE` | `101200100` | 武汉城市编码 |
| `MIN_SALARY_K` | `15` | 薪资区间最低值 |
| `MAX_EXPERIENCE_YEARS` | `3` | 经验要求上限 |
| `PAGE_COUNT` | `5` | 每次查询页数 |
| `REQUEST_INTERVAL_SECONDS` | `1.5` | 翻页请求间隔 |

## 测试

测试不访问 BOSS，不读取真实 Cookie：

```bash
.venv/bin/python -m unittest discover -s tests -v
```

测试覆盖薪资和经验解析、`encryptJobId` 详情链接、旧 `securityId` Excel 行迁移，
以及登录 Cookie 的识别、域名过滤和文件权限。

## 项目边界

- 遇到 `code=37` 时，使用 iv8 计算并更新当前会话的 `__zp_stoken__`
- 只请求职位列表并保存筛选结果
- 不绕过验证码或人工安全验证
- 不实现自动投递或自动沟通
