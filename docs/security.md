# 安全设计

## 1. 范围

项目处理登录 Cookie 和平台安全 challenge，安全目标是避免凭据泄漏、限制请求行为并尊重人工验证边界。

## 2. Cookie 生命周期

- 只接受用户本人合法登录会话。
- 导入时过滤非 `zhipin.com` Cookie，要求非空 `zp_at`。
- 目标文件权限固定 `0600`，父目录建议 `0700`。
- 使用临时文件写入并原子替换。
- 不把 Cookie 放入源码、TOML、CLI 参数、日志、测试 fixture 或 Git。
- 任务结束不主动删除 Cookie；轮换或撤销由用户明确执行。

## 3. 日志与错误脱敏

以下内容禁止输出：

- Cookie 名值对或完整 Cookie 请求头。
- `zp_at`、`wt2`、`__zp_stoken__` 等值。
- Authorization 类头部。
- 含 token 的完整 URL、challenge 原文或完整响应头。

可以输出：Cookie 数量、是否包含必要名称、文件权限、HTTP 状态码、业务码、challenge 名称的安全摘要和缓存路径。

异常信息进入日志前应经过统一 redactor；测试要覆盖常见敏感字段和 URL 编码后的值。

## 4. 安全 challenge 边界

允许：根据服务器返回的 `seed/name/ts` 执行站点下发的安全 JS，更新当前合法会话的 stoken，并低频重试原请求一次。

禁止：验证码识别或绕过、规避人工安全确认、批量账号、隐匿自动化行为、高频并发和扩大到自动沟通/投递。

一旦检测到验证码、登录确认或人工安全验证，程序必须停止并给出明确状态。

## 5. 浏览器登录适配器

- 使用项目专属 Profile，不读取日常浏览器密码或其他站点数据。
- CDP 仅监听 `127.0.0.1` 和随机端口。
- 只导出 `zhipin.com` Cookie。
- 不自动点击授权、二维码确认或安全验证。
- Linux 无浏览器时直接 Cookie 导入应正常工作。

## 6. 依赖与供应链

- 依赖由 `uv.lock` 固定，CI 使用 `uv sync --locked`。
- 依赖升级单独提交，运行完整离线测试后再做真实站点回归。
- 缓存的安全 JS 属于运行数据，不提交仓库；排障样本必须脱敏。

## 7. Git 防护

`.gitignore` 至少覆盖：

```gitignore
.venv/
var/
.browser-profile/
cookies.json
cookies.txt
js_reverse_cache/
logs/
outputs/
*.xlsx
```

后续加入 pre-commit 敏感信息扫描。若凭据误提交，应立即撤销会话并清理 Git 历史，单纯删除最新文件不够。

## 8. 安全验收清单

- Cookie 文件与目录权限正确。
- `git status` 不出现 Cookie、Profile、缓存、日志或 Excel。
- 正常和异常日志均不含凭据值。
- 默认测试不读取真实 Cookie、不访问 BOSS。
- `auth check` 和真实采集均有明确频率限制和超时。
- 人工验证出现时程序停止，不尝试绕过。
