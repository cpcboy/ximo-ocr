#!/bin/zsh
set -u

project_dir="$(cd "$(dirname "$0")" && pwd)"
runtime_dir="$project_dir/.runtime"

stop_saved_process() {
  local pid_file="$1"
  [[ -f "$pid_file" ]] || return 0
  local saved_pid
  saved_pid="$(tr -cd '0-9' < "$pid_file")"
  if [[ -n "$saved_pid" ]] && kill -0 "$saved_pid" >/dev/null 2>&1; then
    /usr/bin/pkill -TERM -P "$saved_pid" >/dev/null 2>&1 || true
    kill "$saved_pid" >/dev/null 2>&1 || true
    for attempt in {1..20}; do
      kill -0 "$saved_pid" >/dev/null 2>&1 || break
      sleep 0.1
    done
    if kill -0 "$saved_pid" >/dev/null 2>&1; then
      /usr/bin/pkill -KILL -P "$saved_pid" >/dev/null 2>&1 || true
      kill -KILL "$saved_pid" >/dev/null 2>&1 || true
    fi
  fi
  rm -f "$pid_file"
}

/usr/bin/curl -fsS -X POST http://127.0.0.1:18765/api/model/unload >/dev/null 2>&1 || true
stop_saved_process "$runtime_dir/frontend.pid"
stop_saved_process "$runtime_dir/backend.pid"

if [[ "${OCR_STUDIO_SILENT:-0}" != "1" ]]; then
  /usr/bin/osascript -e 'display notification "本机服务已经停止" with title "墨析 OCR 工作台"' >/dev/null 2>&1 || true
fi
