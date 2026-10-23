"""OpenAI 兼容模型接口的本地配置存储。

本模块只管理“识别引擎接口”这类应用配置，不接触扫描原件、识别结果或阅读笔记。
接口密钥只在本机配置文件内以 0600 权限保存，读写接口对外只返回是否已配置，
不会把明文密钥写入日志、API 响应或 Git。
"""

from __future__ import annotations

import json
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

LOCAL_ENGINE_ID = "local"
LOCAL_ENGINE_LABEL = "本机 MLX"

# 每个远程接口默认并发；用户可在界面按接口调整。
DEFAULT_ENDPOINT_CONCURRENCY = 3
MAX_ENDPOINT_CONCURRENCY = 9
# 同时运行的文档任务上限（跨引擎）。
GLOBAL_MAX_PARALLEL = 9
# 本机 MLX 只有一个推理实例，固定串行。
LOCAL_MAX_CONCURRENCY = 1

DEFAULT_TIMEOUT_SECONDS = 600
MIN_TIMEOUT_SECONDS = 30
MAX_TIMEOUT_SECONDS = 1800
DEFAULT_MAX_OUTPUT_TOKENS = 16384
MIN_OUTPUT_TOKENS = 512
MAX_OUTPUT_TOKENS = 24576

ENDPOINT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

PRESET_ENDPOINTS: tuple[dict[str, Any], ...] = (
    {
        "id": "preset-3090ti",
        "name": "3090 Ti · Qwen3.8 Flash",
        "base_url": "http://127.0.0.1:18081/v1",
        "model": "qwen3.8-flash-next-iq3_s",
        "max_concurrency": 1,
        "timeout_seconds": 600,
        "max_output_tokens": 16384,
    },
    {
        "id": "preset-4090",
        "name": "4090 · Qwen3.8 Flash",
        "base_url": "http://127.0.0.1:18091/v1",
        "model": "qwen3.8-flash-next-iq3_s",
        "max_concurrency": 1,
        "timeout_seconds": 600,
        "max_output_tokens": 16384,
    },
)


class EndpointValidationError(ValueError):
    """配置字段不合法；API 层转换为 422。"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_text(value: Any, *, field: str, maximum: int) -> str:
    text = str(value or "").strip()
    if not text:
        raise EndpointValidationError(f"{field}不能为空")
    if len(text) > maximum:
        raise EndpointValidationError(f"{field}超过 {maximum} 个字符上限")
    return text


def _clamp_int(
    value: Any,
    *,
    field: str,
    minimum: int,
    maximum: int,
    default: int,
) -> int:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        raise EndpointValidationError(f"{field}必须是整数")
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise EndpointValidationError(f"{field}必须是整数") from exc
    if number < minimum or number > maximum:
        raise EndpointValidationError(f"{field}必须在 {minimum} 到 {maximum} 之间")
    return number


def normalize_base_url(value: Any) -> str:
    text = _clean_text(value, field="接口地址", maximum=500).rstrip("/")
    parts = urlsplit(text)
    if parts.scheme not in {"http", "https"}:
        raise EndpointValidationError("接口地址必须以 http:// 或 https:// 开头")
    if not parts.netloc:
        raise EndpointValidationError("接口地址缺少主机名")
    if parts.query or parts.fragment:
        raise EndpointValidationError("接口地址不能包含查询参数或锚点")
    return text


def is_loopback_url(url: str) -> bool:
    host = urlsplit(url).hostname or ""
    return host in {"127.0.0.1", "localhost", "::1"}


class ModelEndpointRegistry:
    """线程安全的接口配置读写，文件变更立即落盘。"""

    def __init__(self, config_path: Path):
        self._path = Path(config_path)
        self._lock = threading.RLock()
        self._endpoints: list[dict[str, Any]] = []
        self._load()

    # ---- 读取 -------------------------------------------------------------

    @property
    def path(self) -> Path:
        return self._path

    def _load(self) -> None:
        with self._lock:
            if not self._path.exists():
                # 预设只在内存中提供；用户首次改动时才落盘，避免只读场景写文件。
                self._endpoints = [
                    self._normalize({**preset, "api_key": "", "enabled": True, "preset": True})
                    for preset in PRESET_ENDPOINTS
                ]
                return
            try:
                raw = json.loads(self._path.read_text("utf-8"))
            except (OSError, ValueError):
                # 配置损坏时退回空列表，不覆盖原文件，等用户重新添加。
                self._endpoints = []
                return
            endpoints: list[dict[str, Any]] = []
            for item in raw.get("endpoints", []):
                try:
                    endpoint = self._normalize(item)
                except EndpointValidationError:
                    continue
                endpoints.append(endpoint)
            self._endpoints = endpoints

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "endpoints": self._endpoints,
        }
        temporary = self._path.with_suffix(self._path.suffix + ".tmp")
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
            0o600,
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, self._path)
        try:
            os.chmod(self._path, 0o600)
        except OSError:
            pass

    def _normalize(self, item: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(item, dict):
            raise EndpointValidationError("接口配置格式不正确")
        raw_id = str(item.get("id") or "").strip()
        if raw_id and not ENDPOINT_ID_PATTERN.fullmatch(raw_id):
            raise EndpointValidationError("接口 ID 只能包含字母、数字、下划线和短横线")
        endpoint = {
            "id": raw_id or f"ep-{uuid.uuid4().hex[:10]}",
            "name": _clean_text(item.get("name"), field="名称", maximum=60),
            "base_url": normalize_base_url(item.get("base_url")),
            "model": _clean_text(item.get("model"), field="模型 ID", maximum=160),
            "api_key": str(item.get("api_key") or "").strip(),
            "max_concurrency": _clamp_int(
                item.get("max_concurrency"),
                field="并发数",
                minimum=1,
                maximum=MAX_ENDPOINT_CONCURRENCY,
                default=DEFAULT_ENDPOINT_CONCURRENCY,
            ),
            "timeout_seconds": _clamp_int(
                item.get("timeout_seconds"),
                field="超时时间",
                minimum=MIN_TIMEOUT_SECONDS,
                maximum=MAX_TIMEOUT_SECONDS,
                default=DEFAULT_TIMEOUT_SECONDS,
            ),
            "max_output_tokens": _clamp_int(
                item.get("max_output_tokens"),
                field="最大输出",
                minimum=MIN_OUTPUT_TOKENS,
                maximum=MAX_OUTPUT_TOKENS,
                default=DEFAULT_MAX_OUTPUT_TOKENS,
            ),
            "enabled": bool(item.get("enabled", True)),
            "preset": bool(item.get("preset", False)),
            "created_at": str(item.get("created_at") or utc_now()),
            "updated_at": utc_now(),
        }
        if len(endpoint["api_key"]) > 4096:
            raise EndpointValidationError("密钥过长")
        return endpoint

    def list(self, *, only_enabled: bool = False) -> list[dict[str, Any]]:
        with self._lock:
            items = [dict(endpoint) for endpoint in self._endpoints]
        if only_enabled:
            items = [endpoint for endpoint in items if endpoint["enabled"]]
        return items

    def get(self, endpoint_id: str) -> dict[str, Any] | None:
        with self._lock:
            for endpoint in self._endpoints:
                if endpoint["id"] == endpoint_id:
                    return dict(endpoint)
        return None

    def public_list(self) -> list[dict[str, Any]]:
        return [public_endpoint(endpoint) for endpoint in self.list()]

    # ---- 写入 -------------------------------------------------------------

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            endpoint = self._normalize({**payload, "id": ""})
            if any(item["name"] == endpoint["name"] for item in self._endpoints):
                raise EndpointValidationError("已有同名接口，请换一个名称")
            self._endpoints.append(endpoint)
            self._save()
            return dict(endpoint)

    def update(self, endpoint_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            index = self._next_index(endpoint_id)
            current = self._endpoints[index]
            merged = {**current, **payload, "id": endpoint_id}
            if "api_key" not in payload:
                merged["api_key"] = current["api_key"]
            elif payload.get("api_key") == KEEP_KEY_SENTINEL:
                merged["api_key"] = current["api_key"]
            endpoint = self._normalize(merged)
            for other in self._endpoints:
                if other["id"] != endpoint_id and other["name"] == endpoint["name"]:
                    raise EndpointValidationError("已有同名接口，请换一个名称")
            self._endpoints[index] = endpoint
            self._save()
            return dict(endpoint)

    def delete(self, endpoint_id: str) -> None:
        with self._lock:
            index = self._next_index(endpoint_id)
            del self._endpoints[index]
            self._save()

    def _next_index(self, endpoint_id: str) -> int:
        for index, endpoint in enumerate(self._endpoints):
            if endpoint["id"] == endpoint_id:
                return index
        raise KeyError(endpoint_id)


# 前端编辑已有接口时回传该值表示“保持原密钥不变”。
KEEP_KEY_SENTINEL = "__keep__"


def public_endpoint(endpoint: dict[str, Any]) -> dict[str, Any]:
    """去掉明文密钥，只暴露是否已配置。"""
    return {
        key: value
        for key, value in endpoint.items()
        if key != "api_key"
    } | {"api_key_set": bool(endpoint.get("api_key"))}
