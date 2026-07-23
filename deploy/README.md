# Deploy

这里存放平台调度器模板，不包含业务代码。

- `systemd/`：Linux systemd user service 和 timer。
- `launchd/`：macOS launchd plist 模板。

两个平台最终都调用 `scripts/run-daily.sh`，因此采集行为保持一致。模板默认不会自动启用，必须由用户显式安装。
