import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = (file) => readFileSync(new URL(`../${file}`, import.meta.url), "utf8");
test("Mac-only rc.3 packages Unlimited-OCR 2.0 as build 9 without overwriting rc.2", () => {
  assert.ok(read("mac-app/build-installer.sh").includes("MoxiOCR-macOS-arm64-$version-rc.3.dmg"));
  assert.match(read("mac-app/Info.plist"), /<key>CFBundleVersion<\/key>\s*<string>9<\/string>/);
  assert.match(read("mac-app/Info.plist"), /<key>CFBundleShortVersionString<\/key>\s*<string>1\.3\.0<\/string>/);
});

test("Mac-only rc.3 does not rename or upgrade the Windows rc.2 installer", () => {
  const windowsName = "MoxiOCR-Windows-x64-1.3.0-rc.2-candidate.exe";
  for (const file of ["windows/build-installer.sh", "windows/build-installer.ps1"]) {
    assert.ok(read(file).includes(windowsName), file);
  }
  for (const file of ["windows/installer.nsi", "windows/launcher.nsi"]) {
    assert.ok(read(file).includes('VIProductVersion "1.3.0.2"'), file);
    assert.ok(read(file).includes('"1.3.0-rc.2"'), file);
  }
});
