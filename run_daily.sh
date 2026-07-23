#!/bin/zsh
set -u
set -o pipefail

ROOT="${0:A:h}"
cd "$ROOT"
mkdir -p var/logs var/outputs var/cache/security-js var/secrets

RUN_ID="$(date '+%Y%m%d-%H%M%S')"
LATEST_LOG="$ROOT/var/logs/latest.log"
ARCHIVE_LOG="$ROOT/var/logs/run-$RUN_ID.log"
EXIT_FILE="$ROOT/var/logs/latest.exit"

: > "$LATEST_LOG"
{
  echo "run_id=$RUN_ID"
  echo "started_at=$(date '+%Y-%m-%d %H:%M:%S %Z')"
  echo "work_dir=$ROOT"
} >> "$LATEST_LOG"

if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  echo "缺少 .venv，请先运行 ./setup.sh" | tee -a "$LATEST_LOG" >&2
  echo "exit_code=1" > "$EXIT_FILE"
  cp "$LATEST_LOG" "$ARCHIVE_LOG"
  exit 1
fi

if [[ ( -d "$ROOT/var/browser-profile" || -d "$ROOT/.browser-profile" ) && "${SKIP_BROWSER_AUTH:-0}" != "1" ]]; then
  "$ROOT/.venv/bin/python" "$ROOT/browser_auth.py" --headless --timeout 30 2>&1 | tee -a "$LATEST_LOG"
  AUTH_EXIT=${pipestatus[1]}
  if [[ "$AUTH_EXIT" -ne 0 ]]; then
    {
      echo "finished_at=$(date '+%Y-%m-%d %H:%M:%S %Z')"
      echo "exit_code=$AUTH_EXIT"
    } >> "$LATEST_LOG"
    echo "exit_code=$AUTH_EXIT" > "$EXIT_FILE"
    cp "$LATEST_LOG" "$ARCHIVE_LOG"
    echo "登录状态失效，请运行 ./login.sh 完成扫码登录。" >&2
    exit "$AUTH_EXIT"
  fi
fi

"$ROOT/.venv/bin/python" "$ROOT/boss_jobs.py" 2>&1 | tee -a "$LATEST_LOG"
RUN_EXIT=${pipestatus[1]}

{
  echo "finished_at=$(date '+%Y-%m-%d %H:%M:%S %Z')"
  echo "exit_code=$RUN_EXIT"
} >> "$LATEST_LOG"
echo "exit_code=$RUN_EXIT" > "$EXIT_FILE"
cp "$LATEST_LOG" "$ARCHIVE_LOG"

echo "日志已保存：$LATEST_LOG"
exit "$RUN_EXIT"
