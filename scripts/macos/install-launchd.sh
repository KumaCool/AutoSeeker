#!/bin/zsh
set -eu

ROOT="${0:A:h:h:h}"
LABEL="com.autoseeker.collect"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

mkdir -p "$HOME/Library/LaunchAgents" "$ROOT/var/logs"
sed \
  -e "s|__LABEL__|$LABEL|g" \
  -e "s|__RUN_SCRIPT__|$ROOT/scripts/run-daily.sh|g" \
  -e "s|__WORK_DIR__|$ROOT|g" \
  "$ROOT/deploy/launchd/autoseeker.plist.template" > "$PLIST"

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "已安装每日 09:00 任务：$PLIST"
