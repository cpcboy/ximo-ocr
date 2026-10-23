export const ENGINE_API_BASE = "http://127.0.0.1:18765";

export type ScanEngine = {
  id: string;
  label: string;
  kind: "local" | "remote";
  enabled: boolean;
  max_concurrency: number;
  running: number;
  state: string;
  detail?: string;
  model?: string;
  base_url?: string;
  api_key_set?: boolean;
  preset?: boolean;
  platform?: string;
};

export type EngineEndpoint = {
  id: string;
  name: string;
  base_url: string;
  model: string;
  max_concurrency: number;
  timeout_seconds: number;
  max_output_tokens: number;
  enabled: boolean;
  preset: boolean;
  api_key_set: boolean;
};

export const LOCAL_ENGINE_ID = "local";
export const AUTO_ENGINE_ID = "auto";

/** 自动分配只使用可用引擎；优先选择空闲槽位最多的引擎，负载相同则轮转。 */
export function pickEngine(
  engines: ScanEngine[],
  cursor: number,
): { engineId: string; nextCursor: number } {
  const usable = engines.filter(
    (engine) => engine.enabled && engine.running < engine.max_concurrency,
  );
  const pool = usable.length
    ? usable
    : engines.filter((engine) => engine.enabled);
  if (!pool.length) return { engineId: LOCAL_ENGINE_ID, nextCursor: cursor };
  const start = cursor % pool.length;
  let best = pool[start];
  for (let offset = 0; offset < pool.length; offset += 1) {
    const candidate = pool[(start + offset) % pool.length];
    const bestRoom = best.max_concurrency - best.running;
    const room = candidate.max_concurrency - candidate.running;
    if (room > bestRoom) best = candidate;
  }
  const index = pool.indexOf(best);
  return { engineId: best.id, nextCursor: (start + index + 1) % pool.length };
}

export function engineShortLabel(engine: ScanEngine | undefined): string {
  if (!engine) return "";
  if (engine.kind === "local") return "本机";
  return engine.label.replace(/\s*·.*$/, "") || engine.label;
}
