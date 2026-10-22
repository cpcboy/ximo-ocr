import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = (file) => readFileSync(new URL(`../${file}`, import.meta.url), "utf8");
test("rc.2 installers have distinct artifact names and matching native versions", () => {
  const windowsName = "MoxiOCR-Windows-x64-1.3.0-rc.2-candidate.exe";
  for (const file of ["windows/build-installer.sh", "windows/build-installer.ps1"]) {
    assert.ok(read(file).includes(windowsName), file);
  }
  assert.ok(read("mac-app/build-installer.sh").includes("MoxiOCR-macOS-arm64-$version-rc.2.dmg"));
  assert.match(read("mac-app/Info.plist"), /<key>CFBundleVersion<\/key>\s*<string>7<\/string>/);
  for (const file of ["windows/installer.nsi", "windows/launcher.nsi"]) {
    assert.ok(read(file).includes('VIProductVersion "1.3.0.2"'), file);
    assert.ok(read(file).includes('"1.3.0-rc.2"'), file);
  }
});
