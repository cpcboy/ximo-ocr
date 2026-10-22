import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const css = readFileSync(new URL("../app/globals.css", import.meta.url), "utf8");

// These are source contracts, not a substitute for native WebKit visual checks.
function declarations(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const block = css.match(new RegExp(`(?:^|\\n)\\s*${escaped}\\s*\\{([^{}]*)\\}`));
  assert.ok(block, `Missing rule: ${selector}`);
  return Object.fromEntries(
    [...block[1].matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)]
      .map(([, name, value]) => [name, value.trim()]),
  );
}

test("shared result colors are scoped to the reader paper, including nested markup", () => {
  const paper = declarations(".moxi-reader-paper");
  const aliases = {
    "--surface": "--reader-surface",
    "--surface-2": "--reader-paper",
    "--surface-3": "--reader-surface-soft",
    "--ink": "--reader-ink",
    "--ink-soft": "--reader-ink",
    "--muted": "--reader-muted",
    "--line": "--reader-line",
    "--line-strong": "--reader-line",
    "--accent": "--reader-accent",
    "--accent-soft": "--reader-accent-soft",
  };
  for (const [alias, reader] of Object.entries(aliases)) {
    assert.equal(paper[alias], `var(${reader})`, alias);
  }
  // All variables used by the shared rich-result rules need a local mapping.
  const resultRules = css.slice(css.indexOf(".rich-result-preview {"), css.indexOf(".editor-loading,"));
  const used = new Set([...resultRules.matchAll(/var\((--[\w-]+)\)/g)].map(([, name]) => name));
  for (const name of used) {
    if (name === "--font-mono") continue; // Font family is intentionally shared.
    assert.ok(name in aliases, `Unmapped result color: ${name}`);
  }
  assert.equal(declarations(":root")["--surface"], "#ffffff");
  assert.equal(declarations(':root[data-theme="dark"]')["--surface"], "#1a1d21");
});

function luminance(hex) {
  assert.match(hex, /^#[0-9a-f]{3}([0-9a-f]{3})?$/i);
  const digits = hex.length === 4 ? [...hex.slice(1)].map(c => c + c).join("") : hex.slice(1);
  const [r, g, b] = digits.match(/../g).map(channel => {
    const value = Number.parseInt(channel, 16) / 255;
    return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

test("reader text has at least 4.5:1 contrast on paper, headings and code surfaces", () => {
  const light = declarations(".moxi-reader");
  for (const [label, palette] of [
    ["light / system-light", light],
    ["sepia", { ...light, ...declarations(".moxi-reader-theme-sepia") }],
    ["dark", { ...light, ...declarations(".moxi-reader-theme-dark") }],
    ["system-dark", { ...light, ...declarations(".moxi-reader-theme-system") }],
  ]) {
    const foreground = luminance(palette["--reader-ink"]);
    for (const surface of ["--reader-paper", "--reader-surface", "--reader-surface-soft", "--reader-accent-soft"]) {
      const background = luminance(palette[surface]);
      const contrast = (Math.max(foreground, background) + 0.05) / (Math.min(foreground, background) + 0.05);
      assert.ok(contrast >= 4.5, `${label} ${surface}: ${contrast.toFixed(2)}:1`);
    }
  }
});

test("system-dark reader palette matches explicit dark mode", () => {
  assert.match(css, /@media\s*\(prefers-color-scheme:\s*dark\)\s*\{\s*\.moxi-reader-theme-system/);
  assert.deepEqual(declarations(".moxi-reader-theme-system"), declarations(".moxi-reader-theme-dark"));
});
