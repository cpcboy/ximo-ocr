# Apple Silicon MLX 推理效率验证

状态：2026-10-22 源码候选，尚未更新已安装 App 或公开 rc.2 安装包。只使用本机合成样本和已校验模型；不扫描、上传或迁移用户业务文件。性能、输出一致性、浏览器验收与部署分别登记，未通过项不冒记完成。

## 研究结论与边界

- 此项目的 `LoJexLLM/Unlimited-OCR-MLX` 转换版使用 MLX，在 Apple Silicon 上通过 Metal GPU 执行。已安装 App 自带 MLX 0.29.3，实际探针为 `Device(gpu, 0)`、Metal 可用，无需用户另装框架，也不经过 LM Studio。MLX 不是所有 Mac 模型加速的唯一途径，本结论仅针对此模型/引擎；不声称使用 Neural Engine。
- 模型卡：[LoJexLLM/Unlimited-OCR-MLX](https://huggingface.co/LoJexLLM/Unlimited-OCR-MLX)；框架：[Apple MLX](https://github.com/ml-explore/mlx)、[统一内存](https://ml-explore.github.io/mlx/build/html/usage/unified_memory.html)、[惰性执行](https://ml-explore.github.io/mlx/build/html/usage/lazy_evaluation.html)。模型卡宣传速度不是本项目实测。
- [MLX 0.29.3 allocator](https://github.com/ml-explore/mlx/blob/v0.29.3/mlx/backend/metal/allocator.cpp) 的 `clear_cache()` 仅回收闲置缓冲，不改活跃权重/KV。`get_peak_memory()` 统计活跃内存峰值，不能拿它当闲置缓存或清理后的内存值。
- 本机 M3 Max / 36 GiB，既有系统内存压缩、交换和其他负载会影响计时；系统 swap 不能全部归因墨析。本次不终止其他程序、不改系统参数、不提高 MLX wired/memory/cache 全局限制。

## 最小实现

`backend/model_compat.py` 在现有每个 token 的阻塞 `.item()` 完成后，保留 KV 和选定 token，删除已经用完的 `output/logits` 引用，调用 `backend/mlx_performance.py`。只有闲置缓存超过 1 GiB 时才回收；小缓存继续复用。

这是安全点检查的**软触发阈值**，不是总内存/缓存硬上限：单次计算、prefill 和延后释放仍可超过阈值。视觉阶段活跃峰值仍可能约 17 GB，不能据此降低机器内存要求。操作仍在原扫描锁内，不增加清理线程；队列结束/关闭页面/退出 App 的卸载流程不变。

不改权重、精度、图片尺寸/切块、DPI、prompt、最大输出长度、temperature、注意力或矩阵计算内核、防重复/停止规则。Windows 的 NVIDIA/PyTorch 引擎不使用此模块，未做 Windows 推理提速宣传。

已拒绝或撤回的实验：

- 只计算最后一行 logits：可能从 GEMM 变为 GEMV，浮点结果路径改变，未纳入候选。
- 单 token MoE 排序捷径：小矩阵数值测试通过，但首对实测 75.01→84.56 秒，无稳定收益，已撤回。
- 只在首字后清一次缓存：两图四次输出一致，但大页后续闲置缓存仍重新增长到约 21.8 GB，改为阈值检查。不能把这些全部归因某一种中间缓冲。

## 可复现的隔离基准

固定模型修订 `267d7adcbcd3730fdffb1eefd70ef6f486fbfc92`，FP16 权重内容不变。使用**安装包的 Python / MLX 0.29.3**，不是开发虚拟环境的 MLX 0.31.2。基准源码为 `scripts/benchmark_mlx.py`，必须指定已完整校验的本地模型和全新输出目录；不下载、不读取生产任务。

```sh
PYTHONDONTWRITEBYTECODE=1 '/Applications/墨析 OCR 工作台.app/Contents/Resources/OCRStudioRuntime/python/bin/python3' \
  -u scripts/benchmark_mlx.py \
  --model-dir "$MODEL_DIRECTORY" --output "$NEW_BENCHMARK_DIRECTORY" \
  --paired --reference-commit ce8b0392f72a282071a6b451612ffe709924c51f --repeats 2
```

两个变量必须由操作者填入真实模型目录和不存在的私有验证目录；不复制整条命令去覆盖旧报告。脚本仅用于 Apple Silicon/macOS，合成图字体使用系统 Arial/STHeiti；不是跨平台 OCR 测试入口。

五张生成的合成图：英文段落、简单表格、语法/符号、600×600 中英混排、带网格表格/双栏页。高精度参数与生产入口相同：base 1024、tile 640、动态切块、temperature=0、最大长度 32768。

同一已加载模型，提取指定 Git 基线的原 `generate` 与当前候选进行对比，交替 AB/BA；每次计时前两边均同步并清闲置缓存。记录源码 SHA/文件哈希、模型修订、平台/MLX、输入 SHA、完整 token IDs/文字/停止诊断、各页耗时、首字耗时、首字后总耗时、active/cache、清理事件和卸载状态。首字后耗时包含清理和后处理，不是纯 decode 吞吐；监测开销包含在实验计时中。

每对必须输入、全部 token、文字、停止诊断完全相等，否则失败。报告只有全部完成才标 `passed / quality_gate_passed=true`，中断/清理失败标失败；异常后恢复临时方法并卸载模型。冷态首轮与暖态复测分别分析，不把首次清理之前的耗时差异直接归因本次代码，也不承诺任意文档永远提速。

当前完整五图双轮仍在运行；结果、真实浏览器路径和最终测试将在提交前回填。临时图/报告只在 Git 忽略的 `test-results/mlx-perf-20261022/`，不进入仓库或安装包。

## Review、验证与部署门禁

- 代码自查及独立对抗 review：阈值版 P0/P1/P2=0。修复了实验工具方法恢复、失败状态、吞吐指标命名；补纯 CPU 阈值边界/连续调用、EOS/长度和原生成算法 AST 等价契约。
- 11 项新纯 CPU 测试已通过；提交前完整 pytest、lint、前端测试须再执行。实际模型数值/性能不由这些单测替代。
- 真实浏览器须用隔离支持/数据目录，扫描合成图片 → 阅读 → 完整 ZIP 导出 → 任务结束自动卸载；检查日志、Origin 拦截和任务/模型目录不越界。
- 本次尚未得到替换已安装 App 的追加确认；先按既有流程 review → 文档 → PR/CI/合并。未确认不更新 `/Applications`、不发新公开安装包、不操作 Windows。
- 如果获确认，按 DEPLOYMENT.md 的原 snapshot/install/rollback 流程，先备份旧构建和现装 App，校验漂移与所有任务终态，再从合并后 clean main 构建/部署/真实复验。任何关键路径或数据保全失败则恢复旧 App，不改数据掩盖问题。

回滚：源码使用 revert PR；未部署无需 App 回滚。未来部署必须新建审计目录，按其 `previous.app` 和 `installed-manifest.json` 回退；不覆盖扫描、笔记或模型，不改历史 Release/tag。
