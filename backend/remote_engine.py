"""通过 OpenAI 兼容接口调用视觉模型做逐页 OCR。

设计约束：
- 只发送当前页图像与提示词，不发送其他页、任务元数据或阅读笔记。
- 只有回环地址才强制绕过系统代理，远程地址沿用系统网络设置。
- 失败信息区分鉴权、超时、限流和服务端错误，便于界面给出可操作提示。
"""

from __future__ import annotations

import base64
import json
import re
import socket
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .model_registry import is_loopback_url

DEFAULT_OCR_PROMPT = "document parsing."

# 远程视觉模型不认识 "document parsing." 这种原生指令，统一换成结构化转写要求，
# 输出与本地模型一致：纯文本 + HTML 表格，便于前端已有的安全渲染链路复用。
STRUCTURED_OCR_PROMPT = (
    "你是文档 OCR 引擎。请逐行完整转写图片中的文字，保持原始阅读顺序与段落分隔。"
    "表格用 HTML <table> 表示，保留合并单元格；公式和编号保留原样符号。"
    "不要解释、不要总结、不要添加代码块围栏，只输出转写内容。"
)

_FENCE_PATTERN = re.compile(
    r"^\s*```[A-Za-z0-9_-]*\s*\n(?P<body>.*?)\n?\s*```\s*$",
    re.DOTALL,
)
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class RemoteEngineError(RuntimeError):
    """远程接口调用失败，message 直接用于界面展示。"""

    def __init__(self, message: str, *, status: int | None = None):
        super().__init__(message)
        self.status = status


def _auth_headers(api_key: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _opener(url: str) -> urllib.request.OpenerDirector:
    if is_loopback_url(url):
        return urllib.request.build_opener(urllib.request.ProxyHandler({}))
    return urllib.request.build_opener()


def _describe_http_error(error: urllib.error.HTTPError) -> str:
    detail = ""
    try:
        raw = error.read().decode("utf-8", "replace")
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            payload = parsed.get("error")
            if isinstance(payload, dict):
                detail = str(payload.get("message") or "")
            elif isinstance(payload, str):
                detail = payload
            detail = detail or str(parsed.get("detail") or "")
    except Exception:
        detail = ""
    detail = detail.strip()[:300]
    if error.code in {401, 403}:
        base = "接口拒绝了访问，请检查 API 密钥是否正确"
    elif error.code == 404:
        base = "接口地址或模型不存在，请检查 Base URL（通常以 /v1 结尾）和模型 ID"
    elif error.code == 429:
        base = "接口限流或并发已满，请稍后重试或降低并发"
    elif error.code >= 500:
        base = "模型服务暂时不可用"
    else:
        base = "接口返回错误"
    return f"{base}（HTTP {error.code}）" + (f"：{detail}" if detail else "")


def _extract_message(payload: dict[str, Any]) -> tuple[str, dict[str, Any], str]:
    choices = payload.get("choices") or []
    if not choices:
        raise RemoteEngineError("接口没有返回识别结果（choices 为空）")
    choice = choices[0] or {}
    message = choice.get("message") or {}
    content = message.get("content")
    if isinstance(content, list):
        parts = [
            str(part.get("text") or "")
            for part in content
            if isinstance(part, dict) and part.get("type") in {None, "text"}
        ]
        content = "".join(parts)
    text = str(content or "").strip()
    if not text:
        reason = ""
        if choice.get("finish_reason") == "length":
            reason = "输出长度达到上限，请提高“最长输出”或减少单页内容"
        raise RemoteEngineError(reason or "接口返回了空内容")
    return text, dict(payload.get("usage") or {}), str(choice.get("finish_reason") or "")


def _clean_result(text: str) -> str:
    cleaned = text.replace("\x00", "").strip()
    fenced = _FENCE_PATTERN.match(cleaned)
    if fenced:
        cleaned = fenced.group("body").strip()
    if "Assistant:" in cleaned:
        cleaned = cleaned.rsplit("Assistant:", 1)[-1].strip()
    return cleaned


def build_prompt(prompt: str) -> str:
    requested = (prompt or "").strip()
    if not requested or requested.lower() in {
        DEFAULT_OCR_PROMPT,
        "document parsing",
        "document parsing.",
    }:
        return STRUCTURED_OCR_PROMPT
    return requested


def image_data_url(image_path: Path) -> str:
    raw = image_path.read_bytes()
    suffix = image_path.suffix.lower().lstrip(".") or "png"
    mime = "image/jpeg" if suffix in {"jpg", "jpeg"} else f"image/{suffix}"
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"


class RemoteEngine:
    """单个接口的调用封装；并发由调度器统一控制。"""

    def __init__(self, endpoint: dict[str, Any]):
        self.endpoint = dict(endpoint)

    @property
    def id(self) -> str:
        return str(self.endpoint.get("id") or "")

    @property
    def label(self) -> str:
        return str(self.endpoint.get("name") or self.id)

    def _request(
        self,
        path: str,
        body: dict[str, Any] | None,
        *,
        timeout: float,
        retries: int = 2,
    ) -> dict[str, Any]:
        url = f"{str(self.endpoint['base_url']).rstrip('/')}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = _auth_headers(str(self.endpoint.get("api_key") or ""))
        opener = _opener(url)
        last_error = "未知错误"
        for attempt in range(retries + 1):
            request = urllib.request.Request(
                url,
                data=data,
                headers=headers,
                method="POST" if body is not None else "GET",
            )
            try:
                with opener.open(request, timeout=timeout) as response:
                    raw = response.read().decode("utf-8", "replace")
                payload = json.loads(raw)
                if not isinstance(payload, dict):
                    raise RemoteEngineError("接口返回了无法解析的内容")
                return payload
            except urllib.error.HTTPError as error:
                message = _describe_http_error(error)
                if error.code not in _RETRYABLE_STATUS or attempt >= retries:
                    raise RemoteEngineError(message, status=error.code) from error
                last_error = message
            except (urllib.error.URLError, socket.timeout, TimeoutError) as error:
                reason = getattr(error, "reason", error)
                last_error = f"连接模型接口失败：{reason}"
                if attempt >= retries:
                    raise RemoteEngineError(last_error) from error
            except json.JSONDecodeError as error:
                raise RemoteEngineError("接口返回的不是合法 JSON") from error
            time.sleep(2 * (attempt + 1))
        raise RemoteEngineError(last_error)

    def scan(
        self,
        image_path: Path,
        *,
        prompt: str,
        max_length: int,
        mode: str = "precision",
    ) -> tuple[str, dict[str, Any]]:
        budget = int(max_length or 0)
        if budget <= 0:
            budget = int(self.endpoint.get("max_output_tokens") or 8192)
        budget = min(
            budget,
            int(self.endpoint.get("max_output_tokens") or DEFAULT_MAX_OUTPUT_TOKENS),
        )
        body = {
            "model": self.endpoint["model"],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": build_prompt(prompt)},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_data_url(image_path)},
                        },
                    ],
                }
            ],
            "max_tokens": max(512, budget),
            "temperature": 0.0,
            "stream": False,
        }
        payload = self._request(
            "/chat/completions",
            body,
            timeout=float(self.endpoint.get("timeout_seconds") or 600),
        )
        text, usage, finish_reason = _extract_message(payload)
        if finish_reason == "length":
            usage = {**usage, "truncated": True}
        return _clean_result(text), usage

    def list_models(self, *, timeout: float = 15.0) -> list[str]:
        payload = self._request("/models", None, timeout=timeout, retries=0)
        items = payload.get("data") or []
        models = [
            str(item.get("id"))
            for item in items
            if isinstance(item, dict) and item.get("id")
        ]
        return models


def probe_models(
    base_url: str,
    api_key: str,
    *,
    timeout: float = 15.0,
) -> list[str]:
    """在保存前探测某个接口可用模型，密钥只在内存中使用。"""
    endpoint = {
        "id": "probe",
        "name": "probe",
        "base_url": base_url,
        "model": "probe",
        "api_key": api_key,
    }
    return RemoteEngine(endpoint).list_models(timeout=timeout)
