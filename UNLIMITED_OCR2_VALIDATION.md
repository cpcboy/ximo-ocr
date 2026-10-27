# Unlimited-OCR 2.0：Mac 本机预览升级记录

日期：2026-10-27。阶段：**本机已备份更新为 1.3.0(8)，2.0 BF16 模型已安装，授权范围内的源码/原生候选/安装版用户路径和数据保全验证通过**。实际 App 来源为 PR #17 合并 `cfb7c929266fe43c352ae9aadf84b021d675010b`。本文件是后续证据补充，不改变包内来源；未发布新安装器或 Release，Windows 未升级。退出日志的两项非阻断观察和未验范围见下文，不能据此宣称正式版或全数据集质量验收完成。

## 需求、授权与保护范围

用户要求用 2.0 替换现有 1.0；确认保持 BF16 精度，先隔离验证，通过后备份更新本机，保留 1.0；暂不发布新的安装器。另确认已保存编辑、允许正常退出，以及新2.0 OCR/阅读器去重保留数字差异、保留死循环保护和原始输出、不修改旧扫描。

升级前 App：`/Applications/墨析 OCR 工作台.app`，1.3.0(7)，源 `afc73d5685192193fddf9e843f4034a35487c55d`。用户任务4条均终态；正常退出后建立稳定基线。历史扫描、1.0 模型和 API 配置未用于测试；安装版的合成 OCR 使用新正式目录中的 2.0 权重。Windows 引擎与现有公开 `v1.3.0-rc.2` 均不升级，不把 CI artifact 当作新发行。

## 固定来源与运行时

| 项目 | 固定来源 |
| --- | --- |
| 官方2.0 | [baidu/Unlimited-OCR](https://github.com/baidu/Unlimited-OCR)、[模型卡](https://huggingface.co/baidu/Unlimited-OCR-2)，参考修订 `9cf077c4b206e0e2a31879df937b0b0bcba3661c` |
| Mac模型 | [mlx-community/Unlimited-OCR-2-bf16](https://huggingface.co/mlx-community/Unlimited-OCR-2-bf16)，修订 `850d1e483f5a82a0597f0a45aac31b07ba840df2`；BF16、不量化；11文件共6,690,229,659字节 |
| MLX适配 | [上游PR #2601](https://github.com/Blaizzy/mlx-vlm/pull/2601)，固定头 `c3ae82e2e79ee553c534c7b4efea73bc85122ab2`；已核对2026-10-27 16:18:51Z合并，合并SHA `5061bd7f3848f720cb2ba8d0bc1a1a181d733359`。授权时未合并，现仍固定已审查头，不追随浮动版本 |
| 源码校验 | fork源码ZIP SHA-256 `b4b96b728fc617592965d656b72b90311c0491806bf83a97926732fa79828eec`；App启动前另核对关键适配文件哈希 |
| Mac运行库 | portable Python3.11.17；MLX/MLX-Metal0.32.4；MLX-VLM0.7.11（上述源码构建）；Transformers5.14.0；完整依赖锁定在mac-app/requirements-runtime.txt |

模型在隔离目录全量下载，随后由墨析下载管理器按manifest逐文件校验并生成完整收据。没有下载或执行模型仓库中的Python；不使用`trust_remote_code=True`。旧模型清单单独保留为`backend/models/mlx-v1.json`，新引擎不静默套用旧权重。

## 代码影响面与独立 review

- `backend/mlx2_engine.py` / `mlx2_runtime.py` / `mlx2_vision.py`：固定版本验证、原精度逐页推理、视觉兼容修正、停止/卸载。旧引擎原样移至`legacy_mlx_engine.py`用于回退基准，Windows调度不变。
- `backend/config.py` / `models/mlx.json` / `model_download.py`：新目录、新固定下载清单、旧目录拒写；损坏配置修复必须有匹配旧收据和完整权重，修复中断保留依据。
- `ocr2_text.py` / `repetition.py` / `app.py`：安全解析结构标记、保留HTML表格和原始输出/模型来源；新结果完整重复周期去重，阅读器同规则；历史结果不批量修改。
- `app/page.tsx`：2.0/BF16/预览与旧模型保留提示；重复停止/输出上限显式部分结果提示。
- `mac-app/`：固定源码和依赖随App提供，build8；无新公开安装器版本。`scripts/benchmark_mlx.py`仍测旧1.0并记录真实旧源码/清单哈希。
- 回归测试覆盖新旧引擎、下载损坏/暂停、数字/符号/中文/长模板、读者版本分流、异常和数值边界。

对抗review在独立代理只读进行。问题逐条修复并复核：

| 优先级 | 发现与修复 |
| --- | --- |
| P1 | 上游CLIP绝对位置插值的布局错配：明确NHWC、FP32 bicubic antialias、恢复原dtype，与官方参考核对 |
| P1 | CLIP激活/LayerNorm不一致：QuickGELU与1e-5 epsilon修正，含低方差测试 |
| P1 | SAM相对位置插值坐标不一致：按官方half-pixel公式，与PyTorch参考对齐 |
| P1 | 沿用旧去重会把120条编号记录误删；仅保留数字的短窗口仍会误判长模板。改为完整周期精确比对，保留数字/符号/中文差异，并保留真正重复尾巴清理 |
| P2 | 损坏配置无法修复及暂停丢收据：限可信完整旧权重情况下允许修复，中断保留匹配依据 |
| P2 | 重复停止/异常中断状态不完整：partial/stop_reason保留，load中断清理并重新抛出，stream关闭和busy恢复 |
| P2 | BF16容差描述过强：改为真实有序整数ULP距离测试，并加小值2ULP负例门禁 |
| P2 | 旧性能基准未追踪新拆分旧引擎：显式加载v1manifest并加入来源哈希 |

代码末轮：**P0=0、P1=0、P2=0**。这允许进入文档/PR，不等于允许跳过原生、合并和部署门禁。CLIP修正为模型实例级；SAM相对位置helper为MLX进程内局部替换，不修改依赖文件或权重。

## 已完成验证

机器：Apple M3 Max / 36GB，macOS27.0.1。测试合成文件，不读取用户原件；明确选择“本机 MLX · 串行”，不调用远程模型。

### 自动化与数值

- 本机完整Python：178 passed，6条依赖告警（已有SWIG及Starlette/httpx弃用），不宣称零告警。
- `npm run lint`、`npm test`（正式网页构建+11 Node测试）通过；`git diff --check`通过。没有降低lint规则；仅将测试用PyTorch环境放在既有忽略的build目录。
- Mac视觉数值14项：CLIP绝对位置16→10/16/20、SAM绝对64→40/64、相对127→79等、QuickGELU与低方差归一化。FP32 atol1e-5/rtol2e-5；BF16真实ULP差<=1且差异比例<1%，2ULP负例被拒绝。使用PyTorch2.13作测试参考，不打入App。
- 上游适配下载无关的DASH/processor测试40 passed（513 deselected）；它只是随机张量接口验证，不当成OCR质量证据。
- 独立review另用120条长模板（18,496字符）和含金额/正负号/中文（6,395字符）确认全部保留；真正相同循环仍清理。

### 真实模型与浏览器

portable运行时在离线模式完成六张图：英文段落、表格、布局、中英小字、栅格多列、120条小字。锚点全部通过，无partial/截断；120条编号/ID/数量完整。直接引擎计时分别8.03/2.41/2.31/1.59/5.23/35.69秒（首图含本轮首推理影响），不与旧报告跨样本宣称提速。峰值约8.70GB；卸载后MLX active1244字节、cache0、loaded=false。

直接六图记录在最后“完整重复周期”收紧前生成，已含数字保留修正；**最终代码另经真实浏览器重新OCR**：系统选择文件入口同时选3页合成PDF与120条小字PNG，共4页完成。英文、中文、表格金额/双列顺序正确，120条完整；阅读器搜索`Entry 120`得1个匹配；深色主题表格可读。无需重复扫描旧用户文件。

提交`180c920701b461c572d266a342e9dc1c2abc66ad`后又独立复跑最终代码六图，`work/realocr-final/report.json`记录源码/脚本hash：6图全部通过、dense逐条120项匹配，正文及完整原始输出与上一轮逐字一致。耗时9.16/2.50/2.64/1.66/9.61/47.01秒，峰值约8.79GB；卸载active1244/cache0/loaded=false。计时波动说明不能承诺固定提速。该直接进程退出没有出现信号量警告；仍保留源码服务退出的警告记录。

浏览器真实点击完整结果包下载，两ZIP的CRC与JSON字段验证通过，均保留model_id/raw_model_output，dense清洁/阅读有效文本和原始输出全部包含120条。无browser warn/error。任务全部完成自动卸载；关闭页面后`/api/client/status`为connected=false。外部Origin的下载POST被403拒绝；未放宽安全策略。临时服务正常停止，下载的两个合成ZIP移入私有证据目录，不留在Downloads。

源码后端在停止后出现1条Python `resource_tracker` 的信号量清理告警（1 semaphore）；前端/后端无Traceback、ERROR或5xx，监听与进程均退出。不能据此宣称日志零告警；后续原生退出须复查，若有残留进程/模型或功能失败则阻断更新。当前未证实该告警的具体上游根因，不通过屏蔽告警“修复”。

| 浏览器导出 | SHA-256 |
| --- | --- |
| synthetic-three-pages-完整结果.zip | a1a5f75d03143d504534da328fa890ea6c5038c295eae5c058785605834ce04c |
| dense-small-完整结果.zip | 57e762aafc406149559eea79073853d294b217ba243019ed3506172d05c49869 |

### 私有证据位置（不提交Git）

本次worktree为`~/cpcsoft/OCR/work/uocr2-upgrade/`。其中`work/`保留python-tests/frontend-tests/frontend-lint/vision-parity/portable-runtime/model-verification日志、`realocr/report.json`及原始输出、`ui-backend-current.log`/`ui-frontend.log`、`evidence/browser-exports.json`与ZIP/截图。截图`browser-table.png`、`browser-reader-dark.png`、`browser-dense-search.png`。

耐久审计根`~/cpcsoft/OCR/.maintenance-backups/2026-10-27-uocr2/`（0700）保存`installed-before.json`、`data-model-before.json`、`data-model-after.json`、`model-install.json`及`installed-verification.json`，另归档测试脚本、源/原生日志、合成ZIP和截图。旧App与上次部署清单逐项一致；安装与正常启动退出后，data389、managed1.0 14、LM Studio1.0 7条目（含目录/权限/类型）逐项内容、类型和权限完全相同，不是仅比较数量。私有证据不提交 Git、不装进 App，也不作为普通缓存清理。

## 合并、构建与实际部署

PR为[#17](https://github.com/cpcboy/ximo-ocr/pull/17)，已合并为`cfb7c929266fe43c352ae9aadf84b021d675010b`。首轮CI40548974108在Linux收集Mac可选数值测试时失败：NumPy在MLX跳过判断前导入；同批Windows被矩阵fail-fast取消，并非已证明Windows相同报错。最小修正把NumPy导入放到MLX判断后，Mac14项数值门禁复跑通过；不改变容差、不安装无关AI依赖到非Mac CI。首次失败保留审计。

- 最终[PR CI 40549479921](https://github.com/cpcboy/ximo-ocr/actions/runs/40549479921)与[main CI 40550374203](https://github.com/cpcboy/ximo-ocr/actions/runs/40550374203)的 Linux/Windows 均成功：每平台162 Python passed、3 skipped、6 warnings；11 Node通过。Windows额外2项NSIS测试及测试安装器构建通过；只是CI artifact，未新发安装器，也不是Windows2.0实机验收。
- 从干净`HEAD == origin/main == cfb7c929...`构建网页及Mac App，合并源本机178 Python再次通过。严格签名校验通过，包内`SOURCE_COMMIT`与合并SHA一致，版本1.3.0(8)，清单20602项。包中含固定MLX适配及MIT许可，不含权重、用户数据或测试用PyTorch。未经修改的候选完成下面原生路径，清单仍相同。
- 模型只添加到`~/Library/Application Support/墨析 OCR 工作台/models/Unlimited-OCR-2-bf16/`。审计脚本先以pending状态落盘，再逐文件复制/哈希/完整收据校验，原子改名后更新completed记录；11文件、6,690,229,659字节，不复制缓存、临时分片或模型Python。两处1.0目录保持原样。
- 安装前再次核对旧App10424项与原基线、数据/旧模型全部条目、端口空闲及候选来源；原`scripts/deploy_macos.py`备份旧App后安装。`install-v2/previous.app`保留1.3.0(7)，`install-v2/deployment.json`和`installed-manifest.json`保留操作记录与新20602项清单。
- 安装后严格签名、App清单/来源、新模型11文件全量哈希/收据再次通过。正常启动看到原4条任务；只查首页和模型信息，未打开旧阅读器、重扫或变更接口配置。退出后`data-model-after.json`与before完全相同。最终检查时间为2026-10-27 17:46 UTC。

## 真实原生验收与退出状态

两轮均用系统文件选择框和系统保存框，不以HTTP成功代替原生路径。`OCR_STUDIO_SUPPORT_DIR`/`OCR_STUDIO_DATA_DIR`仅对隔离测试进程设置，未改全局环境。候选用隔离模型；安装版用新正式模型目录，业务任务仍全部保留在原目录。

| 范围 | 真实操作与结果 |
| --- | --- |
| 干净合并源候选 | 在`work/native-candidate/`选3页合成PDF，3页完成（209/102/555字），深色表格可读，完整包从系统保存框导出；model_id/raw/完整状态均正确；自动卸载，正常退出 |
| `/Applications`安装版 | 在`work/native-installed/`选120条小字PNG；完成5349字/57.5秒，逐条核对编号、ID和数量全部保留；阅读器搜`Entry 120`为1匹配；完整包系统保存成功；显示2.0 BF16权重/组件就绪、内存未载入、自动释放开启 |
| 普通启动（无隔离环境） | 首页原4个任务仍在，系统状态识别新正式2.0目录并就绪；未打开历史任务；正常退出后数据及两处旧模型逐项不变 |

| 原生导出 | SHA-256 |
| --- | --- |
| native-candidate-完整结果.zip | 6c4bf8088db42ee3a3178c046da805ee41f6efcc6b2c18697cc47991edbc5bb8 |
| native-installed-完整结果.zip | 012a5a6bd688a8b2584262a369174a7bc904b2ce870bea2699cc78255e4eaabf |

两包CRC通过，所有页有`model_id`和`raw_model_output`，无partial/截断/页错误；安装版清洁正文、阅读有效正文、原始输出均保留120条完整记录。截图为审计根的`native-candidate-reader.png`、`native-candidate-model-ready.png`、`native-installed-search.png`、`native-installed-model-ready.png`；仅展示合成内容。

退出证据：候选后端/前端PID7126/7132、安装版隔离9214/9220、普通启动App/后端/前端11846/11853/11862均消失，3000/18765端口关闭。两轮OCR后均自动卸载；日志有正常shutdown。原生测试前后端未检出Traceback/ERROR/HTTP5xx；普通启动日志无OCR提交。最终保持App已退出、模型不占用推理内存，用户可正常从“应用程序”再次打开。

### 非阻断观察（未修复，P2）

1. OCR服务退出复现Python `resource_tracker` 的1 semaphore清理警告。已经确认本次进程/监听退出、任务后模型卸载，但没有证实具体根因或证明所有资源无泄漏；不屏蔽警告、不标为根因已解决。
2. 原生控制台仍有`sandbox_extension_issue_file failed for : 2 (No such file or directory)`。本轮系统选文件、OCR、阅读、导出保存均成功；仅能说明没有阻断本次路径，不能推断诊断已修复。

候选独立review允许继续已授权的本机预览安装。安装后的独立最终复核再次确认App/备份清单与签名、模型11文件固定哈希、前后数据清单、真实截图/ZIP/退出证据及五份文档一致：**P0=0、P1=0、新增文档P2=0，上述既有P2观察2项保留**。任何未来新增关键路径/保全失败仍须停止并回退，不得把这次结论当作后续变更的自动放行。

证据文档补充复跑本机178 Python（6条依赖告警）与lint通过，5份文档37个本地链接及diff检查通过；文档经独立review后单独PR/CI/合并，不再构建或安装App。对应文档PR记录与提交历史是证据补充的准确来源，不能代替App的`cfb7c929...`。

## 未验范围

不涵盖：Windows2.0、干净新Mac/最低macOS14实机、169页教材/任意复杂扫描全量质量、正式基准、不同行为参数速度比较、跨页联合DASH、商业签名/公证。2.0仍可能漏字/幻觉，应对照原图校对；原始输出保留并不保证正确。

## 回退

按 [DEPLOYMENT.md](DEPLOYMENT.md) 的本批次章节：正常退出后，用原部署器`rollback`恢复`install-v2/previous.app`，以本次`installed-manifest.json`核对现版本，使用全新的`rollback-v2/`保护失败候选。旧1.0路径原样保留，App回退即可继续使用，不覆盖任何扫描/笔记/API设置。源码只用revert PR，不强推或重置main。本次备份10424项已复核与旧基线一致、签名通过；未执行回退。新2.0权重可保留，不自动删除；不要复用已存在的安装/回退审计目录。
