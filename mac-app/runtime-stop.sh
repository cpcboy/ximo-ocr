#!/bin/zsh
set -u

support_dir="${OCR_STUDIO_SUPPORT_DIR:-$HOME/Library/Application Support/墨析 OCR 工作台}"
state_dir="$support_dir/runtime"

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
  /bin/rm -f "$pid_file"
}

/usr/bin/curl --noproxy '*' -fsS -X POST http://127.0.0.1:18765/api/model/unload >/dev/null 2>&1 || true
stop_saved_process "$state_dir/frontend.pid"
stop_saved_process "$state_dir/backend.pid"
