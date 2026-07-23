#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
TARGET="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
mkdir -p "$TARGET"
sed "s|__WORK_DIR__|$ROOT|g" "$ROOT/deploy/systemd/autoseeker.service.template" > "$TARGET/autoseeker.service"
install -m 644 "$ROOT/deploy/systemd/autoseeker.timer" "$TARGET/autoseeker.timer"
printf '已生成 systemd user 单元：%s
' "$TARGET"
printf '请自行启用：systemctl --user daemon-reload && systemctl --user enable --now autoseeker.timer
'
