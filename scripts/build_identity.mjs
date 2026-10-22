import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

export function sourceIdentity(root = projectRoot) {
  const git = (...args) => execFileSync("git", ["-C", root, ...args], { encoding: "utf8" }).trim();
  const names = [...new Set(git("ls-files", "--cached", "--others", "--exclude-standard", "-z").split("\0").filter(Boolean))].sort();
  const hash = createHash("sha256");
  for (const name of names) {
    hash.update(`${name}\0`);
    try { hash.update(readFileSync(path.join(root, name))); }
    catch (error) {
      if (error.code !== "ENOENT") throw error;
      hash.update("<deleted>");
    }
    hash.update("\0");
  }
  return { commit: git("rev-parse", "HEAD"), dirty: Boolean(git("status", "--porcelain", "--untracked-files=normal")), digest: hash.digest("hex") };
}

export function verifyFrontend(root = projectRoot) {
  const expected = sourceIdentity(root);
  const actual = JSON.parse(readFileSync(path.join(root, "dist/standalone/BUILD_SOURCE.json"), "utf8"));
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    throw new Error("前端不是当前源码的构建结果；请重新运行 npm run build。");
  }
  return expected.dirty ? `UNCOMMITTED-${expected.commit}-${expected.digest}` : expected.commit;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  if (process.argv.includes("--require-release")) {
    execFileSync("git", ["-C", projectRoot, "fetch", "origin", "main"], { stdio: "inherit" });
    const identity = sourceIdentity();
    const main = execFileSync("git", ["-C", projectRoot, "rev-parse", "origin/main"], { encoding: "utf8" }).trim();
    if (identity.dirty || identity.commit !== main) throw new Error("发布必须使用已合并到 origin/main 的干净源码。");
    console.log(identity.commit);
  } else {
    console.log(verifyFrontend());
  }
}
