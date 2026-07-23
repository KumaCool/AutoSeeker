# macOS Scripts

本目录只服务于 macOS。

- `login.sh`：启动项目专属 Chrome Profile，等待用户扫码或完成人工安全验证，导出 `zhipin.com` Cookie，然后调用每日采集脚本。
- `install-launchd.sh`：根据 `deploy/launchd/` 模板生成并安装每天 09:00 执行的 launchd 用户任务。

这些脚本不会绕过验证码或人工确认。Linux 用户应通过 `autoseeker auth import` 导入 Cookie。
