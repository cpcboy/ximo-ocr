#!/bin/zsh
set -euo pipefail
project_dir="$(cd "$(dirname "$0")/.." && pwd)"
cache="$project_dir/build/runtime-cache/macos"
mkdir -p "$cache"
python_url="https://github.com/astral-sh/python-build-standalone/releases/download/20261021/cpython-3.11.17%2B20261021-aarch64-apple-darwin-install_only_stripped.tar.gz"
python_sha="1d1335d9d526bc37061af3fe72b0edd88056d7e7d9488eb631946b10b4ab97bb"
node_url="https://nodejs.org/dist/v22.23.2/node-v22.23.2-darwin-arm64.tar.gz"
node_sha="61130f394c1630d211dd50aecc4353d379480f36d3ac913cd85dbba1aed585c6"

fetch_verified() {
  local url="$1" destination="$2" expected="$3"
  if [[ ! -f "$destination" ]] || [[ "$(shasum -a 256 "$destination" | cut -d ' ' -f1)" != "$expected" ]]; then
    curl --fail --location --retry 3 --connect-timeout 20 "$url" -o "$destination.part"
    [[ "$(shasum -a 256 "$destination.part" | cut -d ' ' -f1)" == "$expected" ]] || { echo "Runtime checksum failed" >&2; exit 1; }
    mv "$destination.part" "$destination"
  fi
}

fetch_verified "$python_url" "$cache/python.tar.gz" "$python_sha"
fetch_verified "$node_url" "$cache/node.tar.gz" "$node_sha"
vlm_revision="c3ae82e2e79ee553c534c7b4efea73bc85122ab2"
vlm_source="$cache/mlx-vlm-$vlm_revision.zip"
fetch_verified "https://codeload.github.com/shuuul/mlx-vlm/zip/$vlm_revision" "$vlm_source" \
  "b4b96b728fc617592965d656b72b90311c0491806bf83a97926732fa79828eec"
if [[ ! -x "$cache/node-v22.23.2-darwin-arm64/bin/node" ]]; then
  tar -xzf "$cache/node.tar.gz" -C "$cache"
fi
export PYTHONNOUSERSITE=1
unset PYTHONPATH PYTHONHOME
requirements_hash="$(shasum -a 256 "$project_dir/mac-app/requirements-runtime.txt" | cut -d ' ' -f1)"
environment="$cache/runtime-$requirements_hash"
mkdir -p "$environment/wheels"
if [[ ! -x "$environment/python/bin/python3" ]]; then
  tar -xzf "$cache/python.tar.gz" -C "$environment"
fi
if [[ ! -f "$environment/ready" ]]; then
  # Build the reviewed adapter, never a floating branch or remote model Python.
  "$environment/python/bin/python3" -I -m pip install --only-binary=:all: \
    'setuptools==80.9.0' 'wheel==0.45.1' 'packaging==26.3'
  "$environment/python/bin/python3" -I -m pip wheel --no-deps --no-build-isolation \
    --wheel-dir "$environment/wheels" "$vlm_source"
  vlm_wheel="$environment/wheels/mlx_vlm-0.7.11-py3-none-any.whl"
  [[ -f "$vlm_wheel" ]] || { echo "缺少固定版本的 MLX 2.0 适配 wheel" >&2; exit 1; }
  # Resolve wheels for the advertised minimum OS, not for the newer build host.
  "$environment/python/bin/python3" -I -m pip download --only-binary=:all: \
    --platform macosx_14_0_arm64 --dest "$environment/wheels" \
    -r "$project_dir/mac-app/requirements-runtime.txt" "$vlm_wheel"
  "$environment/python/bin/python3" -I -m pip install --no-index --find-links "$environment/wheels" \
    --only-binary=:all: --no-compile -r "$project_dir/mac-app/requirements-runtime.txt" "$vlm_wheel"
  "$environment/python/bin/python3" -I -c 'import mlx.core, mlx_vlm, transformers, fastapi, fitz, PIL, safetensors'
  touch "$environment/ready"
fi
"$environment/python/bin/python3" -I -c 'import mlx.core, mlx_vlm, transformers, fastapi, fitz, PIL, safetensors; print("Portable MLX v2 runtime imports OK")'
