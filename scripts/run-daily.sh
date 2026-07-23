#!/bin/sh
set -u

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
mkdir -p var/logs var/outputs var/cache/security-js var/secrets
RUN_ID=$(date '+%Y%m%d-%H%M%S')
LATEST_LOG="$ROOT/var/logs/latest.log"
ARCHIVE_LOG="$ROOT/var/logs/run-$RUN_ID.log"
EXIT_FILE="$ROOT/var/logs/latest.exit"
: > "$LATEST_LOG"
printf 'run_id=%s
started_at=%s
work_dir=%s
' "$RUN_ID" "$(date '+%Y-%m-%d %H:%M:%S %Z')" "$ROOT" >> "$LATEST_LOG"

if [ ! -x "$ROOT/.venv/bin/autoseeker" ]; then
  echo "缺少已安装 CLI，请先运行 scripts/setup.sh" | tee -a "$LATEST_LOG" >&2
  echo "exit_code=1" > "$EXIT_FILE"
  cp "$LATEST_LOG" "$ARCHIVE_LOG"
  exit 1
fi

"$ROOT/.venv/bin/autoseeker" collect >> "$LATEST_LOG" 2>&1
RUN_EXIT=$?
printf 'finished_at=%s
exit_code=%s
' "$(date '+%Y-%m-%d %H:%M:%S %Z')" "$RUN_EXIT" >> "$LATEST_LOG"
echo "exit_code=$RUN_EXIT" > "$EXIT_FILE"
cp "$LATEST_LOG" "$ARCHIVE_LOG"
cat "$LATEST_LOG"
exit "$RUN_EXIT"
