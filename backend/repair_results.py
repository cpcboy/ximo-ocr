from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .repetition import trim_repetitive_tail


def repair_result_file(
    source_json: Path,
    output_dir: Path,
) -> dict[str, Any]:
    source = json.loads(source_json.read_text(encoding="utf-8"))
    repaired = copy.deepcopy(source)
    changes: list[dict[str, Any]] = []

    for page in repaired.get("pages", []):
        original = str(page.get("text") or "")
        result = trim_repetitive_tail(original)
        if not result.finding.detected:
            continue
        page_number = int(page.get("index") or 0) + 1
        page["text"] = result.text
        page["repetition_trimmed"] = True
        page["repetition_repair"] = result.finding.as_dict()
        changes.append(
            {
                "page": page_number,
                "label": page.get("label"),
                "original_chars": len(original),
                "repaired_chars": len(result.text),
                "removed_chars": result.finding.removed_chars,
                "duplicate_ratio": round(
                    result.finding.duplicate_ratio,
                    4,
                ),
                "max_occurrences": result.finding.max_occurrences,
                "phrase_preview": result.finding.phrase_preview,
            }
        )

    generated_at = datetime.now(timezone.utc).isoformat()
    report = {
        "source": str(source_json),
        "generated_at": generated_at,
        "changed_pages": len(changes),
        "unchanged_pages": len(repaired.get("pages", [])) - len(changes),
        "removed_chars": sum(item["removed_chars"] for item in changes),
        "pages": changes,
        "note": (
            "原始结果未被覆盖。本目录自动去除了重复尾巴；"
            "如果模型在读完页面前就进入循环，清理后的该页仍可能缺少后续内容，"
            "应使用已修复的引擎重新识别该页。"
        ),
    }
    repaired["repair"] = report

    output_dir.mkdir(parents=True, exist_ok=False)
    stem = source_json.stem
    (output_dir / f"{stem}.json").write_text(
        json.dumps(repaired, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    text_sections: list[str] = []
    markdown_sections: list[str] = []
    for page in repaired.get("pages", []):
        page_number = int(page.get("index") or 0) + 1
        label = str(page.get("label") or f"第 {page_number} 页")
        text = str(page.get("text") or "").strip()
        notice = ""
        if page.get("repetition_trimmed"):
            notice = "[本页已自动清理重复尾巴；如内容不完整，请重新识别本页]\n"
        text_sections.append(f"===== {label} =====\n{notice}{text}")
        markdown_notice = ""
        if page.get("repetition_trimmed"):
            markdown_notice = (
                "> 本页已自动清理重复尾巴；如内容不完整，请重新识别本页。\n\n"
            )
        markdown_sections.append(
            f"## {label}\n\n{markdown_notice}{text}"
        )

    (output_dir / f"{stem}.txt").write_text(
        "\n\n".join(text_sections).strip() + "\n",
        encoding="utf-8",
    )
    (output_dir / f"{stem}.md").write_text(
        f"# {stem} - 去重修复版\n\n"
        + "\n\n---\n\n".join(markdown_sections).strip()
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "修复报告.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="为 Unlimited OCR JSON 结果生成不覆盖原件的去重修复版"
    )
    parser.add_argument("source_json", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    report = repair_result_file(args.source_json, args.output_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
