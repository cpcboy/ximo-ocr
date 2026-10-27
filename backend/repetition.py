from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from typing import Sequence


TAG_OR_ENTITY_RE = re.compile(
    r"<[^>]*>|&(?:#[xX][0-9A-Fa-f]+|#[0-9]+|[A-Za-z][A-Za-z0-9]+);"
)
WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['’][A-Za-z]+)?")
HTML_TAG_RE = re.compile(r"<\s*(/?)\s*([A-Za-z0-9]+)(?:\s[^>]*)?>")
STRUCTURAL_TAGS = {
    "table",
    "thead",
    "tbody",
    "tfoot",
    "tr",
    "th",
    "td",
    "ul",
    "ol",
    "li",
    "p",
    "div",
    "blockquote",
}
VOID_TAGS = {"br", "hr", "img", "input", "meta", "link", "source"}


@dataclass(frozen=True)
class RepetitionFinding:
    detected: bool = False
    cutoff: int | None = None
    max_occurrences: int = 0
    duplicate_ratio: float = 0.0
    ngram_size: int = 12
    phrase_preview: str = ""
    removed_chars: int = 0
    passes: int = 0
    reason: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "detected": self.detected,
            "cutoff": self.cutoff,
            "max_occurrences": self.max_occurrences,
            "duplicate_ratio": round(self.duplicate_ratio, 4),
            "ngram_size": self.ngram_size,
            "phrase_preview": self.phrase_preview,
            "removed_chars": self.removed_chars,
            "passes": self.passes,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class TrimmedText:
    text: str
    finding: RepetitionFinding


def _masked_text(value: str) -> str:
    return TAG_OR_ENTITY_RE.sub(
        lambda match: " " * (match.end() - match.start()),
        value,
    )


def _canonical_words(value: str, *, preserve_numbers: bool = False) -> list[tuple[str, int, int]]:
    words: list[tuple[str, int, int]] = []
    for match in WORD_RE.finditer(_masked_text(value)):
        token = match.group(0).lower()
        if not preserve_numbers and any(character.isdigit() for character in token):
            token = "#"
        words.append((token, match.start(), match.end()))
    return words


def _dense_runs(
    positions: list[int],
    *,
    max_gap: int,
) -> list[list[int]]:
    if not positions:
        return []
    runs = [[positions[0]]]
    for position in positions[1:]:
        if position - runs[-1][-1] <= max_gap:
            runs[-1].append(position)
        else:
            runs.append([position])
    return runs


def _snap_cutoff_to_boundary(value: str, cutoff: int) -> int:
    start = max(0, cutoff - 320)
    window = value[start:cutoff]
    candidates: list[int] = []
    newline = window.rfind("\n")
    if newline >= 0:
        candidates.append(start + newline + 1)
    for marker in ("<tr", "<p", "<li", "<div", "<table"):
        position = window.lower().rfind(marker)
        if position >= 0:
            candidates.append(start + position)
    if not candidates:
        return cutoff
    snapped = max(candidates)
    return snapped if cutoff - snapped <= 320 else cutoff


def analyze_repetitive_tail(
    value: str,
    *,
    ngram_size: int = 12,
    tail_words: int = 1200,
    preserve_numbers: bool = False,
) -> RepetitionFinding:
    if preserve_numbers:
        # V2: do not cut a whole record because a short template inside it
        # repeats. The entire candidate tail must be exact repeated cycles,
        # including numbers, punctuation, CJK and HTML (whitespace aside).
        tokens = list(re.finditer(r"\S+", value))
        values = [token.group() for token in tokens]
        loop = find_exact_token_loop(values)
        if not loop:
            return RepetitionFinding()
        start, period = loop["start"], loop["period"]
        block = values[start:start + period]
        while start >= period and values[start - period:start] == block:
            start -= period
        cutoff = tokens[start + period].start()
        return RepetitionFinding(
            detected=True, cutoff=cutoff, max_occurrences=(len(tokens) - start) // period,
            duplicate_ratio=(len(tokens) - start - period) / len(tokens),
            ngram_size=period, phrase_preview=" ".join(block)[:180],
            reason="检测到完整重复周期（保留数字和标点差异）",
        )
    words = _canonical_words(value, preserve_numbers=preserve_numbers)
    if len(words) < 120:
        return RepetitionFinding(ngram_size=ngram_size)

    normalized = [word[0] for word in words]
    tail_start = max(0, len(normalized) - tail_words)
    positions_by_gram: dict[tuple[str, ...], list[int]] = defaultdict(list)
    for index in range(tail_start, len(normalized) - ngram_size + 1):
        gram = tuple(normalized[index : index + ngram_size])
        positions_by_gram[gram].append(index)

    counts = Counter(
        {
            gram: len(positions)
            for gram, positions in positions_by_gram.items()
        }
    )
    total_grams = max(1, len(normalized) - tail_start - ngram_size + 1)
    duplicate_grams = sum(count - 1 for count in counts.values() if count > 1)
    duplicate_ratio = duplicate_grams / total_grams
    max_occurrences = max(counts.values(), default=0)

    detected = (
        (max_occurrences >= 6 and duplicate_ratio >= 0.08)
        or (max_occurrences >= 4 and duplicate_ratio >= 0.22)
        or duplicate_ratio >= 0.48
    )
    if not detected:
        return RepetitionFinding(
            max_occurrences=max_occurrences,
            duplicate_ratio=duplicate_ratio,
            ngram_size=ngram_size,
        )

    best: tuple[int, int, tuple[str, ...], list[int]] | None = None
    latest_useful_position = len(normalized) - max(80, ngram_size * 6)
    for gram, positions in positions_by_gram.items():
        if len(positions) < 4:
            continue
        for run in _dense_runs(positions, max_gap=220):
            if len(run) < 4:
                continue
            if run[-1] < latest_useful_position:
                continue
            score = (len(run), run[-1])
            if best is None or score > best[:2]:
                best = (score[0], score[1], gram, run)

    if best is None:
        return RepetitionFinding(
            max_occurrences=max_occurrences,
            duplicate_ratio=duplicate_ratio,
            ngram_size=ngram_size,
        )

    _, _, gram, run = best
    first, second = run[0], run[1]
    period = max(1, second - first)
    backward_match = 0
    while (
        backward_match < period
        and first - backward_match - 1 >= 0
        and normalized[first - backward_match - 1]
        == normalized[second - backward_match - 1]
    ):
        backward_match += 1

    cutoff_word = max(0, second - backward_match)
    if cutoff_word < 2 or cutoff_word >= len(words):
        return RepetitionFinding(
            max_occurrences=max_occurrences,
            duplicate_ratio=duplicate_ratio,
            ngram_size=ngram_size,
        )

    cutoff = _snap_cutoff_to_boundary(value, words[cutoff_word][1])
    return RepetitionFinding(
        detected=True,
        cutoff=cutoff,
        max_occurrences=max_occurrences,
        duplicate_ratio=duplicate_ratio,
        ngram_size=ngram_size,
        phrase_preview=" ".join(gram)[:180],
        reason="检测到重复词句（已保留数字差异）" if preserve_numbers else "检测到长句或编号变化后的重复循环",
    )


def _close_open_structural_tags(value: str) -> str:
    stack: list[str] = []
    for match in HTML_TAG_RE.finditer(value):
        closing = bool(match.group(1))
        tag = match.group(2).lower()
        if tag not in STRUCTURAL_TAGS or tag in VOID_TAGS:
            continue
        if closing:
            if tag in stack:
                while stack:
                    current = stack.pop()
                    if current == tag:
                        break
        elif not match.group(0).rstrip().endswith("/>"):
            stack.append(tag)
    if not stack:
        return value
    return value + "".join(f"</{tag}>" for tag in reversed(stack))


def trim_repetitive_tail(value: str, *, preserve_numbers: bool = False) -> TrimmedText:
    current = value
    findings: list[RepetitionFinding] = []
    last_finding = RepetitionFinding()
    for _ in range(8):
        finding = analyze_repetitive_tail(current, preserve_numbers=preserve_numbers)
        last_finding = finding
        if not finding.detected or finding.cutoff is None:
            break
        candidate = current[: finding.cutoff].rstrip()
        if len(current) - len(candidate) < 80:
            break
        findings.append(finding)
        current = candidate

    if not findings:
        return TrimmedText(value, last_finding)

    trimmed = _close_open_structural_tags(current)
    removed_chars = max(0, len(value) - len(trimmed))
    primary = findings[0]
    return TrimmedText(
        trimmed,
        replace(
            primary,
            cutoff=len(trimmed),
            max_occurrences=max(item.max_occurrences for item in findings),
            duplicate_ratio=max(item.duplicate_ratio for item in findings),
            removed_chars=removed_chars,
            passes=len(findings),
            reason=f"检测并清理了 {len(findings)} 段重复循环",
        ),
    )


def find_exact_token_loop(
    token_ids: Sequence[int | str],
    *,
    max_period: int = 192,
    minimum_span: int = 96,
) -> dict[str, int] | None:
    length = len(token_ids)
    if length < minimum_span:
        return None

    for period in range(1, min(max_period, length // 3) + 1):
        repeats = max(3, math.ceil(minimum_span / period))
        span = repeats * period
        if span > length:
            continue
        block = token_ids[length - period : length]
        if all(
            token_ids[length - (offset + 1) * period : length - offset * period]
            == block
            for offset in range(1, repeats)
        ):
            return {
                "start": length - span,
                "period": period,
                "repeats": repeats,
            }
    return None
