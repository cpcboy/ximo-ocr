import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, rmSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { collectNotices } from "../scripts/collect_notices.mjs";
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";

test("bundled notices preserve ordinary, scoped and nested package licenses", () => {
  const root = mkdtempSync(path.join(os.tmpdir(), "moxi-notices-test-"));
  try {
    const packages = [
      ["plain", "plain", "LICENSE", "MIT"],
      ["@scope/scoped", "@scope/scoped", "LICENSE-MIT", "MIT"],
      ["plain/node_modules/nested", "nested", "COPYING.txt", "BSD-3-Clause"],
    ];
    for (const [location, name, file, license] of packages) {
      const directory = path.join(root, "node_modules", location);
      mkdirSync(directory, { recursive: true });
      writeFileSync(path.join(directory, "package.json"), JSON.stringify({ name, version: "1.0.0", license }));
      writeFileSync(path.join(directory, file), `${name} synthetic notice`);
    }
    const output = path.join(root, "output");
    collectNotices(root, output);
    const index = JSON.parse(readFileSync(path.join(output, "index.json"), "utf8"));
    assert.equal(index.length, packages.length);
    for (const [, name, file, license] of packages) {
      const entry = index.find(item => item.name === name);
      assert.equal(entry.license, license);
      assert.deepEqual(entry.files, [file]);
      const label = `${name}@1.0.0`.replace(/[^a-zA-Z0-9@._-]/g, "_");
      assert.equal(readFileSync(path.join(output, label, file), "utf8"), `${name} synthetic notice`);
    }
  } finally {
    rmSync(root, { recursive: true }); // Only this synthetic mkdtemp test directory.
  }
});

test("runtime packages without license text fail until a pinned notice is supplied", () => {
  const root = mkdtempSync(path.join(os.tmpdir(), "moxi-notices-test-"));
  try {
    const pkg = JSON.stringify({ name: "missing", version: "1.0.0", license: "MIT" });
    for (const parent of ["node_modules/missing", "dist/standalone/node_modules/missing"]) {
      mkdirSync(path.join(root, parent), { recursive: true });
      writeFileSync(path.join(root, parent, "package.json"), pkg);
    }
    const output = path.join(root, "output");
    assert.throws(() => collectNotices(root, output), /实际打包依赖缺少许可材料/);
    const notice = "synthetic test license";
    const directory = path.join(root, "third-party/licenses");
    mkdirSync(directory, { recursive: true });
    const file = path.join(directory, "missing.txt");
    writeFileSync(file, notice);
    writeFileSync(path.join(directory, "index.json"), JSON.stringify({ "missing@1.0.0": {
      file: "missing.txt", source: "https://example.invalid/pinned/license",
      sha256: createHash("sha256").update(notice).digest("hex"),
    } }));
    collectNotices(root, output);
    assert.equal(readFileSync(path.join(output, "missing@1.0.0/LICENSE"), "utf8"), notice);
    assert.ok(JSON.parse(readFileSync(path.join(output, "missing@1.0.0/SOURCE.json"), "utf8")).source);
    writeFileSync(file, "corrupted");
    assert.throws(() => collectNotices(root, output), /许可内容校验失败/);
  } finally {
    rmSync(root, { recursive: true }); // Only this synthetic mkdtemp test directory.
  }
});

test("Windows-style Git checkout preserves pinned license bytes", () => {
  const root = mkdtempSync(path.join(os.tmpdir(), "moxi-license-checkout-"));
  const git = (...args) => execFileSync("git", ["-C", root, ...args], { stdio: "pipe" });
  try {
    git("init");
    const relative = "third-party/licenses/MIT-standard.txt";
    const original = readFileSync(new URL(`../${relative}`, import.meta.url));
    mkdirSync(path.join(root, "third-party/licenses"), { recursive: true });
    writeFileSync(path.join(root, ".gitattributes"), readFileSync(new URL("../.gitattributes", import.meta.url)));
    writeFileSync(path.join(root, relative), original);
    git("add", ".gitattributes", relative);
    const destination = `${path.join(root, "checkout").replaceAll("\\", "/")}/`;
    git("-c", "core.autocrlf=true", "checkout-index", `--prefix=${destination}`, "--all");
    assert.deepEqual(readFileSync(path.join(destination, relative)), original);
  } finally {
    rmSync(root, { recursive: true }); // Only this synthetic mkdtemp test repository.
  }
});
