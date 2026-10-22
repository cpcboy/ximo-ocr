#!/bin/zsh
set -euo pipefail

project_dir="$(cd "$(dirname "$0")" && pwd)"
cd "$project_dir"

export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

if ! command -v python3 >/dev/null 2>&1; then
  echo "没有找到 Python 3。"
  read -k 1 "?按任意键关闭..."
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "没有找到 Node.js / npm。"
  read -k 1 "?按任意键关闭..."
  exit 1
fi

echo "正在检查本机 OCR 运行环境..."
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -r requirements.txt

echo "正在安装网页组件..."
npm ci --ignore-scripts --no-audit --no-fund

echo "正在构建 OCR 工作台..."
npm run build

echo
echo "安装与检查完成。现在可以双击“启动 OCR 工作台.command”。"
read -k 1 "?按任意键关闭..."
