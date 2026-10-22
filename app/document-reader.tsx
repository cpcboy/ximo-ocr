"use client";

import {
  ArrowLeft,
  ArrowRight,
  Bookmark,
  BookOpen,
  Check,
  Columns2,
  Copy,
  Expand,
  FileText,
  Image as ImageIcon,
  List,
  Minus,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Printer,
  RotateCw,
  Search,
  Settings2,
  StickyNote,
  X,
} from "lucide-react";
import {
  type CSSProperties,
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

export type DocumentReaderPage = {
  index: number;
  label: string;
  source_name?: string;
  image_file: string | null;
  status: string;
  text: string;
  reading_text?: string;
  reading_repair?: {
    removed_chars?: number;
    duplicate_ratio?: number;
    source_chars?: number;
    reading_chars?: number;
  } | null;
  repetition_trimmed?: boolean;
  edited?: boolean;
  error?: string | null;
};

export type DocumentReaderState = {
  last_page: number;
  bookmarks: number[];
  notes: Record<string, string>;
  view_mode: "split" | "scan" | "text";
  theme: "light" | "dark" | "sepia" | "system";
  font_size: number;
  line_height: number;
  split_percent: number;
  spread: boolean;
  show_raw: boolean;
  zoom: number;
  rotation: 0 | 90 | 180 | 270;
  sidebar_tab: "pages" | "search" | "bookmarks" | "notes";
};

export type DocumentReaderJob = {
  id: string;
  filename: string;
  pages: DocumentReaderPage[];
  reader_state?: Partial<DocumentReaderState> | null;
};

type NotifyKind = "success" | "error" | "info";

type DocumentReaderProps = {
  job: DocumentReaderJob;
  initialPage: number;
  apiBase: string;
  renderResult: (value: string) => ReactNode;
  plainText: (value: string) => string;
  onClose: () => void;
  onEditPage: (index: number) => void;
  onNotify: (message: string, kind?: NotifyKind) => void;
};

type SearchResult = {
  page: number;
  count: number;
  snippet: string;
};

const defaultReaderState: DocumentReaderState = {
  last_page: 0,
  bookmarks: [],
  notes: {},
  view_mode: "split",
  theme: "system",
  font_size: 16,
  line_height: 1.7,
  split_percent: 50,
  spread: false,
  show_raw: false,
  zoom: 100,
  rotation: 0,
  sidebar_tab: "pages",
};

function clamp(value: number, minimum: number, maximum: number) {
  return Math.min(Math.max(value, minimum), maximum);
}

function readingValue(page: DocumentReaderPage) {
  return page.reading_text ?? page.text ?? "";
}

function pageTitle(page: DocumentReaderPage, text: string) {
  const firstLine = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .find(Boolean);
  if (!firstLine) return `第 ${page.index + 1} 页`;
  return firstLine.length > 62 ? `${firstLine.slice(0, 62)}…` : firstLine;
}

function searchSnippet(text: string, query: string) {
  const clean = text.replace(/\s+/g, " ").trim();
  const position = clean.toLocaleLowerCase().indexOf(query.toLocaleLowerCase());
  if (position < 0) return clean.slice(0, 120);
  const start = Math.max(0, position - 42);
  const end = Math.min(clean.length, position + query.length + 72);
  return `${start ? "…" : ""}${clean.slice(start, end)}${
    end < clean.length ? "…" : ""
  }`;
}

function countMatches(text: string, query: string) {
  const haystack = text.toLocaleLowerCase();
  const needle = query.toLocaleLowerCase();
  let count = 0;
  let cursor = 0;
  while (count < 1000) {
    const match = haystack.indexOf(needle, cursor);
    if (match < 0) break;
    count += 1;
    cursor = match + Math.max(needle.length, 1);
  }
  return count;
}

function resultTables(value: string) {
  if (typeof DOMParser === "undefined") return [] as string[][][];
  const parsed = new DOMParser().parseFromString(value, "text/html");
  return Array.from(parsed.querySelectorAll("table")).map((table) =>
    Array.from(table.querySelectorAll("tr")).map((row) =>
      Array.from(row.querySelectorAll("th,td")).map((cell) =>
        (cell.textContent || "").replace(/\s+/g, " ").trim(),
      ),
    ),
  );
}

function tablesAsTsv(value: string, fallback: string) {
  const tables = resultTables(value);
  if (!tables.length) return fallback;
  return tables
    .map((table) => table.map((row) => row.join("\t")).join("\n"))
    .join("\n\n");
}

function escapeMarkdownCell(value: string) {
  return value.replace(/\|/g, "\\|").replace(/\r?\n/g, " ");
}

function tablesAsMarkdown(value: string, fallback: string) {
  const tables = resultTables(value);
  if (!tables.length) return fallback;
  return tables
    .map((table) => {
      const width = Math.max(1, ...table.map((row) => row.length));
      const normalized = table.map((row) =>
        Array.from({ length: width }, (_, index) =>
          escapeMarkdownCell(row[index] || ""),
        ),
      );
      const header = normalized[0] || Array(width).fill("");
      const body = normalized.slice(1);
      return [
        `| ${header.join(" | ")} |`,
        `| ${Array(width).fill("---").join(" | ")} |`,
        ...body.map((row) => `| ${row.join(" | ")} |`),
      ].join("\n");
    })
    .join("\n\n");
}

function Highlight({
  text,
  query,
}: {
  text: string;
  query: string;
}) {
  const needle = query.trim();
  if (!needle) return text;
  const escaped = needle.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const pieces = text.split(new RegExp(`(${escaped})`, "gi"));
  return pieces.map((piece, index) =>
    piece.toLocaleLowerCase() === needle.toLocaleLowerCase() ? (
      <mark key={`${piece}-${index}`}>{piece}</mark>
    ) : (
      <span key={`${piece}-${index}`}>{piece}</span>
    ),
  );
}

export function DocumentReader({
  job,
  initialPage,
  apiBase,
  renderResult,
  plainText,
  onClose,
  onEditPage,
  onNotify,
}: DocumentReaderProps) {
  const pageCount = job.pages.length;
  const hasStoredReaderState = Boolean(
    job.reader_state &&
      Object.prototype.hasOwnProperty.call(job.reader_state, "last_page"),
  );
  const initialState = {
    ...defaultReaderState,
    ...(job.reader_state || {}),
  };
  const [currentPage, setCurrentPage] = useState(() =>
    clamp(
      hasStoredReaderState ? initialState.last_page : initialPage || 0,
      0,
      Math.max(0, pageCount - 1),
    ),
  );
  const [bookmarks, setBookmarks] = useState<number[]>(
    initialState.bookmarks || [],
  );
  const [notes, setNotes] = useState<Record<string, string>>(
    initialState.notes || {},
  );
  const [viewMode, setViewMode] = useState<DocumentReaderState["view_mode"]>(
    initialState.view_mode,
  );
  const [theme, setTheme] = useState<DocumentReaderState["theme"]>(
    initialState.theme,
  );
  const [fontSize, setFontSize] = useState(initialState.font_size);
  const [lineHeight, setLineHeight] = useState(initialState.line_height);
  const [splitPercent, setSplitPercent] = useState(initialState.split_percent);
  const [spread, setSpread] = useState(initialState.spread);
  const [showRaw, setShowRaw] = useState(initialState.show_raw);
  const [zoom, setZoom] = useState(initialState.zoom);
  const [rotation, setRotation] =
    useState<DocumentReaderState["rotation"]>(initialState.rotation);
  const [sidebarTab, setSidebarTab] =
    useState<DocumentReaderState["sidebar_tab"]>(initialState.sidebar_tab);
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [pageInput, setPageInput] = useState(String(currentPage + 1));
  const [sidebarOpen, setSidebarOpen] = useState(
    () =>
      typeof window === "undefined" ||
      !window.matchMedia("(max-width: 820px)").matches,
  );
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [copyMenuOpen, setCopyMenuOpen] = useState(false);
  const [stateReady, setStateReady] = useState(false);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "error">(
    "idle",
  );
  const [syncScroll, setSyncScroll] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const sidebarSearchInputRef = useRef<HTMLInputElement>(null);
  const scanScrollRef = useRef<HTMLDivElement>(null);
  const textScrollRef = useRef<HTMLDivElement>(null);
  const copyMenuRef = useRef<HTMLDivElement>(null);
  const syncingScroll = useRef(false);

  const current = job.pages[currentPage];
  const nextPage = spread ? job.pages[currentPage + 1] : null;
  const cleanValue = current ? readingValue(current) : "";
  const cleanPlainText = useMemo(
    () => plainText(cleanValue),
    [cleanValue, plainText],
  );

  const searchIndex = useMemo(
    () =>
      job.pages.map((page) => {
        const text = plainText(readingValue(page));
        return {
          page: page.index,
          text,
          title: pageTitle(page, text),
        };
      }),
    [job.pages, plainText],
  );

  const outline = useMemo(
    () =>
      searchIndex.map(({ page, title }) => ({
        page,
        title,
      })),
    [searchIndex],
  );

  useEffect(() => {
    const timer = window.setTimeout(
      () => setDebouncedQuery(query),
      query ? 180 : 0,
    );
    return () => window.clearTimeout(timer);
  }, [query]);

  const searchResults = useMemo<SearchResult[]>(() => {
    const needle = debouncedQuery.trim();
    if (!needle) return [];
    return searchIndex.flatMap(({ page, text }) => {
      const count = countMatches(text, needle);
      return count
        ? [
            {
              page,
              count,
              snippet: searchSnippet(text, needle),
            },
          ]
        : [];
    });
  }, [debouncedQuery, searchIndex]);

  const searchMatchCount = useMemo(
    () => searchResults.reduce((total, result) => total + result.count, 0),
    [searchResults],
  );
  const searchPending = query.trim() !== debouncedQuery.trim();

  const savedState = useMemo<DocumentReaderState>(
    () => ({
      last_page: currentPage,
      bookmarks,
      notes,
      view_mode: viewMode,
      theme,
      font_size: fontSize,
      line_height: lineHeight,
      split_percent: splitPercent,
      spread,
      show_raw: showRaw,
      zoom,
      rotation,
      sidebar_tab: sidebarTab,
    }),
    [
      bookmarks,
      currentPage,
      fontSize,
      lineHeight,
      notes,
      rotation,
      showRaw,
      sidebarTab,
      splitPercent,
      spread,
      theme,
      viewMode,
      zoom,
    ],
  );
  const latestStateRef = useRef(savedState);

  useEffect(() => {
    latestStateRef.current = savedState;
  }, [savedState]);

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      try {
        const response = await fetch(
          `${apiBase}/api/jobs/${job.id}/reader-state`,
          { signal: controller.signal },
        );
        if (!response.ok) throw new Error(`读取阅读进度失败（${response.status}）`);
        const state = (await response.json()) as DocumentReaderState;
        setBookmarks(state.bookmarks);
        setNotes(state.notes);
        setViewMode(state.view_mode);
        setTheme(state.theme);
        setFontSize(state.font_size);
        setLineHeight(state.line_height);
        setSplitPercent(state.split_percent);
        setSpread(state.spread);
        setShowRaw(state.show_raw);
        setZoom(state.zoom);
        setRotation(state.rotation);
        setSidebarTab(state.sidebar_tab);
        const resumePage = clamp(
          hasStoredReaderState ? state.last_page : initialPage || 0,
          0,
          Math.max(0, pageCount - 1),
        );
        setCurrentPage(resumePage);
        setPageInput(String(resumePage + 1));
        setStateReady(true);
      } catch (error) {
        if ((error as Error).name !== "AbortError") {
          setStateReady(true);
          onNotify((error as Error).message, "error");
        }
      }
    }, 0);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [
    apiBase,
    hasStoredReaderState,
    initialPage,
    job.id,
    onNotify,
    pageCount,
  ]);

  useEffect(() => {
    if (!stateReady) return;
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setSaveState("saving");
      try {
        const response = await fetch(
          `${apiBase}/api/jobs/${job.id}/reader-state`,
          {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(savedState),
            signal: controller.signal,
          },
        );
        if (!response.ok) throw new Error(`保存阅读进度失败（${response.status}）`);
        setSaveState("saved");
      } catch (error) {
        if ((error as Error).name !== "AbortError") {
          setSaveState("error");
        }
      }
    }, 600);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [apiBase, job.id, savedState, stateReady]);

  const saveReaderStateNow = useCallback(async () => {
    if (!stateReady) return;
    setSaveState("saving");
    try {
      const response = await fetch(
        `${apiBase}/api/jobs/${job.id}/reader-state`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(latestStateRef.current),
        },
      );
      if (!response.ok) throw new Error(`保存阅读进度失败（${response.status}）`);
      setSaveState("saved");
    } catch (error) {
      setSaveState("error");
      onNotify((error as Error).message, "error");
    }
  }, [apiBase, job.id, onNotify, stateReady]);

  useEffect(() => {
    if (!stateReady) return;
    const saveBeforePageExit = () => {
      void fetch(`${apiBase}/api/jobs/${job.id}/reader-state`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(latestStateRef.current),
        keepalive: true,
      }).catch(() => undefined);
    };
    window.addEventListener("pagehide", saveBeforePageExit);
    return () => window.removeEventListener("pagehide", saveBeforePageExit);
  }, [apiBase, job.id, stateReady]);

  const closeReader = useCallback(async () => {
    await saveReaderStateNow();
    onClose();
  }, [onClose, saveReaderStateNow]);

  const editCurrentPage = useCallback(async () => {
    await saveReaderStateNow();
    onEditPage(currentPage);
  }, [currentPage, onEditPage, saveReaderStateNow]);

  const goToPage = useCallback(
    (page: number) => {
      const next = clamp(page, 0, Math.max(0, pageCount - 1));
      setCurrentPage(next);
      setPageInput(String(next + 1));
      window.requestAnimationFrame(() => {
        scanScrollRef.current?.scrollTo({ top: 0 });
        textScrollRef.current?.scrollTo({ top: 0 });
      });
      if (window.matchMedia("(max-width: 820px)").matches) {
        setSidebarOpen(false);
      }
    },
    [pageCount],
  );

  const toggleBookmark = useCallback(() => {
    setBookmarks((items) =>
      items.includes(currentPage)
        ? items.filter((item) => item !== currentPage)
        : [...items, currentPage].sort((a, b) => a - b),
    );
  }, [currentPage]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (!stateReady) return;
      const tag = (event.target as HTMLElement | null)?.tagName;
      const typing = tag === "INPUT" || tag === "TEXTAREA";
      if (!typing && event.key === "/") {
        event.preventDefault();
        setSidebarOpen(true);
        setSidebarTab("search");
        window.requestAnimationFrame(() => {
          const compact = window.matchMedia("(max-width: 820px)").matches;
          (compact ? sidebarSearchInputRef : searchInputRef).current?.focus();
        });
      } else if (!typing && ["ArrowLeft", "PageUp"].includes(event.key)) {
        event.preventDefault();
        goToPage(currentPage - (spread ? 2 : 1));
      } else if (!typing && ["ArrowRight", "PageDown"].includes(event.key)) {
        event.preventDefault();
        goToPage(currentPage + (spread ? 2 : 1));
      } else if (!typing && event.key.toLocaleLowerCase() === "b") {
        event.preventDefault();
        toggleBookmark();
      } else if (event.key === "Escape") {
        setSettingsOpen(false);
        setCopyMenuOpen(false);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [currentPage, goToPage, spread, stateReady, toggleBookmark]);

  useEffect(() => {
    if (!copyMenuOpen) return;
    const closeCopyMenu = (event: PointerEvent) => {
      if (!copyMenuRef.current?.contains(event.target as Node)) {
        setCopyMenuOpen(false);
      }
    };
    document.addEventListener("pointerdown", closeCopyMenu, true);
    return () => document.removeEventListener("pointerdown", closeCopyMenu, true);
  }, [copyMenuOpen]);

  const copy = async (value: string, label: string) => {
    try {
      await navigator.clipboard.writeText(value);
      onNotify(`${label}已复制`, "success");
      setCopyMenuOpen(false);
    } catch {
      onNotify("复制失败，请手动选择文字", "error");
    }
  };

  const syncPanelScroll = (
    source: HTMLDivElement,
    target: HTMLDivElement | null,
  ) => {
    if (!syncScroll || !target || syncingScroll.current) return;
    const sourceRange = source.scrollHeight - source.clientHeight;
    const targetRange = target.scrollHeight - target.clientHeight;
    if (sourceRange <= 0 || targetRange <= 0) return;
    syncingScroll.current = true;
    target.scrollTop = (source.scrollTop / sourceRange) * targetRange;
    window.requestAnimationFrame(() => {
      syncingScroll.current = false;
    });
  };

  const commitPageInput = () => {
    const number = Number.parseInt(pageInput, 10);
    if (Number.isFinite(number)) goToPage(number - 1);
    else setPageInput(String(currentPage + 1));
  };

  const rotate = () =>
    setRotation((value) => ((value + 90) % 360) as 0 | 90 | 180 | 270);

  const pageNote = notes[String(currentPage)] || "";
  const progress = pageCount ? ((currentPage + 1) / pageCount) * 100 : 0;
  const readerTheme =
    theme === "system"
      ? "system"
      : theme;

  if (!stateReady) {
    return (
      <div className="moxi-reader-loading" role="status" aria-live="polite">
        <BookOpen size={34} />
        <strong>正在恢复阅读进度…</strong>
      </div>
    );
  }

  if (!current) {
    return (
      <div className="moxi-reader-empty">
        <BookOpen size={36} />
        <strong>这份任务还没有可以阅读的页面</strong>
        <button onClick={() => void closeReader()}>返回工作台</button>
      </div>
    );
  }

  return (
    <div
      className={`moxi-reader moxi-reader-theme-${readerTheme} ${
        sidebarOpen ? "" : "moxi-reader-sidebar-collapsed"
      }`}
      style={
        {
          "--moxi-reader-font-size": `${fontSize}px`,
          "--moxi-reader-line-height": lineHeight,
          "--moxi-reader-split": `${splitPercent}%`,
        } as CSSProperties
      }
    >
      <header className="moxi-reader-header">
        <div className="moxi-reader-title">
          <button onClick={() => void closeReader()} aria-label="返回校对工作台">
            <ArrowLeft size={18} />
          </button>
          <span className="moxi-reader-title-icon">
            <BookOpen size={18} />
          </span>
          <div>
            <strong title={job.filename}>{job.filename}</strong>
            <span>
              第 {currentPage + 1} / {pageCount} 页
              {saveState === "saving"
                ? " · 正在保存进度"
                : saveState === "saved"
                  ? " · 进度已保存"
                  : saveState === "error"
                    ? " · 进度保存失败"
                    : ""}
            </span>
          </div>
        </div>

        <div className="moxi-reader-header-search">
          <Search size={15} />
          <input
            ref={searchInputRef}
            value={query}
            onFocus={() => {
              setSidebarOpen(true);
              setSidebarTab("search");
            }}
            onChange={(event) => {
              setQuery(event.target.value);
              setSidebarTab("search");
            }}
            placeholder="搜索整份文档，按 /"
            aria-label="搜索整份文档"
          />
          {query ? (
            <span>{searchPending ? "搜索中…" : `${searchMatchCount} 项`}</span>
          ) : (
            <kbd>/</kbd>
          )}
        </div>

        <div className="moxi-reader-header-actions">
          <button
            className={bookmarks.includes(currentPage) ? "active" : ""}
            onClick={toggleBookmark}
            aria-pressed={bookmarks.includes(currentPage)}
            title="收藏当前页（B）"
          >
            <Bookmark
              size={17}
              fill={bookmarks.includes(currentPage) ? "currentColor" : "none"}
            />
          </button>
          <button
            onClick={() => document.documentElement.requestFullscreen?.()}
            title="全屏阅读"
          >
            <Expand size={17} />
          </button>
          <button onClick={() => window.print()} title="打印当前阅读页">
            <Printer size={17} />
          </button>
          <button
            className={settingsOpen ? "active" : ""}
            onClick={() => setSettingsOpen((open) => !open)}
            title="阅读设置"
          >
            <Settings2 size={17} />
          </button>
        </div>
      </header>

      <div className="moxi-reader-progress" aria-hidden="true">
        <span style={{ width: `${progress}%` }} />
      </div>

      <div className="moxi-reader-body">
        {sidebarOpen ? (
          <button
            className="moxi-reader-sidebar-backdrop"
            onClick={() => setSidebarOpen(false)}
            aria-label="关闭页面导航"
          />
        ) : null}
        <aside
          className="moxi-reader-sidebar"
          id="moxi-reader-sidebar"
          aria-label="文档导航"
        >
          <button
            className="moxi-reader-sidebar-close"
            onClick={() => setSidebarOpen(false)}
            aria-label="关闭页面导航"
          >
            <X size={16} />
          </button>
          <div className="moxi-reader-sidebar-tabs" role="tablist">
            <button
              className={sidebarTab === "pages" ? "active" : ""}
              onClick={() => setSidebarTab("pages")}
              title="页面"
              role="tab"
              aria-selected={sidebarTab === "pages"}
            >
              <List size={15} /> 页面
            </button>
            <button
              className={sidebarTab === "search" ? "active" : ""}
              onClick={() => {
                setSidebarTab("search");
                window.requestAnimationFrame(() =>
                  sidebarSearchInputRef.current?.focus(),
                );
              }}
              title="搜索"
              role="tab"
              aria-selected={sidebarTab === "search"}
            >
              <Search size={15} /> 搜索
            </button>
            <button
              className={sidebarTab === "bookmarks" ? "active" : ""}
              onClick={() => setSidebarTab("bookmarks")}
              title="书签"
              role="tab"
              aria-selected={sidebarTab === "bookmarks"}
            >
              <Bookmark size={15} /> 书签
            </button>
            <button
              className={sidebarTab === "notes" ? "active" : ""}
              onClick={() => setSidebarTab("notes")}
              title="笔记"
              role="tab"
              aria-selected={sidebarTab === "notes"}
            >
              <StickyNote size={15} /> 笔记
            </button>
          </div>

          {sidebarTab === "search" ? (
            <div className="moxi-reader-search-results">
              <label className="moxi-reader-sidebar-searchbox">
                <Search size={15} />
                <input
                  ref={sidebarSearchInputRef}
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder={`搜索全部 ${pageCount} 页`}
                  aria-label="搜索整份文档"
                />
                {query ? (
                  <button
                    onClick={() => setQuery("")}
                    aria-label="清除搜索文字"
                    type="button"
                  >
                    <X size={14} />
                  </button>
                ) : null}
              </label>
              <div className="moxi-reader-sidebar-heading">
                <strong>全文搜索</strong>
                <span>
                  {searchPending ? "搜索中…" : `${searchMatchCount} 个匹配`}
                </span>
              </div>
              {!query.trim() ? (
                <div className="moxi-reader-sidebar-empty">
                  <Search size={24} />
                  <span>输入文字搜索全部 {pageCount} 页</span>
                </div>
              ) : searchPending ? (
                <div className="moxi-reader-sidebar-empty">
                  <Search size={24} />
                  <span>正在搜索全部页面…</span>
                </div>
              ) : searchResults.length ? (
                searchResults.map((result) => (
                  <button
                    key={result.page}
                    className={result.page === currentPage ? "active" : ""}
                    onClick={() => goToPage(result.page)}
                  >
                    <span>
                      第 {result.page + 1} 页
                      <b>{result.count} 项</b>
                    </span>
                    <p>
                      <Highlight text={result.snippet} query={debouncedQuery} />
                    </p>
                  </button>
                ))
              ) : (
                <div className="moxi-reader-sidebar-empty">
                  <Search size={24} />
                  <span>没有找到“{debouncedQuery}”</span>
                </div>
              )}
            </div>
          ) : sidebarTab === "bookmarks" ? (
            <div className="moxi-reader-page-list">
              <div className="moxi-reader-sidebar-heading">
                <strong>我的书签</strong>
                <span>{bookmarks.length} 页</span>
              </div>
              {bookmarks.length ? (
                bookmarks.map((index) => (
                  <button
                    key={index}
                    className={index === currentPage ? "active" : ""}
                    onClick={() => goToPage(index)}
                  >
                    <span className="moxi-reader-page-number">{index + 1}</span>
                    <span>
                      <strong>{outline[index]?.title}</strong>
                      <small>第 {index + 1} 页</small>
                    </span>
                    <Bookmark size={13} fill="currentColor" />
                  </button>
                ))
              ) : (
                <div className="moxi-reader-sidebar-empty">
                  <Bookmark size={24} />
                  <span>按 B 收藏当前页</span>
                </div>
              )}
            </div>
          ) : sidebarTab === "notes" ? (
            <div className="moxi-reader-notes">
              <div className="moxi-reader-sidebar-heading">
                <strong>第 {currentPage + 1} 页笔记</strong>
                <span>{pageNote.length} 字</span>
              </div>
              <textarea
                value={pageNote}
                onChange={(event) =>
                  setNotes((items) => ({
                    ...items,
                    [String(currentPage)]: event.target.value,
                  }))
                }
                placeholder="记录摘要、疑问或校对提示。笔记会和这份任务一起保存在本机。"
              />
              <p>切换页面前会自动保存，无需手动操作。</p>
              {Object.keys(notes).filter((key) => notes[key]).length ? (
                <div className="moxi-reader-note-pages">
                  {Object.entries(notes)
                    .filter(([, note]) => note)
                    .map(([page, note]) => (
                      <button key={page} onClick={() => goToPage(Number(page))}>
                        <b>第 {Number(page) + 1} 页</b>
                        <span>{note.slice(0, 54)}</span>
                      </button>
                    ))}
                </div>
              ) : null}
            </div>
          ) : (
            <div className="moxi-reader-page-list">
              <div className="moxi-reader-sidebar-heading">
                <strong>页面导航</strong>
                <span>{pageCount} 页</span>
              </div>
              {job.pages.map((page, index) => (
                <button
                  key={page.index}
                  className={index === currentPage ? "active" : ""}
                  onClick={() => goToPage(index)}
                  title={page.label}
                >
                  <span className="moxi-reader-page-number">{index + 1}</span>
                  <span>
                    <strong>{outline[index]?.title}</strong>
                    <small>
                      {page.reading_text
                        ? "阅读版已清理"
                        : page.edited
                          ? "已校对"
                          : page.status === "completed"
                            ? "识别完成"
                            : page.status}
                    </small>
                  </span>
                  {bookmarks.includes(index) ? (
                    <Bookmark size={12} fill="currentColor" />
                  ) : page.reading_text ? (
                    <Check size={12} />
                  ) : null}
                </button>
              ))}
            </div>
          )}
        </aside>

        <main className="moxi-reader-main">
          <div className="moxi-reader-toolbar">
            <button
              className="moxi-reader-sidebar-toggle"
              onClick={() => setSidebarOpen((open) => !open)}
              aria-expanded={sidebarOpen}
              aria-controls="moxi-reader-sidebar"
              title={sidebarOpen ? "收起侧栏" : "展开侧栏"}
            >
              {sidebarOpen ? (
                <PanelLeftClose size={16} />
              ) : (
                <PanelLeftOpen size={16} />
              )}
            </button>

            <div className="moxi-reader-view-tabs" aria-label="阅读布局">
              <button
                className={viewMode === "split" ? "active" : ""}
                onClick={() => setViewMode("split")}
                aria-pressed={viewMode === "split"}
              >
                <Columns2 size={14} /> 对照
              </button>
              <button
                className={viewMode === "scan" ? "active" : ""}
                onClick={() => setViewMode("scan")}
                aria-pressed={viewMode === "scan"}
              >
                <ImageIcon size={14} /> 原页
              </button>
              <button
                className={viewMode === "text" ? "active" : ""}
                onClick={() => setViewMode("text")}
                aria-pressed={viewMode === "text"}
              >
                <FileText size={14} /> 文字
              </button>
            </div>

            <div className="moxi-reader-page-jump">
              <button
                onClick={() => goToPage(currentPage - (spread ? 2 : 1))}
                disabled={currentPage === 0}
                aria-label="上一页"
              >
                <ArrowLeft size={15} />
              </button>
              <label>
                <input
                  value={pageInput}
                  onChange={(event) => setPageInput(event.target.value)}
                  onBlur={commitPageInput}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") commitPageInput();
                  }}
                  aria-label="页码"
                />
                <span>/ {pageCount}</span>
              </label>
              <button
                onClick={() => goToPage(currentPage + (spread ? 2 : 1))}
                disabled={currentPage >= pageCount - 1}
                aria-label="下一页"
              >
                <ArrowRight size={15} />
              </button>
            </div>

            <div className="moxi-reader-tools">
              {viewMode !== "text" ? (
                <>
                  <button
                    onClick={() => setZoom((value) => clamp(value - 10, 50, 300))}
                    aria-label="缩小"
                  >
                    <Minus size={14} />
                  </button>
                  <button className="moxi-reader-zoom-value" onClick={() => setZoom(100)}>
                    {zoom}%
                  </button>
                  <button
                    onClick={() => setZoom((value) => clamp(value + 10, 50, 300))}
                    aria-label="放大"
                  >
                    <Plus size={14} />
                  </button>
                  <button onClick={rotate} title="顺时针旋转">
                    <RotateCw size={15} />
                  </button>
                  <button
                    className={spread ? "active" : ""}
                    onClick={() => setSpread((value) => !value)}
                    aria-pressed={spread}
                    title="双页显示"
                  >
                    <BookOpen size={15} />
                  </button>
                </>
              ) : null}
              {viewMode === "split" ? (
                <button
                  className={syncScroll ? "active" : ""}
                  onClick={() => setSyncScroll((value) => !value)}
                  aria-pressed={syncScroll}
                  title="同步滚动"
                >
                  同步
                </button>
              ) : null}
              <div className="moxi-reader-copy-menu" ref={copyMenuRef}>
                <button
                  onClick={() => setCopyMenuOpen((open) => !open)}
                  aria-expanded={copyMenuOpen}
                  aria-haspopup="menu"
                >
                  <Copy size={14} /> 复制
                </button>
                {copyMenuOpen ? (
                  <div role="menu">
                    <button
                      role="menuitem"
                      onClick={() => copy(cleanPlainText, "清洁文字")}
                    >
                      清洁文字
                    </button>
                    <button
                      role="menuitem"
                      onClick={() => copy(current.text || "", "原始 OCR")}
                    >
                      原始 OCR
                    </button>
                    <button
                      role="menuitem"
                      onClick={() =>
                        copy(tablesAsTsv(cleanValue, cleanPlainText), "表格 TSV")
                      }
                    >
                      表格 TSV
                    </button>
                    <button
                      role="menuitem"
                      onClick={() =>
                        copy(
                          tablesAsMarkdown(cleanValue, cleanPlainText),
                          "Markdown 表格",
                        )
                      }
                    >
                      Markdown 表格
                    </button>
                  </div>
                ) : null}
              </div>
              <button onClick={() => void editCurrentPage()}>校对本页</button>
            </div>
          </div>

          {settingsOpen ? (
            <section className="moxi-reader-settings" aria-label="阅读设置">
              <div>
                <span>主题</span>
                <div>
                  {(["system", "light", "sepia", "dark"] as const).map((value) => (
                    <button
                      key={value}
                      className={theme === value ? "active" : ""}
                      onClick={() => setTheme(value)}
                    >
                      {value === "system"
                        ? "跟随系统"
                        : value === "light"
                          ? "明亮"
                          : value === "sepia"
                            ? "护眼"
                            : "深色"}
                    </button>
                  ))}
                </div>
              </div>
              <label>
                <span>字号 {fontSize}px</span>
                <input
                  type="range"
                  min="12"
                  max="32"
                  value={fontSize}
                  onChange={(event) => setFontSize(Number(event.target.value))}
                />
              </label>
              <label>
                <span>行距 {lineHeight.toFixed(1)}</span>
                <input
                  type="range"
                  min="1.2"
                  max="2.6"
                  step="0.1"
                  value={lineHeight}
                  onChange={(event) => setLineHeight(Number(event.target.value))}
                />
              </label>
              {viewMode === "split" ? (
                <label>
                  <span>原页宽度 {splitPercent}%</span>
                  <input
                    type="range"
                    min="25"
                    max="75"
                    value={splitPercent}
                    onChange={(event) => setSplitPercent(Number(event.target.value))}
                  />
                </label>
              ) : null}
              <button
                className="moxi-reader-settings-close"
                onClick={() => setSettingsOpen(false)}
                aria-label="关闭阅读设置"
              >
                <X size={16} />
              </button>
            </section>
          ) : null}

          <div className={`moxi-reader-workspace moxi-reader-view-${viewMode}`}>
            {viewMode !== "text" ? (
              <section className="moxi-reader-scan-pane">
                <div className="moxi-reader-pane-heading">
                  <span>
                    <ImageIcon size={14} /> 扫描原页
                  </span>
                  <small>
                    {spread && nextPage
                      ? `${currentPage + 1}–${currentPage + 2} 页`
                      : `第 ${currentPage + 1} 页`}
                  </small>
                </div>
                <div
                  ref={scanScrollRef}
                  className={`moxi-reader-scan-scroll ${
                    spread ? "moxi-reader-spread" : ""
                  }`}
                  onScroll={(event) =>
                    syncPanelScroll(event.currentTarget, textScrollRef.current)
                  }
                  onWheel={(event) => {
                    if (event.metaKey || event.ctrlKey) {
                      event.preventDefault();
                      setZoom((value) =>
                        clamp(value + (event.deltaY < 0 ? 10 : -10), 50, 300),
                      );
                    }
                  }}
                >
                  {[current, nextPage].filter(Boolean).map((page) =>
                    page?.image_file ? (
                      // Local OCR preview; no remote loader or optimization is needed.
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        key={`${job.id}-${page.index}`}
                        src={`${apiBase}/api/jobs/${job.id}/pages/${page.index}/image`}
                        alt={page.label}
                        style={{
                          width: `${spread ? zoom / 2 : zoom}%`,
                          transform: `rotate(${rotation}deg)`,
                        }}
                      />
                    ) : (
                      <div className="moxi-reader-no-image" key={page?.index}>
                        <FileText size={36} />
                        <strong>这一页没有图像预览</strong>
                      </div>
                    ),
                  )}
                </div>
              </section>
            ) : null}

            {viewMode !== "scan" ? (
              <section className="moxi-reader-text-pane">
                <div className="moxi-reader-pane-heading">
                  <span>
                    <FileText size={14} /> 识别阅读版
                  </span>
                  <div className="moxi-reader-source-tabs">
                    <button
                      className={!showRaw ? "active" : ""}
                      onClick={() => setShowRaw(false)}
                      aria-pressed={!showRaw}
                    >
                      阅读版
                    </button>
                    <button
                      className={showRaw ? "active" : ""}
                      onClick={() => setShowRaw(true)}
                      aria-pressed={showRaw}
                    >
                      原始 OCR
                    </button>
                  </div>
                </div>

                {current.reading_text && !showRaw ? (
                  <div className="moxi-reader-repair-note">
                    <Check size={14} />
                    <span>
                      已清理本页重复输出
                      {current.reading_repair?.removed_chars
                        ? `，保留原文并移除 ${current.reading_repair.removed_chars.toLocaleString()} 个重复字符`
                        : ""}
                    </span>
                  </div>
                ) : null}

                <div
                  ref={textScrollRef}
                  className="moxi-reader-text-scroll"
                  onScroll={(event) =>
                    syncPanelScroll(event.currentTarget, scanScrollRef.current)
                  }
                >
                  <article className="moxi-reader-paper">
                    {showRaw ? (
                      <pre>{current.text || "本页没有 OCR 文字。"}</pre>
                    ) : cleanValue ? (
                      renderResult(cleanValue)
                    ) : (
                      <div className="moxi-reader-no-text">
                        <FileText size={32} />
                        <strong>本页没有识别文字</strong>
                        <span>{current.error || "可以返回校对工作台手动补充。"}</span>
                      </div>
                    )}
                  </article>
                </div>
              </section>
            ) : null}
          </div>

          <footer className="moxi-reader-footer">
            <button
              onClick={() => goToPage(currentPage - (spread ? 2 : 1))}
              disabled={currentPage === 0}
            >
              <ArrowLeft size={16} />
              <span>
                <small>上一页</small>
                <strong>
                  {currentPage > 0 ? `第 ${Math.max(1, currentPage)} 页` : "已经到开头"}
                </strong>
              </span>
            </button>
            <input
              type="range"
              min="0"
              max={Math.max(0, pageCount - 1)}
              value={currentPage}
              onChange={(event) => goToPage(Number(event.target.value))}
              aria-label="阅读进度"
            />
            <button
              className="moxi-reader-next"
              onClick={() => goToPage(currentPage + (spread ? 2 : 1))}
              disabled={currentPage >= pageCount - 1}
            >
              <span>
                <small>下一页</small>
                <strong>
                  {currentPage < pageCount - 1
                    ? `第 ${Math.min(pageCount, currentPage + (spread ? 3 : 2))} 页`
                    : "已经到末尾"}
                </strong>
              </span>
              <ArrowRight size={16} />
            </button>
          </footer>
        </main>
      </div>
    </div>
  );
}
