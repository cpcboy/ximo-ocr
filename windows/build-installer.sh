#!/bin/zsh
set -euo pipefail

project_dir="$(cd "$(dirname "$0")/.." && pwd)"
build_root="$project_dir/build/windows"
cache_root="$build_root/cache"
stage_root="$build_root/stage"
output_root="$build_root/output"
icon_png="$build_root/AppIcon-256.png"
icon_file="$build_root/AppIcon.ico"
python_version="3.12.10"
node_version="22.23.2"
python_zip="$cache_root/python-$python_version-embed-amd64.zip"
node_zip="$cache_root/node-v$node_version-win-x64.zip"
installer_file="$output_root/MoxiOCR-Windows-x64-1.3.0-candidate.exe"
source_commit="$(node "$project_dir/scripts/build_identity.mjs")"

[[ ! -e "$installer_file" ]] || { echo "请先归档旧安装包：$installer_file" >&2; exit 1; }
/bin/rm -rf "$stage_root"
/bin/mkdir -p \
  "$cache_root" \
  "$stage_root/app" \
  "$stage_root/runtime/python/Lib/site-packages" \
  "$stage_root/runtime/node" \
  "$output_root"

if [[ ! -x "$project_dir/dist/standalone/server.js" ]]; then
  echo "缺少网页独立运行文件，请先执行 npm run build。" >&2
  exit 1
fi

download_if_missing() {
  local url="$1"
  local destination="$2"
  local expected="$3"
  if [[ ! -s "$destination" ]] || [[ "$(shasum -a 256 "$destination" | cut -d ' ' -f1)" != "$expected" ]]; then
    /usr/bin/curl -fL --retry 4 --retry-delay 2 \
      "$url" \
      -o "$destination.part"
    [[ "$(shasum -a 256 "$destination.part" | cut -d ' ' -f1)" == "$expected" ]] || { echo "Runtime checksum failed" >&2; exit 1; }
    /bin/mv "$destination.part" "$destination"
  fi
}

download_if_missing \
  "https://www.python.org/ftp/python/$python_version/python-$python_version-embed-amd64.zip" \
  "$python_zip" "4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3"
download_if_missing \
  "https://nodejs.org/dist/v$node_version/node-v$node_version-win-x64.zip" \
  "$node_zip" "1177b4137ba5adaa56354ae40f1080c7450e8ae09cecb47da459d1c52ac99f97"

/usr/bin/ditto -x -k "$python_zip" "$stage_root/runtime/python"
/usr/bin/ditto "$project_dir/windows/python312._pth" \
  "$stage_root/runtime/python/python312._pth"
/usr/bin/ditto "$project_dir/windows/backend_bootstrap.py" \
  "$stage_root/runtime/python/backend_bootstrap.py"
/usr/bin/ditto "$project_dir/windows/windows_launcher.py" \
  "$stage_root/runtime/python/windows_launcher.py"

"${OCR_STUDIO_BUILD_PYTHON:-$project_dir/.venv/bin/python}" -m pip install \
  --disable-pip-version-check \
  --no-compile \
  --only-binary=:all: \
  --platform win_amd64 \
  --python-version 3.12 \
  --implementation cp \
  --abi cp312 \
  --target "$stage_root/runtime/python/Lib/site-packages" \
  -r "$project_dir/windows/requirements-bootstrap.txt"

node_temp="$build_root/node-extracted"
/bin/rm -rf "$node_temp"
/bin/mkdir -p "$node_temp"
/usr/bin/ditto -x -k "$node_zip" "$node_temp"
/bin/cp "$node_temp/node-v$node_version-win-x64/node.exe" \
  "$stage_root/runtime/node/node.exe"
/bin/cp "$node_temp/node-v$node_version-win-x64/LICENSE" "$stage_root/runtime/node/LICENSE"
/bin/cp "$project_dir/LICENSE" "$project_dir/THIRD_PARTY_NOTICES.md" "$stage_root/"

/usr/bin/ditto "$project_dir/backend" "$stage_root/app/backend"
/usr/bin/find "$stage_root/app/backend" \
  -type d -name __pycache__ -prune -exec /bin/rm -rf {} +
/usr/bin/ditto "$project_dir/dist/standalone" "$stage_root/app/frontend"
/usr/bin/ditto "$project_dir/windows/THIRD_PARTY_NOTICES.txt" \
  "$stage_root/THIRD_PARTY_NOTICES.txt"
printf '%s\n' "$source_commit" > "$stage_root/SOURCE_COMMIT"

if [[ ! -s "$project_dir/build/macos/AppIcon-1024.png" ]]; then
  /usr/bin/xcrun --sdk macosx swiftc -target arm64-apple-macosx14.0 -swift-version 5 \
    "$project_dir/mac-app/MakeIcon.swift" \
    -o "$build_root/MakeIcon" \
    -framework AppKit
  "$build_root/MakeIcon" "$build_root/AppIcon-1024.png"
  icon_source="$build_root/AppIcon-1024.png"
else
  icon_source="$project_dir/build/macos/AppIcon-1024.png"
fi
/usr/bin/sips -z 256 256 "$icon_source" --out "$icon_png" >/dev/null
/usr/bin/sips -s format ico "$icon_png" --out "$icon_file" >/dev/null
[[ "$(node "$project_dir/scripts/build_identity.mjs")" == "$source_commit" ]] || { echo "打包期间源码改变，停止生成安装包。" >&2; exit 1; }

/opt/homebrew/bin/makensis \
  -DOUTPUT_FILE="$stage_root/MoxiOCRStudio.exe" \
  -DICON_FILE="$icon_file" \
  "$project_dir/windows/launcher.nsi"

/opt/homebrew/bin/makensis \
  -DSTAGE_DIR="$stage_root" \
  -DOUTPUT_FILE="$installer_file" \
  -DICON_FILE="$icon_file" \
  "$project_dir/windows/installer.nsi"

(
  cd "$output_root"
  /usr/bin/shasum -a 256 "$(basename "$installer_file")" \
    > "$(basename "$installer_file").sha256"
)
/usr/bin/ditto "$project_dir/windows/Windows安装说明.txt" \
  "$output_root/Windows安装说明.txt"
/usr/bin/file "$installer_file"
/usr/bin/du -h "$installer_file"
echo "$installer_file"
