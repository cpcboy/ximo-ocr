"""Auditable, App-only deployment. Never reads or changes OCR business data."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALLED = Path("/Applications/墨析 OCR 工作台.app")


def manifest(app: Path) -> dict[str, str]:
    if not app.is_dir() or app.is_symlink() or app.suffix != ".app":
        raise RuntimeError("目标必须是实际 .app 目录")
    result = {}
    for path in sorted(app.rglob("*")):
        relative = path.relative_to(app).as_posix()
        if path.is_symlink():
            result[relative] = "symlink:" + os.readlink(path)
        elif path.is_file():
            with path.open("rb") as source:
                result[relative] = hashlib.file_digest(source, "sha256").hexdigest()
    return result


def git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def replace_app(candidate: Path, expected: Path, backup: Path, *, rollback: bool) -> None:
    if not candidate.is_absolute() or candidate.resolve() == INSTALLED.resolve():
        raise RuntimeError("候选应用必须是独立的绝对路径")
    expected_manifest = json.loads(expected.read_text())
    if manifest(INSTALLED) != expected_manifest:
        raise RuntimeError("当前已安装应用存在漂移；停止部署，请人工核对")
    for port in (3000, 18765):
        with socket.socket() as connection:
            connection.settimeout(1)
            if connection.connect_ex(("127.0.0.1", port)) == 0:
                raise RuntimeError("请先正常退出墨析，确认任务结束；部署器不会强行终止服务")
    if not rollback:
        if git("status", "--porcelain", "--untracked-files=normal"):
            raise RuntimeError("工作区不干净；只允许从已合并的干净版本部署")
        subprocess.run(["git", "-C", str(ROOT), "fetch", "origin", "main"], check=True)
        head = git("rev-parse", "HEAD")
        if head != git("rev-parse", "origin/main"):
            raise RuntimeError("当前版本不是远端 main；先 review / 合并 PR")
        if (candidate / "Contents/Resources/SOURCE_COMMIT").read_text().strip() != head:
            raise RuntimeError("安装包源码版本不匹配，请从合并版本重新构建")
    subprocess.run(["codesign", "--verify", "--deep", "--strict", str(candidate)], check=True)
    candidate_manifest = manifest(candidate)
    backup = backup.resolve()
    if backup.is_relative_to(ROOT / "build") or backup.is_relative_to(INSTALLED):
        raise RuntimeError("回退目录不能放在构建清理目录或已安装应用内部")
    backup.mkdir(parents=True, exist_ok=False)
    if backup.stat().st_dev != INSTALLED.parent.stat().st_dev:
        raise RuntimeError("回退目录须与 Applications 位于同一文件系统，以便原子移动")
    # mkdtemp is a private, exact destination; no existing application is overwritten.
    staging = Path(tempfile.mkdtemp(prefix=".MoxiOCR-install-", dir=INSTALLED.parent)) / INSTALLED.name
    subprocess.run(["ditto", str(candidate), str(staging)], check=True)
    if manifest(staging) != candidate_manifest:
        raise RuntimeError(f"候选应用复制校验失败，尚未更换应用；暂存路径 {staging}")
    previous = backup / "previous.app"
    INSTALLED.rename(previous)
    try:
        if manifest(previous) != expected_manifest:
            raise RuntimeError("回退副本校验失败")
        staging.rename(INSTALLED)
    except BaseException:
        previous.rename(INSTALLED)
        raise
    staging.parent.rmdir()
    record = {"previous": str(previous), "installed": str(INSTALLED),
              "previous_manifest": expected_manifest, "installed_manifest": candidate_manifest}
    (backup / "deployment.json").write_text(json.dumps(record, ensure_ascii=False, indent=2))
    (backup / "installed-manifest.json").write_text(json.dumps(candidate_manifest, sort_keys=True))
    print(json.dumps({"installed": str(INSTALLED), "backup": str(previous), "audit": str(backup / "deployment.json")}, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    snapshot = commands.add_parser("snapshot")
    snapshot.add_argument("output", type=Path)
    for name in ("install", "rollback"):
        command = commands.add_parser(name)
        command.add_argument("candidate", type=Path)
        command.add_argument("--expected-current", type=Path, required=True)
        command.add_argument("--backup-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "snapshot":
        with args.output.open("x", encoding="utf-8") as output:
            json.dump(manifest(INSTALLED), output, sort_keys=True)
        print(args.output)
    else:
        replace_app(args.candidate, args.expected_current, args.backup_dir, rollback=args.command == "rollback")


if __name__ == "__main__":
    main()
