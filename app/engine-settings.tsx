"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Check,
  CircleAlert,
  LoaderCircle,
  Plus,
  Server,
  Trash2,
  X,
  Zap,
} from "lucide-react";
import { ENGINE_API_BASE, type EngineEndpoint, type ScanEngine } from "./engines";

type Notify = (message: string, kind?: "success" | "error" | "info") => void;

type Draft = {
  id: string | null;
  name: string;
  base_url: string;
  model: string;
  api_key: string;
  max_concurrency: number;
  timeout_seconds: number;
  max_output_tokens: number;
};

const EMPTY_DRAFT: Draft = {
  id: null,
  name: "",
  base_url: "http://127.0.0.1:18081/v1",
  model: "qwen3.8-flash-next-iq3_s",
  api_key: "",
  max_concurrency: 3,
  timeout_seconds: 600,
  max_output_tokens: 16384,
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${ENGINE_API_BASE}${path}`, init);
  if (!response.ok) {
    let message = `请求失败（${response.status}）`;
    try {
      const payload = await response.json();
      message = payload.detail || payload.message || message;
    } catch {
      // Keep the fallback message.
    }
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

function toDraft(endpoint: EngineEndpoint): Draft {
  return {
    id: endpoint.id,
    name: endpoint.name,
    base_url: endpoint.base_url,
    model: endpoint.model,
    api_key: "",
    max_concurrency: endpoint.max_concurrency,
    timeout_seconds: endpoint.timeout_seconds,
    max_output_tokens: endpoint.max_output_tokens,
  };
}

export function EngineSettings({
  notify,
  onChanged,
  refreshToken,
}: {
  notify: Notify;
  onChanged: () => void;
  refreshToken: number;
}) {
  const [engines, setEngines] = useState<ScanEngine[]>([]);
  const [endpoints, setEndpoints] = useState<EngineEndpoint[]>([]);
  const [maxParallel, setMaxParallel] = useState(9);
  const [loading, setLoading] = useState(true);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [models, setModels] = useState<string[]>([]);

  const load = useCallback(async () => {
    try {
      const [catalog, config] = await Promise.all([
        request<{ engines: ScanEngine[]; max_parallel: number }>("/api/models"),
        request<{ endpoints: EngineEndpoint[] }>("/api/models/endpoints"),
      ]);
      setEngines(catalog.engines);
      setMaxParallel(catalog.max_parallel);
      setEndpoints(config.endpoints);
    } catch {
      // 后端未就绪时保持空列表，界面仍可打开。
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load, refreshToken]);

  const runningJobs = engines.reduce((sum, item) => sum + item.running, 0);

  const save = async () => {
    if (!draft) return;
    setBusy("save");
    try {
      const payload = {
        name: draft.name,
        base_url: draft.base_url,
        model: draft.model,
        max_concurrency: draft.max_concurrency,
        timeout_seconds: draft.timeout_seconds,
        max_output_tokens: draft.max_output_tokens,
        ...(draft.api_key ? { api_key: draft.api_key } : {}),
      };
      if (draft.id) {
        await request(`/api/models/endpoints/${draft.id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        notify("接口配置已更新", "success");
      } else {
        await request("/api/models/endpoints", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        notify("接口已添加，可以立即用它扫描", "success");
      }
      setDraft(null);
      setModels([]);
      await load();
      onChanged();
    } catch (error) {
      notify((error as Error).message, "error");
    } finally {
      setBusy(null);
    }
  };

  const discover = async () => {
    if (!draft) return;
    setBusy("discover");
    try {
      const result = await request<{ models: string[] }>("/api/models/discover", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          base_url: draft.base_url,
          api_key: draft.api_key,
        }),
      });
      setModels(result.models);
      if (result.models.length === 1) {
        setDraft({ ...draft, model: result.models[0] });
      }
      notify(`读取到 ${result.models.length} 个模型`, "success");
    } catch (error) {
      notify((error as Error).message, "error");
    } finally {
      setBusy(null);
    }
  };

  const testDraft = async () => {
    if (!draft?.id) return;
    setBusy("test-draft");
    try {
      const result = await request<{ message: string }>(
        `/api/models/endpoints/${draft.id}/test`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            base_url: draft.base_url,
            model: draft.model,
            ...(draft.api_key ? { api_key: draft.api_key } : {}),
          }),
        },
      );
      notify(result.message, "success");
    } catch (error) {
      notify((error as Error).message, "error");
    } finally {
      setBusy(null);
    }
  };

  const test = async (endpoint: EngineEndpoint) => {
    setBusy(`test-${endpoint.id}`);
    try {
      const result = await request<{ message: string }>(
        `/api/models/endpoints/${endpoint.id}/test`,
        { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" },
      );
      notify(result.message, "success");
    } catch (error) {
      notify((error as Error).message, "error");
    } finally {
      setBusy(null);
    }
  };

  const toggle = async (endpoint: EngineEndpoint) => {
    setBusy(`toggle-${endpoint.id}`);
    try {
      await request(`/api/models/endpoints/${endpoint.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: !endpoint.enabled }),
      });
      await load();
      onChanged();
    } catch (error) {
      notify((error as Error).message, "error");
    } finally {
      setBusy(null);
    }
  };

  const remove = async (endpoint: EngineEndpoint) => {
    if (!window.confirm(`删除接口“${endpoint.name}”？已经完成的任务不受影响。`)) {
      return;
    }
    setBusy(`delete-${endpoint.id}`);
    try {
      await request(`/api/models/endpoints/${endpoint.id}`, { method: "DELETE" });
      notify("接口已删除", "success");
      await load();
      onChanged();
    } catch (error) {
      notify((error as Error).message, "error");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="settings-section">
      <h3>模型接口与并行</h3>
      <div className="parallel-meter">
        <Zap size={14} />
        <span>
          正在并行 <strong>{runningJobs}</strong> / {maxParallel} 个任务
        </span>
      </div>

      <div className="engine-list">
        {engines.map((engine) => (
          <div
            className={`engine-row ${engine.enabled ? "" : "engine-row-off"}`}
            key={engine.id}
          >
            <div className="engine-row-head">
              <span className={`engine-dot dot-${engine.enabled ? "on" : "off"}`} />
              <strong>{engine.label}</strong>
              {engine.kind === "local" ? (
                <span className="engine-tag">本机 · 串行</span>
              ) : (
                <span className="engine-tag">
                  并发 {engine.max_concurrency}
                </span>
              )}
              {engine.running > 0 && (
                <span className="engine-tag engine-tag-live">
                  <LoaderCircle className="spin" size={11} /> {engine.running}
                </span>
              )}
            </div>
            <div className="engine-row-detail">{engine.detail}</div>
            {engine.kind === "remote" && (
              <div className="engine-row-actions">
                <button
                  type="button"
                  onClick={() => {
                    const endpoint = endpoints.find((item) => item.id === engine.id);
                    if (endpoint) {
                      setDraft(toDraft(endpoint));
                      setModels([]);
                    }
                  }}
                >
                  编辑
                </button>
                <button
                  type="button"
                  onClick={() => {
                    const endpoint = endpoints.find((item) => item.id === engine.id);
                    if (endpoint) void test(endpoint);
                  }}
                  disabled={busy === `test-${engine.id}`}
                >
                  {busy === `test-${engine.id}` ? "测试中…" : "测试连接"}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    const endpoint = endpoints.find((item) => item.id === engine.id);
                    if (endpoint) void toggle(endpoint);
                  }}
                  disabled={busy === `toggle-${engine.id}`}
                >
                  {engine.enabled ? "停用" : "启用"}
                </button>
                <button
                  type="button"
                  className="danger-link"
                  onClick={() => {
                    const endpoint = endpoints.find((item) => item.id === engine.id);
                    if (endpoint) void remove(endpoint);
                  }}
                  disabled={busy === `delete-${engine.id}`}
                >
                  <Trash2 size={13} /> 删除
                </button>
              </div>
            )}
          </div>
        ))}
        {!engines.length && (
          <div className="engine-empty">
            {loading ? "正在读取接口…" : "还没有可用的识别接口"}
          </div>
        )}
      </div>

      {draft ? (
        <div className="engine-form">
          <div className="engine-form-grid">
            <label>
              <span>名称</span>
              <input
                value={draft.name}
                onChange={(event) => setDraft({ ...draft, name: event.target.value })}
                placeholder="例如 4090 · Qwen3.8"
              />
            </label>
            <label>
              <span>接口地址</span>
              <input
                value={draft.base_url}
                onChange={(event) =>
                  setDraft({ ...draft, base_url: event.target.value })
                }
                placeholder="http://127.0.0.1:18091/v1"
              />
            </label>
            <label>
              <span>模型 ID</span>
              <input
                value={draft.model}
                onChange={(event) => setDraft({ ...draft, model: event.target.value })}
                placeholder="qwen3.8-flash-next-iq3_s"
                list="engine-model-options"
              />
              <datalist id="engine-model-options">
                {models.map((model) => (
                  <option key={model} value={model} />
                ))}
              </datalist>
            </label>
            <label>
              <span>API 密钥{draft.id ? "（留空保持不变）" : ""}</span>
              <input
                type="password"
                value={draft.api_key}
                onChange={(event) =>
                  setDraft({ ...draft, api_key: event.target.value })
                }
                placeholder="仅保存在这台 Mac"
                autoComplete="off"
              />
            </label>
            <label>
              <span>并发数</span>
              <input
                type="number"
                min={1}
                max={9}
                value={draft.max_concurrency}
                onChange={(event) =>
                  setDraft({
                    ...draft,
                    max_concurrency: Number(event.target.value) || 1,
                  })
                }
              />
            </label>
            <label>
              <span>超时（秒）</span>
              <input
                type="number"
                min={30}
                max={1800}
                value={draft.timeout_seconds}
                onChange={(event) =>
                  setDraft({
                    ...draft,
                    timeout_seconds: Number(event.target.value) || 600,
                  })
                }
              />
            </label>
          </div>
          <div className="engine-form-actions">
            <button
              type="button"
              className="button button-secondary"
              onClick={() => void discover()}
              disabled={busy === "discover"}
            >
              {busy === "discover" ? (
                <LoaderCircle className="spin" size={14} />
              ) : (
                <Server size={14} />
              )}
              读取模型列表
            </button>
            {draft.id && (
              <button
                type="button"
                className="button button-secondary"
                onClick={() => void testDraft()}
                disabled={busy === "test-draft"}
              >
                {busy === "test-draft" ? (
                  <LoaderCircle className="spin" size={14} />
                ) : (
                  <Zap size={14} />
                )}
                测试这个配置
              </button>
            )}
            <button
              type="button"
              className="button button-primary"
              onClick={() => void save()}
              disabled={busy === "save" || !draft.name || !draft.base_url || !draft.model}
            >
              {busy === "save" ? (
                <LoaderCircle className="spin" size={14} />
              ) : (
                <Check size={14} />
              )}
              保存接口
            </button>
            <button
              type="button"
              className="button button-ghost"
              onClick={() => {
                setDraft(null);
                setModels([]);
              }}
            >
              <X size={14} /> 取消
            </button>
          </div>
          <small className="engine-form-hint">
            接口需兼容 OpenAI <code>/chat/completions</code> 与图片输入。密钥只写入本机
            配置文件（macOS 权限 0600），不进入日志、Git 或安装包。
          </small>
        </div>
      ) : (
        <div className="engine-form-actions">
          <button
            type="button"
            className="button button-secondary"
            onClick={() => {
              setDraft({ ...EMPTY_DRAFT });
              setModels([]);
            }}
          >
            <Plus size={14} /> 添加模型接口
          </button>
        </div>
      )}

      {engines.some((engine) => engine.kind === "remote" && !engine.api_key_set) && (
        <div className="hardware-note hardware-warning">
          <CircleAlert size={14} />
          <span>有接口尚未填写 API 密钥；如果服务端需要鉴权，扫描会返回 401。</span>
        </div>
      )}
    </div>
  );
}
