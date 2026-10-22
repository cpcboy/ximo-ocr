import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync, readFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { sourceIdentity, verifyFrontend } from "../scripts/build_identity.mjs";

test("build provenance rejects stale output and labels uncommitted candidates", () => {
  const root = mkdtempSync(path.join(os.tmpdir(), "moxi-build-test-"));
  const git = (...args) => execFileSync("git", ["-C", root, ...args], { stdio: "pipe" });
  try {
    git("init");
    writeFileSync(path.join(root, ".gitignore"), "dist/\n");
    writeFileSync(path.join(root, "source.txt"), "original");
    git("add", ".gitignore", "source.txt");
    git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "test");
    mkdirSync(path.join(root, "dist/standalone"), { recursive: true });
    const stamp = path.join(root, "dist/standalone/BUILD_SOURCE.json");
    const clean = sourceIdentity(root);
    writeFileSync(stamp, JSON.stringify(clean));
    assert.equal(verifyFrontend(root), clean.commit);
    writeFileSync(path.join(root, "source.txt"), "changed");
    assert.throws(() => verifyFrontend(root), /重新运行/);
    writeFileSync(stamp, JSON.stringify(sourceIdentity(root)));
    assert.match(verifyFrontend(root), /^UNCOMMITTED-/);
    writeFileSync(path.join(root, "source.txt"), "original");
    assert.throws(() => verifyFrontend(root), /重新运行/);
  } finally {
    rmSync(root, { recursive: true }); // Only this synthetic mkdtemp test repository.
  }
});

test("packagers verify source both before and after copying runtime", () => {
  for (const file of ["../mac-app/build-app.sh", "../windows/build-installer.sh", "../windows/build-installer.ps1"]) {
    const source = readFileSync(new URL(file, import.meta.url), "utf8");
    assert.equal(source.match(/scripts[\\/]build_identity\.mjs/g)?.length, 2);
    assert.match(source, /打包期间源码改变/);
  }
});
