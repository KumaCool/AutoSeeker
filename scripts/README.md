# Scripts

项目的本地操作脚本集中在这里。

- `setup.sh`：使用 uv 按锁文件安装项目和开发依赖，并创建 `var/` 运行目录。它不会自动登录或启动定时任务。
- `run-daily.sh`：调用正式 CLI `autoseeker collect`，将本次输出、退出码和归档日志写入 `var/logs/`。
- `macos/`：仅用于 macOS Chrome 登录与 launchd 安装；Linux 不依赖这些脚本。

脚本只是 CLI 和部署模板的包装层，业务逻辑全部位于 `src/auto_seeker/`。
