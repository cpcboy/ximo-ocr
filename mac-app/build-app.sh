#!/bin/zsh
set -euo pipefail

project_dir="$(cd "$(dirname "$0")/.." && pwd)"
build_root="$project_dir/build/macos"
app_bundle="$build_root/墨析 OCR 工作台.app"
contents="$app_bundle/Contents"
resources="$contents/Resources"
macos="$contents/MacOS"
runtime="$resources/OCRStudioRuntime"
icon_source="$build_root/AppIcon-1024.png"
iconset="$build_root/AppIcon.iconset"
swift_cache="$project_dir/build/swift-cache"
swift_sdk="${OCR_STUDIO_SWIFT_SDK:-$(/usr/bin/xcrun --sdk macosx --show-sdk-path)}"
source_commit="$(node "$project_dir/scripts/build_identity.mjs")"

/bin/rm -rf "$app_bundle" "$iconset"
/bin/mkdir -p "$resources" "$macos" "$iconset" "$runtime/node/bin" \
  "$swift_cache/clang" "$swift_cache/swift"

[[ -d "$swift_sdk" ]] || { echo "找不到所选 macOS SDK：$swift_sdk" >&2; exit 1; }
export CLANG_MODULE_CACHE_PATH="$swift_cache/clang"
export SWIFT_MODULE_CACHE_PATH="$swift_cache/swift"

if [[ ! -x "$project_dir/dist/standalone/server.js" ]]; then
  echo "缺少独立网页运行文件，请先执行 npm run build。" >&2
  exit 1
fi

"$project_dir/mac-app/prepare-runtime.sh"
portable_root="$project_dir/build/runtime-cache/macos"
requirements_hash="$(shasum -a 256 "$project_dir/mac-app/requirements-runtime.txt" | cut -d ' ' -f1)"
python_source="$portable_root/runtime-$requirements_hash/python"
node_source="$portable_root/node-v22.23.2-darwin-arm64/bin/node"
if [[ -z "$node_source" ]]; then
  echo "没有找到 Node.js，无法制作本机应用。" >&2
  exit 1
fi

/usr/bin/xcrun --sdk macosx swiftc -sdk "$swift_sdk" -target arm64-apple-macosx14.0 -swift-version 5 \
  "$project_dir/mac-app/OCRStudioApp.swift" \
  -o "$macos/OCRStudio" \
  -framework AppKit \
  -framework WebKit

/usr/bin/xcrun --sdk macosx swiftc -sdk "$swift_sdk" -target arm64-apple-macosx14.0 -swift-version 5 \
  "$project_dir/mac-app/MakeIcon.swift" \
  -o "$build_root/MakeIcon" \
  -framework AppKit
"$build_root/MakeIcon" "$icon_source"

for spec in \
  "16 icon_16x16.png" \
  "32 icon_16x16@2x.png" \
  "32 icon_32x32.png" \
  "64 icon_32x32@2x.png" \
  "128 icon_128x128.png" \
  "256 icon_128x128@2x.png" \
  "256 icon_256x256.png" \
  "512 icon_256x256@2x.png" \
  "512 icon_512x512.png" \
  "1024 icon_512x512@2x.png"
do
  size="${spec%% *}"
  name="${spec#* }"
/usr/bin/sips -z "$size" "$size" "$icon_source" --out "$iconset/$name" >/dev/null
done

if ! /usr/bin/iconutil -c icns "$iconset" -o "$resources/AppIcon.icns"; then
  installed_icon="/Applications/墨析 OCR 工作台.app/Contents/Resources/AppIcon.icns"
  if [[ ! -f "$installed_icon" ]]; then
    echo "系统 iconutil 无法生成图标，且没有可复用的已安装图标。" >&2
    exit 1
  fi
  echo "系统 iconutil 当前不可用，复用已安装应用的同款图标。" >&2
  /usr/bin/ditto "$installed_icon" "$resources/AppIcon.icns"
fi
/usr/bin/ditto "$project_dir/mac-app/Info.plist" "$contents/Info.plist"
/usr/bin/ditto "$project_dir/backend" "$runtime/backend"
/usr/bin/find "$runtime/backend" -type d -name __pycache__ -prune -exec /bin/rm -rf {} +
/usr/bin/ditto "$python_source" "$runtime/python"
/usr/bin/ditto "$project_dir/dist/standalone" "$runtime/frontend"
/usr/bin/ditto "$project_dir/mac-app/runtime-start.sh" "$runtime/start.sh"
/usr/bin/ditto "$project_dir/mac-app/runtime-stop.sh" "$runtime/stop.sh"
/bin/cp -L "$node_source" "$runtime/node/bin/node"
/bin/cp "$portable_root/node-v22.23.2-darwin-arm64/LICENSE" "$runtime/node/LICENSE"
/bin/cp "$project_dir/LICENSE" "$project_dir/THIRD_PARTY_NOTICES.md" "$resources/"
/bin/chmod +x "$runtime/start.sh" "$runtime/stop.sh" "$runtime/node/bin/node"
printf '%s\n' "$source_commit" > "$resources/SOURCE_COMMIT"
"$runtime/python/bin/python3" -I -c 'import mlx.core, transformers, fastapi, fitz'
[[ "$(node "$project_dir/scripts/build_identity.mjs")" == "$source_commit" ]] || { echo "打包期间源码改变，停止签名。" >&2; exit 1; }
/usr/bin/codesign --force --deep --sign - "$app_bundle"
/usr/bin/plutil -lint "$contents/Info.plist"
/usr/bin/codesign --verify --deep --strict "$app_bundle"

echo "$app_bundle"
