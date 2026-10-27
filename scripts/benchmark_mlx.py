"""Opt-in local OCR benchmark. Never downloads models or opens production jobs.

Use an explicit model directory and a new output directory. Synthetic fixtures
and raw token IDs are kept only in that output directory for paired comparison.
Run with the shipped Python/MLX runtime and PYTHONDONTWRITEBYTECODE=1.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class RuntimeMethods:
    """Restore temporary benchmark hooks even when a quality gate fails."""

    def __init__(self, model_class):
        self.model_class = model_class
        self.generate = model_class.generate

    def restore(self) -> None:
        self.model_class.generate = self.generate


def instrument_generate(source: str, namespace: dict, observer):
    """Observe after the existing blocking item(), without evaluating extra ops."""
    tree = ast.parse(source)
    generate = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "generate")
    loop = next(n for n in ast.walk(generate) if isinstance(n, ast.For) and isinstance(n.target, ast.Name) and n.target.id == "step")
    index = next(i for i, n in enumerate(loop.body) if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "token_id")
    hook = ast.parse("if step == 0:\n    _benchmark_observe_prefill()\n").body[0]
    loop.body.insert(index + 1, hook)
    module = ast.fix_missing_locations(ast.Module(body=[generate], type_ignores=[]))
    scope = dict(namespace, _benchmark_observe_prefill=observer)
    exec(compile(module, "<benchmark-generate>", "exec"), scope)
    return scope["generate"]


def make_samples(directory: Path) -> list[Path]:
    from PIL import Image, ImageDraw, ImageFont

    font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"
    font = ImageFont.truetype(font_path, 30)
    small = ImageFont.truetype(font_path, 24)
    samples = []
    for name, lines in (
        ("paragraph", ["MOXI OCR QUALITY CHECK", "A quiet library opens at 09:30 every morning.",
                       "The reader borrowed three books on October 22.",
                       "Keep punctuation, numbers and line breaks intact.",
                       "Reference: AB-2048 / Total: $123.45"]),
        ("table", ["INVOICE - SYNTHETIC TEST", "Item                 Quantity             Price",
                   "Blue notebook        3                    12.50",
                   "Black pen            8                     2.25",
                   "Subtotal                                  55.50",
                   "Tax                                        5.55",
                   "Total                                     61.05"]),
        ("layout", ["GRAMMAR AND VOCABULARY", "1. If I had more time, I would learn French.",
                    "2. She has lived here since 2010.", "3. We used to walk to school.",
                    "Symbols: (a + b) = 12; 25% of 80 = 20.",
                    "Do not omit this final sentence."]),
    ):
        picture = Image.new("RGB", (900, 1000), "white")
        draw = ImageDraw.Draw(picture)
        for i, line in enumerate(lines):
            draw.text((45, 60 + i * 85), line, font=font if i == 0 else small, fill="black")
        path = directory / f"{name}.png"
        picture.save(path)
        samples.append(path)
    cjk_font = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 22)
    picture = Image.new("RGB", (600, 600), "white")
    draw = ImageDraw.Draw(picture)
    for i, line in enumerate(["墨析 OCR 测试 / Quality Test", "中文与 English 混合排版。", "日期：2026年10月22日", "金额：￥123.45；数量：8件", "标点：（括号）、引号和百分比 25%。"]):
        draw.text((20, 40 + i * 80), line, font=cjk_font, fill="black")
    path = directory / "mixed-small.png"
    picture.save(path)
    samples.append(path)
    picture = Image.new("RGB", (1100, 1400), "white")
    draw = ImageDraw.Draw(picture)
    draw.text((40, 35), "TABLE AND TWO COLUMNS", font=font, fill="black")
    for y in range(140, 501, 90):
        draw.line((40, y, 1040, y), fill="black", width=2)
    for x in (40, 430, 730, 1040):
        draw.line((x, 140, x, 500), fill="black", width=2)
    for i, row in enumerate([("Item", "Count", "Price"), ("Notebook", "3", "12.50"), ("Pen", "8", "2.25"), ("Total", "11", "55.50")]):
        for x, value in zip((55, 445, 745), row):
            draw.text((x, 165 + i * 90), value, font=small, fill="black")
    for i in range(6):
        draw.text((40, 600 + i * 85), f"Left {i+1}: Read every line.", font=small, fill="black")
        draw.text((570, 600 + i * 85), f"Right {i+1}: Preserve order.", font=small, fill="black")
    path = directory / "grid-columns.png"
    picture.save(path)
    samples.append(path)
    return samples


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--samples", nargs="+", help="Fixture stems; default is all five")
    parser.add_argument("--reference", action="store_true", help="Run the baseline generation method only")
    parser.add_argument("--reference-commit", help="Explicit pre-optimization Git commit for reference generation")
    parser.add_argument("--paired", action="store_true", help="Alternate reference/optimized order using the same loaded model")
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    if args.reference and args.paired:
        parser.error("Choose --reference or --paired, not both")
    if (args.reference or args.paired) and not args.reference_commit:
        parser.error("Reference comparisons require --reference-commit")
    args.output.mkdir(parents=True, exist_ok=False)

    import importlib.metadata
    import mlx.core as mx
    # This historical benchmark measures the v1 compatibility/cache patch only.
    from backend.engine import LegacyMLXEngine as ModelEngine
    from backend.model_catalog import CATALOG_DIR, model_verified
    legacy_spec = json.loads((CATALOG_DIR / "mlx-v1.json").read_text())

    if not model_verified(args.model_dir, legacy_spec):
        raise RuntimeError("Benchmark requires an already verified local MLX model")
    samples = make_samples(args.output)
    if args.samples:
        unknown = set(args.samples) - {p.stem for p in samples}
        if unknown:
            parser.error(f"Unknown samples: {sorted(unknown)}")
        samples = [p for p in samples if p.stem in args.samples]
    engine = ModelEngine(args.model_dir)
    root = Path(__file__).resolve().parents[1]
    from backend import model_compat
    candidate_source = (root / "backend/model_compat.py").read_text()
    reference_source = subprocess.check_output(["git", "-C", str(root), "show", f"{args.reference_commit}:backend/model_compat.py"], text=True) if args.reference_commit else candidate_source
    report = {"mlx": importlib.metadata.version("mlx"), "device": str(mx.default_device()),
              "macos": platform.mac_ver()[0], "machine": platform.machine(),
              "chip": subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True).strip(),
              "source_commit": subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip(),
              "source_sha256": {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__).resolve(), root / "backend/model_compat.py", root / "backend/mlx_performance.py", root / "backend/engine.py", root / "backend/legacy_mlx_engine.py", CATALOG_DIR / "mlx-v1.json"]},
              "model_revision": legacy_spec["revision"], "reference": args.reference,
              "reference_commit": args.reference_commit,
              "reference_source_sha256": hashlib.sha256(reference_source.encode()).hexdigest(),
              "allocator_start": "cache cleared before each timed scan; same loaded model",
              "mode": "precise", "max_length": 32768, "runs": [],
              "status": "running", "quality_gate_passed": False}
    methods = None
    try:
        started = time.perf_counter()
        engine.load()
        mx.synchronize()
        report["load_seconds"] = time.perf_counter() - started
        runner = engine._runner
        methods = RuntimeMethods(type(runner.model))
        if args.paired and candidate_source == reference_source:
            raise RuntimeError("Paired benchmark requires distinct optimized/reference source")
        captured = []
        phases = {}

        def memory():
            return {"active_bytes": mx.get_active_memory(), "cache_bytes": mx.get_cache_memory()}

        def observe():
            phases["first_token_seconds"] = time.perf_counter() - started
            phases["prefill_memory"] = memory()

        def release():
            cleared = model_compat.release_inference_cache()
            if cleared:
                phases.setdefault("cache_releases", []).append({"seconds": time.perf_counter() - started, **memory()})
            return cleared

        namespace = dict(vars(model_compat), release_inference_cache=release)
        generators = {"reference": instrument_generate(reference_source, namespace, observe),
                      "optimized": instrument_generate(candidate_source, namespace, observe)}

        def capture(model, *positional, **kwargs):
            result = generators[variant](model, *positional, **kwargs)
            captured[:] = result[0, kwargs["input_ids"].shape[1]:].tolist()
            return result

        type(runner.model).generate = capture
        for repeat in range(args.repeats):
            for sample_index, sample in enumerate(samples):
                variants = ["reference", "optimized"] if args.paired else ["reference" if args.reference else "optimized"]
                if args.paired and (repeat + sample_index) % 2:
                    variants.reverse()
                pair = []
                for variant in variants:
                    phases.clear()
                    mx.synchronize()
                    mx.clear_cache()
                    start_memory = memory()
                    mx.reset_peak_memory()
                    started = time.perf_counter()
                    result = engine.scan(sample, prompt="document parsing.", mode="precise", max_length=32768)
                    mx.synchronize()
                    elapsed = time.perf_counter() - started
                    row = {"sample": sample.name, "repeat": repeat, "variant": variant, "seconds": elapsed,
                           "tokens": list(captured), "text": result,
                           "end_to_end_tokens_per_second": len(captured) / elapsed,
                           "peak_bytes": mx.get_peak_memory(),
                           "start_memory": start_memory, "end_memory": memory(),
                           "phases": dict(phases),
                           # Includes cache release, remaining generation and
                           # text postprocessing; not a pure decode-rate metric.
                           "after_first_token_seconds": elapsed - phases["first_token_seconds"],
                           "input_sha256": hashlib.sha256(sample.read_bytes()).hexdigest(),
                           "diagnostics": engine.last_scan_diagnostics()}
                    pair.append(row)
                    report["runs"].append(row)
                    (args.output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
                    print(json.dumps({k: v for k, v in row.items() if k not in {"text", "tokens"}}, ensure_ascii=False), flush=True)
                if args.paired:
                    for key in ("input_sha256", "tokens", "text", "diagnostics"):
                        if pair[0][key] != pair[1][key]:
                            raise RuntimeError(f"Quality gate failed: {sample.name} {key}")
        report["status"] = "passed"
        report["quality_gate_passed"] = args.paired
    except BaseException as exc:
        report["status"] = "failed"
        report["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        if methods is not None:
            methods.restore()
        runner = None
        try:
            # This benchmark is single-threaded; an interrupt has already
            # unwound inference. Clear its busy marker before normal cleanup.
            if engine.busy:
                engine._set_state("error", "Benchmark interrupted", busy=False)
            engine.unload()
            mx.synchronize()
            report["active_bytes_after_unload"] = mx.get_active_memory()
            report["cache_bytes_after_unload"] = mx.get_cache_memory()
        except BaseException as exc:
            report["status"] = "failed"
            report["quality_gate_passed"] = False
            report["cleanup_error"] = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            (args.output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
