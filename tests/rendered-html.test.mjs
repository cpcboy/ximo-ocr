import assert from "node:assert/strict";
import { readFile, stat } from "node:fs/promises";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request("http://localhost/", {
      headers: { accept: "text/html" },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("server-renders the local OCR workspace", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<title>墨析 · 本地 OCR 工作台<\/title>/);
  assert.match(html, /批量识别图片、PDF、Office 文档与压缩包/);
  assert.match(html, /文件仅在本机/);
  assert.match(html, /新建扫描/);
  assert.doesNotMatch(html, /Your site is taking shape|Building your site/);
});

test("keeps the browser and local engine contracts aligned", async () => {
  const [page, reader, backend, startCommand, stopCommand, macApp] =
    await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/document-reader.tsx", import.meta.url), "utf8"),
    readFile(new URL("../backend/app.py", import.meta.url), "utf8"),
    readFile(
      new URL(
        `../${encodeURIComponent("启动 OCR 工作台.command")}`,
        import.meta.url,
      ),
      "utf8",
    ),
    readFile(
      new URL(
        `../${encodeURIComponent("停止 OCR 工作台.command")}`,
        import.meta.url,
      ),
      "utf8",
    ),
    readFile(new URL("../mac-app/OCRStudioApp.swift", import.meta.url), "utf8"),
  ]);

  assert.match(page, /http:\/\/127\.0\.0\.1:18765/);
  assert.match(page, /\.pdf.*\.png.*\.docx.*\.xlsx.*\.pptx.*\.zip/);
  assert.match(page, /downloadPlainText/);
  assert.match(page, /download\/md/);
  assert.match(page, /download\/json/);
  assert.match(page, /download\/zip\/package/);
  assert.match(page, /排版预览/);
  assert.match(page, /原始文本/);
  assert.match(page, /SAFE_RESULT_TAGS/);
  assert.match(page, /复制纯文本/);
  assert.match(page, /pagehide/);
  assert.match(page, /sendBeacon/);
  assert.match(page, /自动释放/);
  assert.match(page, /重复保护/);
  assert.match(page, /已自动停止并清理重复输出/);
  assert.match(page, /openDocumentReader/);
  assert.match(page, /reader\/prepare/);
  assert.match(page, /\/api\/model\/unload/);
  assert.match(page, /<DocumentReader/);
  assert.match(page, /inputRef\.current\?\.click\(\)/);
  assert.match(page, /type="file"/);
  assert.match(page, /onChange=\{selected\}/);
  assert.match(page, /\bmultiple\b/);

  assert.match(reader, /搜索整份文档/);
  assert.match(reader, /reader-state/);
  assert.match(reader, /reading_text/);
  assert.match(reader, /清洁文字/);
  assert.match(reader, /表格 TSV/);
  assert.match(reader, /Markdown 表格/);
  assert.match(reader, /笔记会和这份任务一起保存在本机/);
  assert.match(reader, /requestFullscreen/);
  assert.match(reader, /saveReaderStateNow/);
  assert.match(reader, /keepalive: true/);
  assert.match(reader, /moxi-reader-sidebar-close/);
  assert.match(reader, /sidebarSearchInputRef/);
  assert.match(reader, /searchIndex/);
  assert.match(reader, /moxi-reader-workspace moxi-reader-view-/);
  assert.doesNotMatch(reader, /127\.0\.0\.1:4173/);

  assert.match(backend, /@app\.post\("\/api\/jobs"/);
  assert.match(backend, /@app\.get\("\/api\/health"/);
  assert.match(backend, /@app\.post\("\/api\/model\/load"/);
  assert.match(backend, /@app\.post\("\/api\/client\/disconnect"/);
  assert.match(backend, /_unload_model_if_idle\("任务队列已全部完成"\)/);
  assert.match(backend, /repetition_trimmed/);
  assert.match(backend, /@app\.post\("\/api\/jobs\/\{job_id\}\/reader\/prepare"/);
  assert.match(backend, /@app\.get\("\/api\/jobs\/\{job_id\}\/reader-state"/);
  assert.match(backend, /@app\.put\("\/api\/jobs\/\{job_id\}\/reader-state"/);
  assert.match(backend, /reading_text/);
  assert.match(backend, /reading_repair/);
  assert.match(startCommand, /--host 127\.0\.0\.1 --port 18765/);
  assert.match(startCommand, /PORT=3000 npm run start/);
  assert.match(stopCommand, /backend\.pid/);
  assert.match(stopCommand, /frontend\.pid/);
  assert.match(macApp, /WKUIDelegate/);
  assert.match(macApp, /WKDownloadDelegate/);
  assert.match(macApp, /webView\.uiDelegate = self/);
  assert.match(macApp, /runOpenPanelWith parameters: WKOpenPanelParameters/);
  assert.match(macApp, /let panel = NSOpenPanel\(\)/);
  assert.match(
    macApp,
    /panel\.allowsMultipleSelection = parameters\.allowsMultipleSelection/,
  );
  assert.match(macApp, /completionHandler\(response == \.OK \? panel\.urls : nil\)/);
  assert.match(macApp, /navigationAction\.shouldPerformDownload \? \.download : \.allow/);
  assert.match(macApp, /Content-Disposition/);
  assert.match(macApp, /isAttachment \|\| !navigationResponse\.canShowMIMEType/);
  assert.match(macApp, /download\.delegate = self/);
  assert.match(macApp, /let panel = NSSavePanel\(\)/);
  assert.match(macApp, /panel\.nameFieldStringValue = suggestedFilename/);
  assert.match(macApp, /completionHandler\(destination\)/);
  assert.match(macApp, /isExpectedNavigationCancellation\(error\)/);
  assert.match(macApp, /nsError\.domain == "WebKitErrorDomain" && nsError\.code == 102/);
  assert.match(macApp, /panel\.isExtensionHidden = false/);

  for (const name of [
    "启动 OCR 工作台.command",
    "停止 OCR 工作台.command",
    "安装或修复 OCR 工作台.command",
  ]) {
    const info = await stat(new URL(`../${encodeURIComponent(name)}`, import.meta.url));
    assert.ok(info.isFile(), `${name} should exist`);
    if (process.platform !== "win32") {
      assert.notEqual(info.mode & 0o111, 0, `${name} should be executable`);
    }
  }
});
