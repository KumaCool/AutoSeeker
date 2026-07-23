# launchd Template

`boss-zhipin.plist.template` 是 macOS 用户级 launchd 任务模板，默认每天 09:00 调用 `scripts/run-daily.sh`。

模板中的项目路径、日志路径和 label 由 `scripts/macos/install-launchd.sh` 替换。该目录本身不执行安装。
