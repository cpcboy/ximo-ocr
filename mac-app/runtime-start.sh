#!/bin/zsh
set -u

runtime_dir="$(cd "$(dirname "$0")" && pwd)"
support_dir="${OCR_STUDIO_SUPPORT_DIR:-$HOME/Library/Application Support/墨析 OCR 工作台}"
state_dir="$support_dir/runtime"
log_dir="$support_dir/logs"
data_dir="$support_dir/data"

/bin/mkdir -p "$state_dir" "$log_dir" "$data_dir"

process_is_running() {
  local pid_file="$1"
  [[ -f "$pid_file" ]] || return 1
  local saved_pid
  saved_pid="$(tr -cd '0-9' < "$pid_file")"
  [[ -n "$saved_pid" ]] || return 1
  kill -0 "$saved_pid" >/dev/null 2>&1
}

python_bin="$runtime_dir/python/bin/python3"
node_bin="$runtime_dir/node/bin/node"
frontend_dir="$runtime_dir/frontend"

if [[ ! -x "$python_bin" || ! -x "$node_bin" || ! -f "$frontend_dir/server.js" ]]; then
  echo "OCR 应用的运行文件不完整，请重新安装应用。" >&2
  exit 1
fi

export PATH="$runtime_dir/node/bin:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export OCR_STUDIO_DATA_DIR="$data_dir"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONNOUSERSITE=1
unset PYTHONHOME PYTHONPATH
export SSL_CERT_FILE="$runtime_dir/python/lib/python3.11/site-packages/certifi/cacert.pem"

cd "$runtime_dir" || exit 1

if ! process_is_running "$state_dir/backend.pid"; then
  nohup "$python_bin" -m uvicorn backend.app:app \
    --host 127.0.0.1 --port 18765 \
    > "$log_dir/backend.log" 2>&1 &
  echo $! > "$state_dir/backend.pid"
fi

backend_ready=0
for attempt in {1..60}; do
  if /usr/bin/curl --noproxy '*' -fsS http://127.0.0.1:18765/api/health >/dev/null 2>&1; then
    backend_ready=1
    break
  fi
  sleep 0.5
done

if [[ "$backend_ready" -ne 1 ]]; then
  echo "OCR 后端没有成功启动，可查看应用支持目录中的 logs/backend.log。" >&2
  exit 1
fi

if ! process_is_running "$state_dir/frontend.pid"; then
  (
    cd "$frontend_dir" || exit 1
    nohup env PORT=3000 HOST=127.0.0.1 "$node_bin" server.js \
      > "$log_dir/frontend.log" 2>&1 &
    echo $! > "$state_dir/frontend.pid"
  )
fi

frontend_ready=0
for attempt in {1..60}; do
  if /usr/bin/curl --noproxy '*' -fsS http://127.0.0.1:3000/ >/dev/null 2>&1; then
    frontend_ready=1
    break
  fi
  sleep 0.5
done

if [[ "$frontend_ready" -ne 1 ]]; then
  echo "OCR 网页没有成功启动，可查看应用支持目录中的 logs/frontend.log。" >&2
  exit 1
fi
