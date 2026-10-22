#!/bin/zsh
set -u

project_dir="$(cd "$(dirname "$0")" && pwd)"
cd "$project_dir" || exit 1

export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

runtime_dir="$project_dir/.runtime"
log_dir="$project_dir/logs"
mkdir -p "$runtime_dir" "$log_dir"

show_error() {
  local message="$1"
  /usr/bin/osascript -e "display dialog \"$message\" buttons {\"好\"} default button \"好\" with icon stop" >/dev/null 2>&1 || true
  echo "$message"
}

process_is_running() {
  local pid_file="$1"
  [[ -f "$pid_file" ]] || return 1
  local saved_pid
  saved_pid="$(tr -cd '0-9' < "$pid_file")"
  [[ -n "$saved_pid" ]] || return 1
  kill -0 "$saved_pid" >/dev/null 2>&1
}

if [[ ! -x "$project_dir/.venv/bin/python" ]]; then
  show_error "OCR 工作台缺少本机运行环境。请先双击“安装或修复 OCR 工作台.command”。"
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  show_error "没有找到网页运行环境 Node.js。请先安装或恢复 LM Studio/Codex 使用的 Node.js。"
  exit 1
fi

if [[ ! -d "$project_dir/dist" ]]; then
  show_error "网页尚未构建。请先双击“安装或修复 OCR 工作台.command”。"
  exit 1
fi

if ! process_is_running "$runtime_dir/backend.pid"; then
  nohup "$project_dir/.venv/bin/python" -m uvicorn backend.app:app \
    --host 127.0.0.1 --port 18765 \
    > "$log_dir/backend.log" 2>&1 &
  echo $! > "$runtime_dir/backend.pid"
fi

backend_ready=0
for attempt in {1..60}; do
  if /usr/bin/curl -fsS http://127.0.0.1:18765/api/health >/dev/null 2>&1; then
    backend_ready=1
    break
  fi
  sleep 0.5
done

if [[ "$backend_ready" -ne 1 ]]; then
  show_error "OCR 后端没有成功启动。可查看项目 logs/backend.log 中的原因。"
  exit 1
fi

if ! process_is_running "$runtime_dir/frontend.pid"; then
  nohup env PORT=3000 npm run start \
    > "$log_dir/frontend.log" 2>&1 &
  echo $! > "$runtime_dir/frontend.pid"
fi

frontend_ready=0
for attempt in {1..60}; do
  if /usr/bin/curl -fsS http://127.0.0.1:3000/ >/dev/null 2>&1; then
    frontend_ready=1
    break
  fi
  sleep 0.5
done

if [[ "$frontend_ready" -ne 1 ]]; then
  show_error "OCR 网页没有成功启动。可查看项目 logs/frontend.log 中的原因。"
  exit 1
fi

if [[ "${OCR_STUDIO_NO_BROWSER:-0}" != "1" ]]; then
  open "http://127.0.0.1:3000/"
fi
