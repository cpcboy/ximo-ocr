import { copyFileSync, existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import path from "node:path";

function walkPackages(directory, visit) {
  if (!existsSync(directory)) return;
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    if (!entry.isDirectory() || entry.name.startsWith(".")) continue;
    const full = path.join(directory, entry.name);
    if (entry.name.startsWith("@")) {
      for (const scoped of readdirSync(full, { withFileTypes: true })) {
        if (scoped.isDirectory()) visit(path.join(full, scoped.name));
      }
    } else visit(full);
  }
}

export function collectNotices(root, output) {
  const inventory = [];
  const fallbackRoot = path.join(root, "third-party/licenses");
  const fallbackIndex = path.join(fallbackRoot, "index.json");
  const fallbacks = existsSync(fallbackIndex) ? JSON.parse(readFileSync(fallbackIndex, "utf8")) : {};
  mkdirSync(output, { recursive: true });
  function packageNotice(directory) {
    const metadata = path.join(directory, "package.json");
    if (!existsSync(metadata)) return;
    const pkg = JSON.parse(readFileSync(metadata, "utf8"));
    const label = `${pkg.name}@${pkg.version}`.replace(/[^a-zA-Z0-9@._-]/g, "_");
    const notices = readdirSync(directory, { withFileTypes: true })
      .filter(entry => entry.isFile() && /^(licen[cs]e|copying|notice)([.-].*)?$/i.test(entry.name));
    const target = path.join(output, label);
    const fallback = fallbacks[`${pkg.name}@${pkg.version}`];
    if (notices.length || fallback) mkdirSync(target, { recursive: true });
    for (const entry of notices) copyFileSync(path.join(directory, entry.name), path.join(target, entry.name));
    const files = notices.map(entry => entry.name);
    if (!notices.length && fallback) {
      if (path.basename(fallback.file) !== fallback.file) throw new Error("许可补充文件必须位于 licenses 根目录");
      const license = path.join(fallbackRoot, fallback.file);
      const sha256 = createHash("sha256").update(readFileSync(license)).digest("hex");
      if (sha256 !== fallback.sha256) throw new Error(`许可内容校验失败: ${pkg.name}`);
      copyFileSync(license, path.join(target, "LICENSE"));
      writeFileSync(path.join(target, "SOURCE.json"), JSON.stringify(fallback, null, 2));
      files.push("LICENSE", "SOURCE.json");
    }
    inventory.push({ name: pkg.name, version: pkg.version, license: pkg.license ?? null,
      repository: pkg.repository ?? null, files });
    walkPackages(path.join(directory, "node_modules"), packageNotice);
  }
  walkPackages(path.join(root, "node_modules"), packageNotice);
  const missing = [];
  function checkRuntime(directory) {
    const metadata = path.join(directory, "package.json");
    if (!existsSync(metadata)) return;
    const pkg = JSON.parse(readFileSync(metadata, "utf8"));
    if (!inventory.some(entry => entry.name === pkg.name && entry.version === pkg.version && entry.files.length)) {
      missing.push(`${pkg.name}@${pkg.version}`);
    }
    walkPackages(path.join(directory, "node_modules"), checkRuntime);
  }
  walkPackages(path.join(root, "dist/standalone/node_modules"), checkRuntime);
  if (missing.length) throw new Error(`实际打包依赖缺少许可材料: ${missing.join(", ")}`);
  writeFileSync(path.join(output, "index.json"), JSON.stringify(inventory, null, 2));
}
