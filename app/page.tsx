"use client";

import {
  Archive,
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Check,
  ChevronDown,
  CircleAlert,
  Clipboard,
  Code2,
  Copy,
  Download,
  Eye,
  FileArchive,
  FileImage,
  FileSpreadsheet,
  FileText,
  FileType2,
  FolderOpen,
  Gauge,
  HardDrive,
  Image as ImageIcon,
  LoaderCircle,
  Menu,
  Moon,
  PackageOpen,
  Pause,
  Play,
  Plus,
  RefreshCw,
  RotateCcw,
  Save,
  ScanLine,
  Search,
  Server,
  Settings2,
  ShieldCheck,
  Sparkles,
  Square,
  Sun,
  Trash2,
  UploadCloud,
  X,
  Zap,
} from "lucide-react";
import {
  ChangeEvent,
  DragEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  DocumentReader,
  type DocumentReaderState,
} from "./document-reader";

const API_BASE = "http://127.0.0.1:18765";
const ACCEPTED_FILES =
  ".pdf,.png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff,.gif,.heic,.heif,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.odt,.ods,.odp,.txt,.md,.csv,.tsv,.json,.xml,.yaml,.yml,.html,.htm,.log,.rtf,.eml,.zip";

type ModelStatus = {
  path: string;
  exists: boolean;
  weights_found: boolean;
  size_bytes: number;
  size_gb: number;
  loaded: boolean;
  state: "not_loaded" | "loading" | "ready" | "running" | "error";
  message: string;
  busy: boolean;
  last_loaded_at: string | null;
  platform?: "windows";
  framework?: string;
  hardware?: {
    compatible: boolean;
    name: string | null;
    memory_gb: number;
    driver: string | null;
    message: string;
  };
};

type ModelDownloadStatus = {
  available: boolean;
  platform: "mlx" | "windows" | null;
  model_ready: boolean;
  download_path: string;
  using_external_model: boolean;
  model_revision: string;
  model_id: string;
  model_url: string;
  state:
    | "idle"
    | "checking"
    | "installing"
    | "downloading"
    | "verifying"
    | "completed"
    | "error"
    | "canceling"
    | "cancelled";
  message: string;
  progress: number;
  bytes_downloaded: number;
  bytes_total: number;
  runtime_variant: string | null;
  runtime_ready: boolean;
  error: string | null;
  running: boolean;
};

type Health = {
  status: string;
  local_only: boolean;
  model: ModelStatus;
  model_download: ModelDownloadStatus;
  converters: {
    pdf: boolean;
    images: boolean;
    office: boolean;
    office_tool: string | null;
    archives: boolean;
    plain_text: boolean;
  };
  supported_extensions: string[];
  max_upload_bytes: number;
  queue_size: number;
  lifecycle: {
    auto_unload: boolean;
    client_connected: boolean;
    client_timeout_seconds: number;
  };
};

type JobStatus =
  | "uploading"
  | "queued"
  | "preparing"
  | "running"
  | "canceling"
  | "canceled"
  | "completed"
  | "partial"
  | "failed";

type PageRecord = {
  index: number;
  label: string;
  source_name: string;
  image_file: string | null;
  status: JobStatus | "completed" | "failed";
  text: string;
  kind?: "ocr" | "direct";
  error: string | null;
  elapsed_seconds: number;
  edited?: boolean;
  repetition_trimmed?: boolean;
  repetition_diagnostics?: Record<string, unknown> | null;
  reading_text?: string;
  reading_repair?: {
    removed_chars?: number;
    duplicate_ratio?: number;
    source_chars?: number;
    reading_chars?: number;
  } | null;
};

type JobStats = {
  total_pages: number;
  completed_pages: number;
  failed_pages: number;
  elapsed_seconds: number;
};

type JobSummary = {
  id: string;
  filename: string;
  content_type: string;
  size: number;
  status: JobStatus;
  stage: string;
  progress: number;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  error: string | null;
  warnings: string[];
  stats: JobStats;
};

type Job = JobSummary & {
  options: OcrOptions;
  pages: PageRecord[];
  cancel_requested: boolean;
  reader_state?: Partial<DocumentReaderState> | null;
};

type OcrOptions = {
  mode: "precision" | "fast";
  prompt: string;
  page_range: string;
  dpi: number;
  max_length: number;
  language_hint: string;
  output_style: string;
};

type Toast = {
  id: number;
  message: string;
  kind: "success" | "error" | "info";
};

const defaultOptions: OcrOptions = {
  mode: "precision",
  prompt: "document parsing.",
  page_range: "",
  dpi: 160,
  max_length: 8192,
  language_hint: "auto",
  output_style: "structured",
};

const statusMeta: Record<
  JobStatus,
  { label: string; tone: string; active?: boolean }
> = {
  uploading: { label: "上传中", tone: "blue", active: true },
  queued: { label: "等待中", tone: "gray", active: true },
  preparing: { label: "准备页面", tone: "purple", active: true },
  running: { label: "识别中", tone: "blue", active: true },
  canceling: { label: "正在取消", tone: "orange", active: true },
  canceled: { label: "已取消", tone: "gray" },
  completed: { label: "已完成", tone: "green" },
  partial: { label: "部分完成", tone: "orange" },
  failed: { label: "失败", tone: "red" },
};

function formatBytes(value: number) {
  if (!value) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(
    Math.floor(Math.log(value) / Math.log(1024)),
    units.length - 1,
  );
  const number = value / 1024 ** index;
  return `${number >= 10 || index === 0 ? number.toFixed(0) : number.toFixed(1)} ${units[index]}`;
}

function formatDate(value: string | null | undefined) {
  if (!value) return "—";
  const date = new Date(value);
  return new Intl.DateTimeFormat("zh-CN", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function fileIcon(filename: string, size = 18) {
  const extension = filename.split(".").pop()?.toLowerCase();
  if (["png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff", "gif", "heic"].includes(extension || "")) {
    return <FileImage size={size} />;
  }
  if (["xls", "xlsx", "csv", "tsv", "ods"].includes(extension || "")) {
    return <FileSpreadsheet size={size} />;
  }
  if (["zip"].includes(extension || "")) {
    return <FileArchive size={size} />;
  }
  if (["pdf"].includes(extension || "")) {
    return <FileType2 size={size} />;
  }
  return <FileText size={size} />;
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    let message = `请求失败（${response.status}）`;
    try {
      const payload = await response.json();
      message = payload.detail || message;
    } catch {
      // Keep the fallback message.
    }
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

const STRUCTURED_HTML_PATTERN =
  /<(?:table|thead|tbody|tfoot|tr|th|td|caption|h[1-6]|ul|ol|li|blockquote|pre|code)\b/i;

const SAFE_RESULT_TAGS = new Set([
  "table",
  "thead",
  "tbody",
  "tfoot",
  "tr",
  "th",
  "td",
  "caption",
  "colgroup",
  "col",
  "p",
  "br",
  "strong",
  "b",
  "em",
  "i",
  "u",
  "s",
  "del",
  "ins",
  "sup",
  "sub",
  "ul",
  "ol",
  "li",
  "h1",
  "h2",
  "h3",
  "h4",
  "h5",
  "h6",
  "blockquote",
  "pre",
  "code",
  "hr",
  "div",
  "span",
]);

const DROPPED_RESULT_TAGS = new Set([
  "script",
  "style",
  "iframe",
  "object",
  "embed",
  "svg",
  "math",
  "form",
  "input",
  "button",
  "textarea",
  "select",
  "option",
  "link",
  "meta",
  "base",
  "template",
]);

function hasStructuredHtml(value: string) {
  return STRUCTURED_HTML_PATTERN.test(value);
}

function safeIntegerAttribute(value: string, maximum = 100) {
  if (!/^\d{1,3}$/.test(value)) return null;
  const number = Number(value);
  return number >= 1 && number <= maximum ? String(number) : null;
}

function sanitizeResultHtml(value: string) {
  if (typeof document === "undefined" || typeof DOMParser === "undefined") {
    return "";
  }

  const parsed = new DOMParser().parseFromString(value, "text/html");
  const output = document.createElement("div");

  const appendSafeNode = (source: Node, target: Node) => {
    if (source.nodeType === Node.TEXT_NODE) {
      target.appendChild(document.createTextNode(source.textContent || ""));
      return;
    }
    if (source.nodeType !== Node.ELEMENT_NODE) return;

    const sourceElement = source as Element;
    const tag = sourceElement.tagName.toLowerCase();
    if (DROPPED_RESULT_TAGS.has(tag)) return;

    if (!SAFE_RESULT_TAGS.has(tag)) {
      Array.from(source.childNodes).forEach((child) =>
        appendSafeNode(child, target),
      );
      return;
    }

    const cleanElement = document.createElement(tag);
    const direction = sourceElement.getAttribute("dir");
    if (direction && ["ltr", "rtl", "auto"].includes(direction)) {
      cleanElement.setAttribute("dir", direction);
    }
    if (tag === "td" || tag === "th") {
      for (const attribute of ["colspan", "rowspan"]) {
        const safeValue = safeIntegerAttribute(
          sourceElement.getAttribute(attribute) || "",
        );
        if (safeValue) cleanElement.setAttribute(attribute, safeValue);
      }
      const scope = sourceElement.getAttribute("scope");
      if (scope && ["row", "col", "rowgroup", "colgroup"].includes(scope)) {
        cleanElement.setAttribute("scope", scope);
      }
    }
    if (tag === "ol") {
      const start = safeIntegerAttribute(
        sourceElement.getAttribute("start") || "",
        999,
      );
      if (start) cleanElement.setAttribute("start", start);
    }
    if (tag === "li") {
      const itemValue = safeIntegerAttribute(
        sourceElement.getAttribute("value") || "",
        999,
      );
      if (itemValue) cleanElement.setAttribute("value", itemValue);
    }

    Array.from(source.childNodes).forEach((child) =>
      appendSafeNode(child, cleanElement),
    );
    target.appendChild(cleanElement);
  };

  Array.from(parsed.body.childNodes).forEach((child) =>
    appendSafeNode(child, output),
  );
  return output.innerHTML;
}

function htmlResultToPlainText(value: string) {
  if (!hasStructuredHtml(value)) return value;
  if (typeof DOMParser === "undefined") {
    return value
      .replace(/<br\s*\/?>/gi, "\n")
      .replace(/<\/(?:td|th)>/gi, "\t")
      .replace(/<\/(?:tr|p|h[1-6]|li|blockquote)>/gi, "\n")
      .replace(/<[^>]+>/g, "")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  }

  const parsed = new DOMParser().parseFromString(value, "text/html");
  parsed
    .querySelectorAll(
      "script,style,iframe,object,embed,svg,math,form,template",
    )
    .forEach((element) => element.remove());
  parsed.querySelectorAll("br").forEach((element) => element.replaceWith("\n"));
  parsed.querySelectorAll("td,th").forEach((element) => element.append("\t"));
  parsed
    .querySelectorAll("tr,p,h1,h2,h3,h4,h5,h6,li,blockquote")
    .forEach((element) => element.append("\n"));
  return (parsed.body.textContent || "")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\t+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function RichResultPreview({ value }: { value: string }) {
  const [safeMarkup, setSafeMarkup] = useState("");

  useEffect(() => {
    const timer = window.setTimeout(
      () => setSafeMarkup(sanitizeResultHtml(value)),
      0,
    );
    return () => window.clearTimeout(timer);
  }, [value]);

  return (
    <div className="rich-result-preview">
      {safeMarkup ? (
        <div
          className="rich-result-document"
          // The markup is rebuilt from a strict tag and attribute allowlist.
          dangerouslySetInnerHTML={{ __html: safeMarkup }}
        />
      ) : (
        <div className="rich-result-empty">正在整理表格排版…</div>
      )}
    </div>
  );
}

function UploadPanel({
  options,
  setOptions,
  onFiles,
  uploading,
  compact = false,
}: {
  options: OcrOptions;
  setOptions: (next: OcrOptions) => void;
  onFiles: (files: File[]) => void;
  uploading: string | null;
  compact?: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const choose = () => inputRef.current?.click();
  const selected = (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    if (files.length) onFiles(files);
    event.target.value = "";
  };
  const dropped = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    const files = Array.from(event.dataTransfer.files || []);
    if (files.length) onFiles(files);
  };

  return (
    <div className={`upload-panel ${compact ? "upload-panel-compact" : ""}`}>
      <div
        className={`drop-zone ${dragging ? "is-dragging" : ""}`}
        onDragEnter={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget as Node)) {
            setDragging(false);
          }
        }}
        onDrop={dropped}
        role="button"
        tabIndex={0}
        onClick={choose}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") choose();
        }}
        aria-label="选择要扫描的文件"
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPTED_FILES}
          onChange={selected}
          hidden
        />
        <div className="scan-corners" aria-hidden="true">
          <span />
          <span />
          <span />
          <span />
        </div>
        <div className="drop-icon">
          {uploading ? (
            <LoaderCircle className="spin" size={28} />
          ) : (
            <UploadCloud size={29} />
          )}
        </div>
        <div className="drop-copy">
          <strong>{uploading || "拖入文件，或点击选择"}</strong>
          <span>
            支持批量上传；每个文件会成为一个独立任务，便于查看与导出
          </span>
        </div>
        <button
          className="button button-primary choose-button"
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            choose();
          }}
          disabled={Boolean(uploading)}
        >
          <FolderOpen size={16} />
          选择文件
        </button>
      </div>

      <div className="format-strip" aria-label="支持的文件格式">
        <span><FileImage size={14} /> 图片 / 多页 TIFF</span>
        <span><FileType2 size={14} /> PDF</span>
        <span><FileText size={14} /> Word / PPT</span>
        <span><FileSpreadsheet size={14} /> Excel</span>
        <span><FileArchive size={14} /> ZIP 压缩包</span>
      </div>

      <div className="quick-options">
        <div className="option-group">
          <span className="option-label">识别模式</span>
          <div className="segmented">
            <button
              type="button"
              className={options.mode === "precision" ? "active" : ""}
              onClick={() => setOptions({ ...options, mode: "precision" })}
            >
              <Sparkles size={14} />
              高精度
            </button>
            <button
              type="button"
              className={options.mode === "fast" ? "active" : ""}
              onClick={() => setOptions({ ...options, mode: "fast" })}
            >
              <Zap size={14} />
              快速
            </button>
          </div>
        </div>
        <label className="field-inline">
          <span>页码范围</span>
          <input
            value={options.page_range}
            onChange={(event) =>
              setOptions({ ...options, page_range: event.target.value })
            }
            placeholder="全部，如 1-5,8"
          />
        </label>
        <button
          type="button"
          className="advanced-toggle"
          onClick={() => setShowAdvanced((value) => !value)}
          aria-expanded={showAdvanced}
        >
          <Settings2 size={15} />
          更多设置
          <ChevronDown
            size={14}
            className={showAdvanced ? "turned" : ""}
          />
        </button>
      </div>

      {showAdvanced && (
        <div className="advanced-grid">
          <label>
            <span>扫描清晰度</span>
            <select
              value={options.dpi}
              onChange={(event) =>
                setOptions({ ...options, dpi: Number(event.target.value) })
              }
            >
              <option value={120}>120 DPI · 更快</option>
              <option value={160}>160 DPI · 推荐</option>
              <option value={220}>220 DPI · 小字</option>
              <option value={300}>300 DPI · 极小字</option>
            </select>
          </label>
          <label>
            <span>最长输出</span>
            <select
              value={options.max_length}
              onChange={(event) =>
                setOptions({
                  ...options,
                  max_length: Number(event.target.value),
                })
              }
            >
              <option value={4096}>4K · 普通页面</option>
              <option value={8192}>8K · 推荐</option>
              <option value={16384}>16K · 长表格</option>
              <option value={32768}>32K · 超长页面</option>
            </select>
          </label>
          <label>
            <span>语言提示</span>
            <select
              value={options.language_hint}
              onChange={(event) =>
                setOptions({ ...options, language_hint: event.target.value })
              }
            >
              <option value="auto">自动识别</option>
              <option value="zh">中文为主</option>
              <option value="en">英文为主</option>
              <option value="mixed">中英混排</option>
            </select>
          </label>
          <label>
            <span>结果样式</span>
            <select
              value={options.output_style}
              onChange={(event) =>
                setOptions({ ...options, output_style: event.target.value })
              }
            >
              <option value="structured">保留结构</option>
              <option value="plain">纯文字</option>
              <option value="table">优先还原表格</option>
            </select>
          </label>
          <label className="prompt-field">
            <span>模型指令</span>
            <textarea
              value={options.prompt}
              onChange={(event) =>
                setOptions({ ...options, prompt: event.target.value })
              }
              rows={2}
              placeholder="document parsing."
            />
            <small>模型原生推荐指令为 document parsing.</small>
          </label>
        </div>
      )}
    </div>
  );
}

export default function Home() {
  const [health, setHealth] = useState<Health | null>(null);
  const [backendOnline, setBackendOnline] = useState(false);
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [currentPage, setCurrentPage] = useState(0);
  const [options, setOptionsState] = useState<OcrOptions>(defaultOptions);
  const [uploading, setUploading] = useState<string | null>(null);
  const [showUpload, setShowUpload] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [jobQuery, setJobQuery] = useState("");
  const [jobFilter, setJobFilter] = useState<
    "all" | "active" | "completed" | "failed"
  >("all");
  const [draft, setDraft] = useState("");
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [resultQuery, setResultQuery] = useState("");
  const [matchIndex, setMatchIndex] = useState(0);
  const [resultView, setResultView] = useState<"preview" | "source">(
    "preview",
  );
  const [readerMode, setReaderMode] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [dark, setDark] = useState(false);
  const textAreaRef = useRef<HTMLTextAreaElement>(null);
  const toastId = useRef(0);

  const notify = useCallback(
    (message: string, kind: Toast["kind"] = "info") => {
      const id = ++toastId.current;
      setToasts((items) => [...items, { id, message, kind }]);
      window.setTimeout(
        () => setToasts((items) => items.filter((item) => item.id !== id)),
        3600,
      );
    },
    [],
  );

  const setOptions = useCallback((next: OcrOptions) => {
    setOptionsState(next);
    window.localStorage.setItem("ocr-studio-options", JSON.stringify(next));
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const storedOptions = window.localStorage.getItem("ocr-studio-options");
      const storedTheme = window.localStorage.getItem("ocr-studio-theme");
      if (storedOptions) {
        try {
          setOptionsState({ ...defaultOptions, ...JSON.parse(storedOptions) });
        } catch {
          // Ignore malformed local preferences.
        }
      }
      if (storedTheme === "dark") setDark(true);
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    window.localStorage.setItem("ocr-studio-theme", dark ? "dark" : "light");
  }, [dark]);

  const refresh = useCallback(async () => {
    try {
      const [healthResult, jobResult] = await Promise.all([
        api<Health>("/api/health"),
        api<{ jobs: JobSummary[] }>("/api/jobs"),
      ]);
      setHealth(healthResult);
      setBackendOnline(true);
      setJobs(jobResult.jobs);
      if (selectedId && !readerMode) {
        try {
          const detail = await api<Job>(`/api/jobs/${selectedId}`);
          setSelectedJob(detail);
        } catch {
          setSelectedId(null);
          setSelectedJob(null);
          setCurrentPage(0);
          setDraft("");
          setDirty(false);
          setResultQuery("");
          setResultView("preview");
        }
      }
    } catch {
      setBackendOnline(false);
    }
  }, [readerMode, selectedId]);

  useEffect(() => {
    const run = () => void refresh();
    const initial = window.setTimeout(run, 0);
    const timer = window.setInterval(run, 1600);
    return () => {
      window.clearTimeout(initial);
      window.clearInterval(timer);
    };
  }, [refresh]);

  useEffect(() => {
    const disconnect = () => {
      navigator.sendBeacon(`${API_BASE}/api/client/disconnect`);
    };
    window.addEventListener("pagehide", disconnect);
    return () => window.removeEventListener("pagehide", disconnect);
  }, []);

  const resetReader = useCallback(() => {
    setReaderMode(false);
    setCurrentPage(0);
    setDraft("");
    setDirty(false);
    setResultQuery("");
    setMatchIndex(0);
    setResultView("preview");
  }, []);

  const selectedPage = selectedJob?.pages?.[currentPage] || null;

  useEffect(() => {
    if (dirty) return;
    const nextDraft = selectedPage?.text || "";
    const timer = window.setTimeout(() => setDraft(nextDraft), 0);
    return () => window.clearTimeout(timer);
  }, [selectedPage?.text, selectedPage?.index, dirty]);

  const saveCurrentPage = useCallback(
    async (silent = false) => {
      if (!selectedJob || !selectedPage || !dirty) return;
      setSaving(true);
      try {
        const updated = await api<Job>(
          `/api/jobs/${selectedJob.id}/pages/${selectedPage.index}`,
          {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: draft }),
          },
        );
        setSelectedJob(updated);
        setDirty(false);
        if (!silent) notify("本页修改已保存", "success");
      } catch (error) {
        notify((error as Error).message, "error");
      } finally {
        setSaving(false);
      }
    },
    [selectedJob, selectedPage, dirty, draft, notify],
  );

  useEffect(() => {
    if (!dirty || !selectedPage) return;
    const timer = window.setTimeout(() => saveCurrentPage(true), 1200);
    return () => window.clearTimeout(timer);
  }, [draft, dirty, selectedPage, saveCurrentPage]);

  const openJob = async (jobId: string) => {
    if (dirty) await saveCurrentPage(true);
    resetReader();
    setSelectedJob(null);
    setSelectedId(jobId);
    setSidebarOpen(false);
    try {
      setSelectedJob(await api<Job>(`/api/jobs/${jobId}`));
    } catch (error) {
      notify((error as Error).message, "error");
    }
  };

  const uploadFiles = async (files: File[]) => {
    if (!backendOnline) {
      notify("后端服务尚未启动，请先双击“启动 OCR 工作台”", "error");
      return;
    }
    setShowUpload(false);
    for (let index = 0; index < files.length; index += 1) {
      const file = files[index];
      setUploading(`正在上传 ${index + 1}/${files.length} · ${file.name}`);
      try {
        const job = await api<Job>("/api/jobs", {
          method: "POST",
          headers: {
            "Content-Type": "application/octet-stream",
            "X-File-Name": encodeURIComponent(file.name),
            "X-File-Type": file.type || "application/octet-stream",
            "X-OCR-Options": encodeURIComponent(JSON.stringify(options)),
          },
          body: file,
        });
        resetReader();
        setSelectedId(job.id);
        setSelectedJob(job);
        notify(`${file.name} 已加入识别队列`, "success");
      } catch (error) {
        notify(`${file.name}：${(error as Error).message}`, "error");
      }
    }
    setUploading(null);
    refresh();
  };

  const jobAction = async (
    action: "cancel" | "retry" | "delete",
    job: Job,
  ) => {
    try {
      if (action === "delete") {
        if (!window.confirm(`确定删除“${job.filename}”及其本地结果吗？`)) return;
        await api<void>(`/api/jobs/${job.id}`, { method: "DELETE" });
        resetReader();
        setSelectedId(null);
        setSelectedJob(null);
        notify("任务及本地结果已删除", "success");
      } else {
        const updated = await api<Job>(`/api/jobs/${job.id}/${action}`, {
          method: "POST",
        });
        setSelectedJob(updated);
        notify(action === "cancel" ? "已提交取消请求" : "任务已重新排队");
      }
      refresh();
    } catch (error) {
      notify((error as Error).message, "error");
    }
  };

  const modelAction = async (action: "load" | "unload") => {
    try {
      await api(`/api/model/${action}`, { method: "POST" });
      notify(action === "load" ? "正在载入本机模型" : "模型已卸载", "success");
      refresh();
    } catch (error) {
      notify((error as Error).message, "error");
    }
  };

  const modelDownloadAction = async (action: "start" | "cancel") => {
    try {
      await api(
        action === "start"
          ? "/api/model/download"
          : "/api/model/download/cancel",
        { method: "POST" },
      );
      notify(
        action === "start"
          ? "模型下载已经开始，可在这里查看进度"
          : "正在暂停模型下载",
        "success",
      );
      refresh();
    } catch (error) {
      notify((error as Error).message, "error");
    }
  };

  const filteredJobs = useMemo(() => {
    const query = jobQuery.trim().toLowerCase();
    return jobs.filter((job) => {
      const matchesQuery = !query || job.filename.toLowerCase().includes(query);
      const matchesFilter =
        jobFilter === "all" ||
        (jobFilter === "active" &&
          ["uploading", "queued", "preparing", "running", "canceling"].includes(
            job.status,
          )) ||
        (jobFilter === "completed" &&
          ["completed", "partial"].includes(job.status)) ||
        (jobFilter === "failed" &&
          ["failed", "canceled"].includes(job.status));
      return matchesQuery && matchesFilter;
    });
  }, [jobs, jobQuery, jobFilter]);

  const currentResultHasHtml = useMemo(
    () => hasStructuredHtml(draft),
    [draft],
  );

  const currentPlainText = useMemo(
    () => htmlResultToPlainText(draft),
    [draft],
  );

  const allPlainResultText = useMemo(() => {
    if (!selectedJob) return "";
    return selectedJob.pages
      .map(
        (page) =>
          `${page.label}\n${htmlResultToPlainText(page.text || "")}`,
      )
      .join("\n\n");
  }, [selectedJob]);

  const downloadPlainText = () => {
    if (!selectedJob || !allPlainResultText) return;
    const stem =
      selectedJob.filename.replace(/\.[^.]+$/, "").trim() || "OCR结果";
    const blob = new Blob([allPlainResultText], {
      type: "text/plain;charset=utf-8",
    });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${stem}-纯文本.txt`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => window.URL.revokeObjectURL(url), 1000);
    notify("纯文本 TXT 已生成", "success");
  };

  const matches = useMemo(() => {
    const query = resultQuery.trim().toLocaleLowerCase();
    if (!query) return [];
    const text = draft.toLocaleLowerCase();
    const positions: number[] = [];
    let from = 0;
    while (positions.length < 500) {
      const found = text.indexOf(query, from);
      if (found === -1) break;
      positions.push(found);
      from = found + Math.max(query.length, 1);
    }
    return positions;
  }, [draft, resultQuery]);

  const goToMatch = (direction: 1 | -1) => {
    if (!matches.length || !textAreaRef.current) return;
    const next = (matchIndex + direction + matches.length) % matches.length;
    setMatchIndex(next);
    textAreaRef.current.focus();
    textAreaRef.current.setSelectionRange(
      matches[next],
      matches[next] + resultQuery.length,
    );
  };

  const changePage = async (index: number) => {
    if (dirty) await saveCurrentPage(true);
    setCurrentPage(index);
    setDirty(false);
    setResultQuery("");
    setResultView("preview");
  };

  const copyText = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text);
      notify(`${label}已复制`, "success");
    } catch {
      notify("复制失败，请手动选择文字", "error");
    }
  };

  const openDocumentReader = async () => {
    if (!selectedJob?.pages.length) return;
    if (dirty) await saveCurrentPage(true);
    try {
      if (
        health?.model.loaded &&
        !health.model.busy &&
        health.queue_size === 0
      ) {
        try {
          await api("/api/model/unload", { method: "POST" });
        } catch {
          // Reading does not need the model. A busy model will still be
          // released by the existing queue and window lifecycle safeguards.
        }
      }
      const prepared = await api<{
        job: Job;
        changed_pages: number;
        removed_chars: number;
      }>(`/api/jobs/${selectedJob.id}/reader/prepare`, {
        method: "POST",
      });
      setSelectedJob(prepared.job);
      setReaderMode(true);
      if (prepared.changed_pages) {
        notify(
          `阅读版已整理 ${prepared.changed_pages} 页，清理 ${prepared.removed_chars.toLocaleString()} 个重复字符；原始 OCR 已保留`,
          "success",
        );
      }
    } catch (error) {
      notify((error as Error).message, "error");
    }
  };

  const model = health?.model;
  const modelTone =
    !backendOnline || model?.state === "error"
      ? "error"
      : model?.state === "ready"
        ? "ready"
        : model?.state === "running" || model?.state === "loading"
          ? "working"
          : "idle";
  const modelLabel = !backendOnline
    ? "服务未连接"
    : model?.state === "ready"
      ? "模型已就绪"
      : model?.state === "running"
        ? "模型识别中"
        : model?.state === "loading"
          ? "正在加载模型"
          : model?.state === "error"
            ? "模型异常"
            : "模型待加载";

  if (readerMode && selectedJob) {
    return (
      <>
        <DocumentReader
          job={selectedJob}
          initialPage={currentPage}
          apiBase={API_BASE}
          renderResult={(value) => <RichResultPreview value={value} />}
          plainText={htmlResultToPlainText}
          onClose={() => setReaderMode(false)}
          onEditPage={(index) => {
            setCurrentPage(index);
            setDirty(false);
            setResultQuery("");
            setResultView("source");
            setReaderMode(false);
          }}
          onNotify={notify}
        />
        <div className="toast-stack" aria-live="polite">
          {toasts.map((toast) => (
            <div className={`toast toast-${toast.kind}`} key={toast.id}>
              {toast.kind === "success" ? (
                <Check size={16} />
              ) : toast.kind === "error" ? (
                <CircleAlert size={16} />
              ) : (
                <Gauge size={16} />
              )}
              <span>{toast.message}</span>
              <button
                onClick={() =>
                  setToasts((items) =>
                    items.filter((item) => item.id !== toast.id),
                  )
                }
                aria-label="关闭提示"
              >
                <X size={13} />
              </button>
            </div>
          ))}
        </div>
      </>
    );
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <button
            className="icon-button mobile-menu"
            onClick={() => setSidebarOpen((value) => !value)}
            aria-label="打开任务列表"
          >
            <Menu size={19} />
          </button>
          <div className="brand-mark">
            <ScanLine size={22} />
          </div>
          <div>
            <div className="brand-name">墨析</div>
            <div className="brand-subtitle">本地 OCR 工作台</div>
          </div>
        </div>

        <div className="topbar-actions">
          <button
            className={`model-pill model-${modelTone}`}
            onClick={() => setShowSettings(true)}
            type="button"
          >
            <span className="status-dot" />
            <span>{modelLabel}</span>
            {model?.size_gb ? <small>{model.size_gb} GB</small> : null}
          </button>
          <div className="privacy-badge">
            <ShieldCheck size={15} />
            文件仅在本机
          </div>
          <button
            className="icon-button"
            onClick={() => setDark((value) => !value)}
            aria-label={dark ? "切换浅色模式" : "切换深色模式"}
          >
            {dark ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          <button
            className="icon-button"
            onClick={() => setShowSettings(true)}
            aria-label="打开系统状态"
          >
            <Settings2 size={18} />
          </button>
        </div>
      </header>

      {!backendOnline && (
        <div className="offline-banner">
          <CircleAlert size={17} />
          <span>
            本机后端尚未连接。请双击项目中的“启动 OCR 工作台.command”。
          </span>
          <button onClick={refresh}>
            <RefreshCw size={14} /> 重新连接
          </button>
        </div>
      )}

      {backendOnline && health && (!health.model_download.model_ready || !health.model_download.runtime_ready) && (
        <div className="offline-banner model-setup-banner">
          <Download size={17} />
          <span>{health.model_download.running ? health.model_download.message : "首次使用？先下载本机识别模型，无需预装 LM Studio。"}</span>
          <button onClick={() => setShowSettings(true)}>
            {health.model_download.running ? `查看下载 ${health.model_download.progress}%` : "下载模型"}
          </button>
        </div>
      )}

      <div className="app-body">
        <aside className={`sidebar ${sidebarOpen ? "sidebar-open" : ""}`}>
          <div className="sidebar-top">
            <button
              className="button button-primary new-task"
              onClick={() => setShowUpload(true)}
            >
              <Plus size={17} />
              新建扫描
            </button>
            <button
              className="icon-button sidebar-close"
              onClick={() => setSidebarOpen(false)}
              aria-label="关闭任务列表"
            >
              <X size={18} />
            </button>
          </div>

          <div className="task-heading">
            <span>任务记录</span>
            <small>{jobs.length}</small>
          </div>
          <div className="sidebar-search">
            <Search size={15} />
            <input
              value={jobQuery}
              onChange={(event) => setJobQuery(event.target.value)}
              placeholder="搜索文件名"
            />
            {jobQuery && (
              <button onClick={() => setJobQuery("")} aria-label="清空搜索">
                <X size={13} />
              </button>
            )}
          </div>
          <div className="filter-tabs">
            {(
              [
                ["all", "全部"],
                ["active", "处理中"],
                ["completed", "已完成"],
                ["failed", "异常"],
              ] as const
            ).map(([value, label]) => (
              <button
                key={value}
                className={jobFilter === value ? "active" : ""}
                onClick={() => setJobFilter(value)}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="task-list">
            {!filteredJobs.length && (
              <div className="empty-list">
                <Archive size={23} />
                <span>{jobs.length ? "没有匹配任务" : "扫描任务会显示在这里"}</span>
              </div>
            )}
            {filteredJobs.map((job) => {
              const meta = statusMeta[job.status] || statusMeta.queued;
              return (
                <button
                  className={`task-card ${selectedId === job.id ? "selected" : ""}`}
                  key={job.id}
                  onClick={() => openJob(job.id)}
                >
                  <div className={`file-tile tile-${meta.tone}`}>
                    {fileIcon(job.filename)}
                  </div>
                  <div className="task-card-body">
                    <strong title={job.filename}>{job.filename}</strong>
                    <div className="task-meta">
                      <span className={`mini-status tone-${meta.tone}`}>
                        {meta.active && <LoaderCircle className="spin" size={11} />}
                        {meta.label}
                      </span>
                      <span>{formatDate(job.created_at)}</span>
                    </div>
                    {meta.active && (
                      <div className="mini-progress">
                        <span style={{ width: `${job.progress || 2}%` }} />
                      </div>
                    )}
                  </div>
                </button>
              );
            })}
          </div>

          <div className="sidebar-foot">
            <HardDrive size={15} />
            <div>
              <strong>本地持久保存</strong>
              <span>任务与结果保留在这台 Mac</span>
            </div>
          </div>
        </aside>

        {sidebarOpen && (
          <button
            className="sidebar-scrim"
            onClick={() => setSidebarOpen(false)}
            aria-label="关闭侧栏"
          />
        )}

        <main className="main-content">
          {!selectedJob ? (
            <section className="welcome-view">
              <div className="welcome-heading">
                <div className="eyebrow">
                  <span />
                  PRIVATE DOCUMENT INTELLIGENCE
                </div>
                <h1>
                  把复杂文件变成
                  <br />
                  <em>可编辑的清晰文字</em>
                </h1>
                <p>
                  图片、扫描 PDF、Word、Excel、PPT
                  或压缩包都可以批量投入。识别、预览、校对和导出全部在本机完成。
                </p>
              </div>

              <UploadPanel
                options={options}
                setOptions={setOptions}
                onFiles={uploadFiles}
                uploading={uploading}
              />

              <div className="feature-row">
                <div>
                  <span className="feature-icon"><ScanLine size={18} /></span>
                  <strong>逐页高精度识别</strong>
                  <p>动态切片处理小字、表格和复杂版面。</p>
                </div>
                <div>
                  <span className="feature-icon"><PackageOpen size={18} /></span>
                  <strong>批量与多格式</strong>
                  <p>自动拆分 PDF、Office、多帧图片和 ZIP。</p>
                </div>
                <div>
                  <span className="feature-icon"><ShieldCheck size={18} /></span>
                  <strong>隐私留在本机</strong>
                  <p>文件和识别结果不会发送到云端服务。</p>
                </div>
              </div>
            </section>
          ) : (
            <section className="job-view">
              <div className="job-header">
                <div className="job-title">
                  <button
                    className="icon-button mobile-back"
                    onClick={() => {
                      resetReader();
                      setSelectedId(null);
                      setSelectedJob(null);
                    }}
                    aria-label="返回首页"
                  >
                    <ArrowLeft size={18} />
                  </button>
                  <div className="job-file-icon">
                    {fileIcon(selectedJob.filename, 21)}
                  </div>
                  <div>
                    <h2 title={selectedJob.filename}>{selectedJob.filename}</h2>
                    <div className="job-subtitle">
                      <span>{formatBytes(selectedJob.size)}</span>
                      <span>·</span>
                      <span>{formatDate(selectedJob.created_at)}</span>
                      {selectedJob.stats.total_pages > 0 && (
                        <>
                          <span>·</span>
                          <span>{selectedJob.stats.total_pages} 页</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
                <div className="job-actions">
                  {["uploading", "queued", "preparing", "running", "canceling"].includes(
                    selectedJob.status,
                  ) && (
                    <button
                      className="button button-secondary"
                      onClick={() => jobAction("cancel", selectedJob)}
                      disabled={selectedJob.status === "canceling"}
                    >
                      <Square size={14} />
                      取消
                    </button>
                  )}
                  {["failed", "partial", "canceled"].includes(selectedJob.status) && (
                    <button
                      className="button button-secondary"
                      onClick={() => jobAction("retry", selectedJob)}
                    >
                      <RotateCcw size={15} />
                      重试
                    </button>
                  )}
                  {selectedJob.pages.length > 0 &&
                    ["completed", "partial", "failed", "canceled"].includes(
                      selectedJob.status,
                    ) && (
                      <button
                        className="button button-reader"
                        onClick={openDocumentReader}
                      >
                        <BookOpen size={15} />
                        阅读
                      </button>
                    )}
                  {selectedJob.pages.length > 0 && (
                    <div className="download-menu">
                      <button className="button button-primary">
                        <Download size={15} />
                        导出
                        <ChevronDown size={13} />
                      </button>
                      <div className="download-popover">
                        <button type="button" onClick={downloadPlainText}>
                          <FileText size={15} /> 纯文本 TXT
                        </button>
                        <a href={`${API_BASE}/api/jobs/${selectedJob.id}/download/md`}>
                          <FileType2 size={15} /> Markdown
                        </a>
                        <a href={`${API_BASE}/api/jobs/${selectedJob.id}/download/json`}>
                          <FileArchive size={15} /> 结构化 JSON
                        </a>
                        <a
                          href={`${API_BASE}/api/jobs/${selectedJob.id}/download/zip/package`}
                        >
                          <Archive size={15} /> 完整结果包
                        </a>
                      </div>
                    </div>
                  )}
                  <button
                    className="icon-button danger-hover"
                    onClick={() => jobAction("delete", selectedJob)}
                    aria-label="删除任务"
                  >
                    <Trash2 size={17} />
                  </button>
                </div>
              </div>

              <div className={`job-status-card status-${selectedJob.status}`}>
                <div className="status-symbol">
                  {["uploading", "queued", "preparing", "running", "canceling"].includes(
                    selectedJob.status,
                  ) ? (
                    <LoaderCircle className="spin" size={20} />
                  ) : selectedJob.status === "completed" ? (
                    <Check size={20} />
                  ) : (
                    <CircleAlert size={20} />
                  )}
                </div>
                <div className="status-copy">
                  <div>
                    <strong>{selectedJob.stage}</strong>
                    <span>
                      {selectedJob.stats.completed_pages > 0 &&
                        `${selectedJob.stats.completed_pages} 页已完成`}
                      {selectedJob.stats.failed_pages > 0 &&
                        ` · ${selectedJob.stats.failed_pages} 页失败`}
                    </span>
                  </div>
                  <b>{selectedJob.progress}%</b>
                </div>
                <div className="job-progress">
                  <span style={{ width: `${selectedJob.progress}%` }} />
                </div>
                {selectedJob.error && (
                  <p className="job-error">{selectedJob.error}</p>
                )}
              </div>

              {selectedJob.warnings?.length > 0 && (
                <details className="warning-box">
                  <summary>
                    <CircleAlert size={15} />
                    {selectedJob.warnings.length} 条文件处理提示
                    <ChevronDown size={14} />
                  </summary>
                  <ul>
                    {selectedJob.warnings.map((warning, index) => (
                      <li key={`${warning}-${index}`}>{warning}</li>
                    ))}
                  </ul>
                </details>
              )}

              {selectedJob.pages.length ? (
                <div className="document-workspace">
                  <section className="preview-pane">
                    <div className="pane-toolbar">
                      <div>
                        <ImageIcon size={16} />
                        <strong>页面预览</strong>
                      </div>
                      <div className="page-nav">
                        <button
                          onClick={() => changePage(Math.max(0, currentPage - 1))}
                          disabled={currentPage === 0}
                          aria-label="上一页"
                        >
                          <ArrowLeft size={15} />
                        </button>
                        <span>
                          {currentPage + 1} / {selectedJob.pages.length}
                        </span>
                        <button
                          onClick={() =>
                            changePage(
                              Math.min(
                                selectedJob.pages.length - 1,
                                currentPage + 1,
                              ),
                            )
                          }
                          disabled={currentPage >= selectedJob.pages.length - 1}
                          aria-label="下一页"
                        >
                          <ArrowRight size={15} />
                        </button>
                      </div>
                    </div>
                    <div className="preview-stage">
                      {selectedPage?.image_file ? (
                        // The image is served by the local OCR API and must
                        // reflect edits immediately; Next image optimization
                        // would add no benefit for this localhost-only view.
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          key={`${selectedJob.id}-${selectedPage.index}`}
                          src={`${API_BASE}/api/jobs/${selectedJob.id}/pages/${selectedPage.index}/image`}
                          alt={selectedPage.label}
                        />
                      ) : (
                        <div className="direct-preview">
                          <FileText size={44} />
                          <strong>文本型文件</strong>
                          <span>内容已直接读取，无需图像识别</span>
                        </div>
                      )}
                    </div>
                    <div className="page-strip">
                      {selectedJob.pages.map((page, index) => (
                        <button
                          key={`${page.index}-${page.status}`}
                          className={currentPage === index ? "active" : ""}
                          onClick={() => changePage(index)}
                          title={page.label}
                        >
                          <span>{index + 1}</span>
                          {page.status === "completed" && <Check size={11} />}
                          {page.status === "failed" && <CircleAlert size={11} />}
                          {page.status === "running" && (
                            <LoaderCircle className="spin" size={11} />
                          )}
                        </button>
                      ))}
                    </div>
                  </section>

                  <section className="result-pane">
                    <div className="pane-toolbar result-toolbar">
                      <div>
                        <FileText size={16} />
                        <strong>识别结果</strong>
                        {selectedPage?.edited && (
                          <span className="edited-badge">已校对</span>
                        )}
                      </div>
                      <div className="result-actions">
                        <button
                          onClick={() =>
                            copyText(
                              currentResultHasHtml &&
                                resultView === "preview"
                                ? currentPlainText
                                : draft,
                              currentResultHasHtml &&
                                resultView === "preview"
                                ? "本页纯文本"
                                : "本页内容",
                            )
                          }
                          disabled={!draft}
                        >
                          <Copy size={14} />
                          {currentResultHasHtml &&
                          resultView === "preview"
                            ? "复制纯文本"
                            : "复制本页"}
                        </button>
                        <button
                          onClick={() =>
                            copyText(allPlainResultText, "全部纯文本")
                          }
                          disabled={!allPlainResultText}
                        >
                          <Clipboard size={14} /> 复制全部
                        </button>
                        <button
                          onClick={() => saveCurrentPage(false)}
                          disabled={!dirty || saving}
                          className={dirty ? "save-active" : ""}
                        >
                          {saving ? (
                            <LoaderCircle className="spin" size={14} />
                          ) : (
                            <Save size={14} />
                          )}
                          {saving ? "保存中" : "保存"}
                        </button>
                      </div>
                    </div>
                    {currentResultHasHtml && (
                      <div className="result-view-bar">
                        <div
                          className="result-view-tabs"
                          role="tablist"
                          aria-label="识别结果显示方式"
                        >
                          <button
                            type="button"
                            role="tab"
                            aria-selected={resultView === "preview"}
                            className={
                              resultView === "preview" ? "active" : ""
                            }
                            onClick={() => {
                              setResultView("preview");
                              setResultQuery("");
                            }}
                          >
                            <Eye size={14} /> 排版预览
                          </button>
                          <button
                            type="button"
                            role="tab"
                            aria-selected={resultView === "source"}
                            className={
                              resultView === "source" ? "active" : ""
                            }
                            onClick={() => setResultView("source")}
                          >
                            <Code2 size={14} /> 原始文本
                          </button>
                        </div>
                        <span>
                          <ShieldCheck size={13} />
                          检测到表格结构，已安全排版
                        </span>
                      </div>
                    )}
                    {(!currentResultHasHtml ||
                      resultView === "source") && (
                      <div className="find-bar">
                        <Search size={14} />
                        <input
                          value={resultQuery}
                          onChange={(event) => {
                            setResultQuery(event.target.value);
                            setMatchIndex(0);
                          }}
                          placeholder="在本页结果中查找"
                        />
                        <span>
                          {resultQuery
                            ? matches.length
                              ? `${Math.min(matchIndex + 1, matches.length)} / ${matches.length}`
                              : "0 项"
                            : ""}
                        </span>
                        <button
                          onClick={() => goToMatch(-1)}
                          disabled={!matches.length}
                          aria-label="上一个匹配"
                        >
                          <ChevronDown className="up-chevron" size={15} />
                        </button>
                        <button
                          onClick={() => goToMatch(1)}
                          disabled={!matches.length}
                          aria-label="下一个匹配"
                        >
                          <ChevronDown size={15} />
                        </button>
                      </div>
                    )}
                    <div className="editor-wrap">
                      {selectedPage?.status === "running" && !draft ? (
                        <div className="editor-loading">
                          <div className="ocr-wave">
                            <span />
                            <span />
                            <span />
                            <span />
                          </div>
                          <strong>模型正在读取这一页</strong>
                          <span>高精度模式会把复杂页面切成多个区域</span>
                        </div>
                      ) : selectedPage?.status === "failed" ? (
                        <div className="editor-error">
                          <CircleAlert size={28} />
                          <strong>这一页没有识别成功</strong>
                          <span>{selectedPage.error}</span>
                        </div>
                      ) : currentResultHasHtml &&
                        resultView === "preview" ? (
                        <RichResultPreview value={draft} />
                      ) : (
                        <textarea
                          ref={textAreaRef}
                          value={draft}
                          onChange={(event) => {
                            setDraft(event.target.value);
                            setDirty(true);
                          }}
                          placeholder={
                            selectedPage?.status === "completed"
                              ? "这一页没有返回文字，你可以在这里手动补充。"
                              : "识别结果生成后会显示在这里。"
                          }
                          readOnly={
                            !["completed", "failed"].includes(
                              selectedPage?.status || "",
                            )
                          }
                          spellCheck={false}
                        />
                      )}
                    </div>
                    <div className="editor-footer">
                      <span>
                        {draft.length.toLocaleString()} 字符
                        {selectedPage?.elapsed_seconds
                          ? ` · ${selectedPage.elapsed_seconds.toFixed(1)} 秒`
                          : ""}
                      </span>
                      <span>
                        {selectedPage?.repetition_trimmed
                          ? "已自动停止并清理重复输出"
                          : currentResultHasHtml &&
                              resultView === "preview"
                          ? "当前为排版预览；切换“原始文本”可校对"
                          : dirty
                            ? "修改将在片刻后自动保存"
                            : "结果已保存在本机"}
                      </span>
                    </div>
                  </section>
                </div>
              ) : (
                <div className="processing-empty">
                  <div className="processing-orbit">
                    <ScanLine size={28} />
                    <span />
                  </div>
                  <strong>{selectedJob.stage}</strong>
                  <p>页面准备好后，会在这里显示原稿与识别结果。</p>
                </div>
              )}
            </section>
          )}
        </main>
      </div>

      {showUpload && (
        <div className="modal-backdrop" onMouseDown={() => setShowUpload(false)}>
          <div
            className="modal upload-modal"
            role="dialog"
            aria-modal="true"
            aria-label="新建扫描任务"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="modal-header">
              <div>
                <span className="modal-kicker">NEW SCAN</span>
                <h2>新建扫描任务</h2>
                <p>可一次选择多个不同类型的文件。</p>
              </div>
              <button
                className="icon-button"
                onClick={() => setShowUpload(false)}
                aria-label="关闭"
              >
                <X size={19} />
              </button>
            </div>
            <UploadPanel
              options={options}
              setOptions={setOptions}
              onFiles={uploadFiles}
              uploading={uploading}
              compact
            />
          </div>
        </div>
      )}

      {showSettings && (
        <div
          className="drawer-backdrop"
          onMouseDown={() => setShowSettings(false)}
        >
          <aside
            className="settings-drawer"
            role="dialog"
            aria-modal="true"
            aria-label="系统状态"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="drawer-header">
              <div>
                <span className="modal-kicker">LOCAL ENGINE</span>
                <h2>本机引擎</h2>
              </div>
              <button
                className="icon-button"
                onClick={() => setShowSettings(false)}
                aria-label="关闭"
              >
                <X size={19} />
              </button>
            </div>

            <div className={`engine-card engine-${modelTone}`}>
              <div className="engine-icon">
                <Server size={22} />
              </div>
              <div>
                <strong>{modelLabel}</strong>
                <span>{model?.message || "正在等待本机服务"}</span>
              </div>
              <span className="status-dot" />
            </div>

            <div className="settings-section">
              <h3>
                {model?.platform === "windows"
                  ? "Unlimited-OCR Windows"
                  : "Unlimited-OCR MLX"}
              </h3>
              <dl>
                <div>
                  <dt>权重文件</dt>
                  <dd>{model?.weights_found ? "已找到" : "未找到"}</dd>
                </div>
                <div>
                  <dt>模型大小</dt>
                  <dd>{model?.size_gb ? `${model.size_gb} GB` : "—"}</dd>
                </div>
                <div>
                  <dt>内存状态</dt>
                  <dd>{model?.loaded ? "已载入" : "未载入"}</dd>
                </div>
                <div>
                  <dt>任务队列</dt>
                  <dd>{health?.queue_size || 0} 个等待</dd>
                </div>
                <div>
                  <dt>自动释放</dt>
                  <dd>
                    {health?.lifecycle.auto_unload
                      ? "已开启"
                      : "等待后端连接"}
                  </dd>
                </div>
                <div>
                  <dt>重复保护</dt>
                  <dd>循环检测 + 自动清理</dd>
                </div>
                {model?.platform === "windows" ? (
                  <div>
                    <dt>Windows 推理</dt>
                    <dd>{model.framework || "PyTorch + CUDA"}</dd>
                  </div>
                ) : null}
              </dl>
              {model?.platform === "windows" && model.hardware ? (
                <div
                  className={`hardware-note ${
                    model.hardware.compatible ? "hardware-ready" : "hardware-warning"
                  }`}
                >
                  {model.hardware.compatible ? (
                    <Check size={14} />
                  ) : (
                    <CircleAlert size={14} />
                  )}
                  <span>{model.hardware.message}</span>
                </div>
              ) : null}
              <div className="model-path" title={model?.path}>
                <HardDrive size={14} />
                <span>{model?.path || "—"}</span>
              </div>
              {health?.model_download ? (
                <div className="model-download-card">
                  <div className="model-download-copy">
                    <strong>{health.model_download.platform === "windows"
                      ? "Unlimited-OCR · Windows / NVIDIA"
                      : "Unlimited-OCR MLX · Apple Silicon"}</strong>
                    <span role="status">{health.model_download.message}</span>
                  </div>
                  <div className="model-download-progress">
                    <span
                      style={{
                        width: `${Math.max(
                          0,
                          Math.min(100, health.model_download.progress),
                        )}%`,
                      }}
                    />
                  </div>
                  <div className="model-download-meta">
                    <span>{health.model_download.progress}% · {(health.model_download.bytes_downloaded / 1024 ** 3).toFixed(2)} / {(health.model_download.bytes_total / 1024 ** 3).toFixed(2)} GB</span>
                    <a
                      href={health.model_download.model_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {health.model_download.model_id}
                    </a>
                  </div>
                  {health.model_download.running ? (
                    <button
                      className="button button-secondary"
                      onClick={() => modelDownloadAction("cancel")}
                      disabled={health.model_download.state === "canceling"}
                    >
                      <Square size={14} />
                      {health.model_download.state === "canceling" ? "正在暂停…" : "暂停下载"}
                    </button>
                  ) : (
                    <button
                      className="button button-primary"
                      onClick={() => modelDownloadAction("start")}
                      disabled={!health.model_download.available || model?.busy || model?.loaded || Boolean(health.queue_size)}
                    >
                      <Download size={14} />
                      {health.model_download.using_external_model
                        ? "下载到墨析独立目录"
                        : health.model_download.model_ready && health.model_download.runtime_ready
                        ? "校验 / 修复模型"
                        : health.model_download.state === "error" ||
                      health.model_download.state === "cancelled"
                        ? "继续下载"
                        : "下载模型与推理组件"}
                    </button>
                  )}
                  <small>支持暂停与断点续传；固定版本，完整校验后启用。关闭应用会暂停下载，重新打开后点“继续下载”。模型不包含在安装包中。</small>
                  <small>{health.model_download.platform === "windows"
                    ? "Windows 使用 PyTorch / NVIDIA CUDA，不使用 Apple MLX；首次还需下载推理组件，建议至少预留 18 GB。"
                    : "需要 Apple Silicon（M 系列）和 macOS 14+；无需安装 LM Studio，建议预留 8 GB 磁盘。"}</small>
                  <small className="model-download-path">保存至：{health.model_download.download_path}</small>
                  <small>模型版本：{health.model_download.model_revision.slice(0, 12)}</small>
                </div>
              ) : null}
              <div className="engine-actions">
                {!model?.loaded ? (
                  <button
                    className="button button-primary"
                    onClick={() => modelAction("load")}
                    disabled={
                      !backendOnline ||
                      !model?.weights_found ||
                      !health?.model_download.model_ready ||
                      !health?.model_download.runtime_ready ||
                      health?.model_download.running ||
                      model?.state === "loading"
                    }
                  >
                    {model?.state === "loading" ? (
                      <LoaderCircle className="spin" size={15} />
                    ) : (
                      <Play size={15} />
                    )}
                    {model?.state === "loading" ? "正在载入" : "预先载入模型"}
                  </button>
                ) : (
                  <button
                    className="button button-secondary"
                    onClick={() => modelAction("unload")}
                    disabled={model?.busy}
                  >
                    <Pause size={15} />
                    卸载并释放内存
                  </button>
                )}
              </div>
            </div>

            <div className="settings-section">
              <h3>文件转换能力</h3>
              <div className="capability-list">
                {[
                  ["图片与多页 TIFF", health?.converters.images],
                  ["PDF 文档", health?.converters.pdf],
                  ["Word / Excel / PPT", health?.converters.office],
                  ["ZIP 压缩包", health?.converters.archives],
                  ["文本与邮件", health?.converters.plain_text],
                ].map(([label, available]) => (
                  <div key={String(label)}>
                    {available ? (
                      <Check size={15} />
                    ) : (
                      <CircleAlert size={15} />
                    )}
                    <span>{label}</span>
                    <small>{available ? "可用" : "缺少转换器"}</small>
                  </div>
                ))}
              </div>
            </div>

            <div className="local-note">
              <ShieldCheck size={19} />
              <div>
                <strong>隐私说明</strong>
                <p>
                  后端只监听本机地址 127.0.0.1。上传文件、页面图像和结果均保存在这台
                  Mac，不会发送到外部 API。
                </p>
              </div>
            </div>
          </aside>
        </div>
      )}

      <div className="toast-stack" aria-live="polite">
        {toasts.map((toast) => (
          <div className={`toast toast-${toast.kind}`} key={toast.id}>
            {toast.kind === "success" ? (
              <Check size={16} />
            ) : toast.kind === "error" ? (
              <CircleAlert size={16} />
            ) : (
              <Gauge size={16} />
            )}
            <span>{toast.message}</span>
            <button
              onClick={() =>
                setToasts((items) =>
                  items.filter((item) => item.id !== toast.id),
                )
              }
              aria-label="关闭提示"
            >
              <X size={13} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
