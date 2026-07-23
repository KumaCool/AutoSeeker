# systemd User Timer

- `autoseeker.service.template`：一次性采集服务模板，工作目录在安装时替换。
- `autoseeker.timer`：每天 09:00 触发服务。
- `install-user-timer.sh`：把模板生成到 `~/.config/systemd/user/`，但不会自动 enable 或 start。

生成后按脚本输出的 `systemctl --user` 命令显式启用。
