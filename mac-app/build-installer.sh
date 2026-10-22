#!/bin/zsh
set -euo pipefail
project_dir="$(cd "$(dirname "$0")/.." && pwd)"
version="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$project_dir/mac-app/Info.plist")"
output="$project_dir/build/macos/output"
destination="$output/MoxiOCR-macOS-arm64-$version.dmg"
[[ ! -e "$destination" ]] || { echo "请先归档旧安装包：$destination" >&2; exit 1; }
node "$project_dir/scripts/build_identity.mjs" --require-release
(cd "$project_dir" && npm run build)
"$project_dir/mac-app/build-app.sh"
stage="$(mktemp -d "$project_dir/build/macos/dmg-stage.XXXXXX")"
trap '/bin/rm -rf "$stage"' EXIT
ditto "$project_dir/build/macos/墨析 OCR 工作台.app" "$stage/墨析 OCR 工作台.app"
ln -s /Applications "$stage/Applications"
mkdir -p "$output"
hdiutil create -volname "墨析 OCR 工作台" -srcfolder "$stage" -format UDZO "$destination"
(cd "$output" && shasum -a 256 "${destination:t}" > "${destination:t}.sha256")
hdiutil verify "$destination"
echo "$destination"
