# rc.3：Mac Unlimited-OCR 2.0 候选构建与发布验证

## 当前阶段（2026-10-27）

**已公开[Mac 2.0候选rc.3](https://github.com/cpcboy/ximo-ocr/releases/tag/v1.3.0-rc.3)，新DMG隔离原生路径及真实浏览器下载验收通过。** 用户已明确确认“仅发布Mac 2.0候选安装包”，保持Pre-release/非正式/非Latest，不再次更新本机，不操作Windows。完整正式验收的未覆盖范围和三类非阻断诊断仍保留，不能把本次候选分发当正式版。

本机现装版仍为1.3.0(8)、源`cfb7c929266fe43c352ae9aadf84b021d675010b`，此前验证见[2.0本机记录](UNLIMITED_OCR2_VALIDATION.md)。Mac当前公开候选为rc.3；Windows仍rc.2（不含2.0）。本次新DMG与tag源为`ee808f671712e8795c89a4d4f1c1d3f6d6287115`，不沿用现装版SHA，不把后续证据文档提交当作包源。

## 最小变更与Review

基础源码为PR #18合并`130ac4139e308aa9097d9a7a2f4455dc2e0f9fd2`。

- `mac-app/Info.plist`：build8→9，产品版本仍1.3.0。
- `mac-app/build-installer.sh`：独立rc.3输出名，保留同名拒绝覆盖、clean main及来源/签名门禁。
- `tests/release-version.test.mjs`：Mac新候选与Windows原rc.2分别校验，新增1项Node测试。
- README/CHANGELOG/DEPLOYMENT/MAINTENANCE_RULES及本文件、候选说明：记录仅Mac范围、来源、签名限制、实测门禁和回退。

三文件代码、六份文档及私有归档脚本自查与独立对抗review末轮新增P0/P1/P2=0。审计脚本初轮1项P2（基线/目录持久化）已用flush/fsync及原子状态替换修复；两个定向版本测试、脚本语法、plist、diff、43个文档本地链接检查通过。无OCR逻辑、模型清单、Windows代码、权限或业务数据变更。

本机完整回归：178项Python通过（6条依赖告警）、lint通过、前端构建与12项Node测试通过。PR #19及main双平台CI已成功，新DMG原生路径、公开分发和真实下载实际结果分列下文，不用本机回归代替。

## 构建、保护与发布门禁

按[DEPLOYMENT](DEPLOYMENT.md)本批次流程执行。审计根为本机忽略目录`~/cpcsoft/OCR/.maintenance-backups/2026-10-27-rc3/`，不上传Git或Release。

1. 旧构建App须先归档并核对清单/签名；现安装版与上次已审计清单一致，数据、两处1.0及现有2.0模型建立只读基线。
2. PR、main CI成功后从干净合并源构建；DMG仅App/运行时和许可，不含模型、扫描/笔记/API配置、日志、测试依赖或备份。包内SOURCE_COMMIT、前端构建摘要与tag实际提交必须一致。
3. 只读挂载新DMG，在全新隔离支持目录操作无模型提示/文件选择/合成OCR/阅读/ZIP保存/退出。只用现有已校验隔离2.0权重，不重新下载生产模型、不使用真实扫描或远程接口密钥。
4. 新包/说明/验收独立review后才建草稿；核对两资产digest/size、真实tag目标、prerelease和非Latest后公开；再用真实浏览器点击下载并独立公开回读hash。
5. 完成后复核现安装App/数据/模型不变、临时服务与端口退出；合成任务可恢复归档。实际包SHA、资产、CI、截图、下载及失败边界通过证据PR回填。

## 已知限制与撤回

沿用2.0预览的两项非阻断P2观察：退出信号量清理告警、原生sandbox文件诊断；本次两轮正常退出另观察到IMK消息通道诊断，合计三类。根因均未宣称解决；未发现对应关键路径或保全失败。分发门禁已完成，仍不扩大为正式验收。

Mac包仅ad-hoc签名，未Developer ID公证，不绕过Gatekeeper或浏览器拦截。仅此Mac硬件/系统的合成样本验收，不代表全新Mac、最低macOS14或全数据集质量。Windows不提供本次新包，CI Windows artifact不是发行或实机验收。

分发失败保留草稿；公开后异常醒目标记撤回并保留原tag/包，修复走新PR及新候选，不覆写旧资产。本次没有安装到本机，因此不执行本机回滚；既有App/数据/模型和旧公开rc.2均保留。详细步骤见DEPLOYMENT。

## 实际构建与来源

- 准备提交`1047ef2819088c187d21f17d35f465e1ef6a6092`；[PR #19](https://github.com/cpcboy/ximo-ocr/pull/19)合并为`ee808f671712e8795c89a4d4f1c1d3f6d6287115`，这是本批DMG唯一包源。后续证据文档提交不得替代该SHA。
- [PR CI40559179370](https://github.com/cpcboy/ximo-ocr/actions/runs/40559179370)、[main CI40560077376](https://github.com/cpcboy/ximo-ocr/actions/runs/40560077376)均success；Windows只生成原流程临时CI artifact，不作为本次发行。
- 在干净合并源执行原`build-installer.sh`；旧worktree build8已先同卷归档，20602项清单、签名及耐久回执通过。现装App仍为1.3.0(8)、源cfb7c929；不重启或替换它。
- DMG镜像校验、只读挂载来源、包内外20602项清单、严格ad-hoc签名、前端BUILD_SOURCE及后端精确Git清单通过；Python/Node与已验证运行时逐项一致，Metal可用，固定适配9源码hash和MIT许可通过。包内无模型权重、用户扫描/笔记/接口配置、PyTorch/pytest验证环境。

| 文件 | 字节数 | SHA-256 |
| --- | ---: | --- |
| MoxiOCR-macOS-arm64-1.3.0-rc.3.dmg | 527924040 | `0eff500098a1188538673afaca6c86235aec5a0ebacfa32542a178881a689658` |
| MoxiOCR-macOS-arm64-1.3.0-rc.3.dmg.sha256 | 101 | `3629e871c233fc454089d17dbf29aa0a0fed70cb2465977f4887431d2a8a3518` |

## 实际原生路径与保护结果

环境为Apple M3 Max/36GB、macOS27.0.1，直接运行只读DMG中的App，两个全新support目录，不复制生产接口密钥或扫描数据。

1. 空模型目录：首页首次下载提示、系统状态的Unlimited-OCR 2.0/BF16/Apple Silicon、固定修订和下载入口可见；预载按钮禁用。本轮不重新下载6.7GB模型，不把入口可见当全量下载验收。
2. 完整模型目录：复用既有隔离2.0模型，先逐个核对固定清单11文件的全部hash和收据；系统选文件框一次选择3页合成PDF与120条小字图片，本机MLX串行完成2个任务。
3. PDF三页字符数209/102/555；第3页表格在深色阅读中清晰可读，编号/数量差异保留。小字5349字符，单次显示38.8秒，仅是本次样本观测，不作性能提升承诺；全文搜索Entry120为1匹配。
4. 两次“完整结果包”均真实调用系统保存框，返回工作台未出现帧加载中断。两个ZIP的CRC、页数、2.0模型标记、原始输出、无截断/无部分结果/无错误标记通过；120条在正文、原文与有效阅读正文中逐条完整且仅一次保留。
5. UI和health均显示模型已卸载、队列空；携带外部Origin的下载POST实测403（接口边界测试，不冒充浏览器跨站实测）。正常CmdQ后前后端及模型子进程退出、3000/18765端口关闭，随后正常卸载DMG。
6. 新旧App、数据及模型只读保全复核：现装App20602项及签名不变；data389、managed1.0 14、LM Studio1.0 7、managed2.0 13条目内容/类型/权限完全一致（条目含目录/收据，不等于文件数）。旧build8归档也未变化。

| 私有合成导出 | 页数 | SHA-256 |
| --- | ---: | --- |
| rc3-three-pages-完整结果.zip | 3 | `336f9175729bc3adea02976b46e83f0e1acfadeb5eee023d39cb87d20dfe7487` |
| rc3-dense-完整结果.zip | 1 | `e58bf02e0f72b2fffb971b2884d6376041d776c280ef75fd79e91eb1effa71a1` |

私有审计根仍为`~/cpcsoft/OCR/.maintenance-backups/2026-10-27-rc3/`，包含package/native验证、保护前后清单、CI/构建/运行日志与四张原生截图：`native-empty-model.png`、`native-dark-table.png`、`native-dense-search.png`、`native-model-unloaded.png`。不上传这些运行数据/日志到仓库或发行附件。

## 对抗Review、调查及剩余观察

- P1：私有验包脚本的有限黑名单漏检风险已修复为后端精确Git清单、前端/依赖目录对照，拒绝额外环境文件、私钥容器及未知私钥块；未发现用户凭据泄漏。
- P2：归档记录持久化、镜像/只读挂载绑定、固定适配与许可校验，以及通用目录清单函数/系统只读字段兼容问题均已修复并独立复核。临时验证工具只在忽略目录使用，不更改App权限或部署器。
- 验包密钥扫描曾因OpenCV内嵌GnuTLS的8个公开自检向量停止。保留首次失败日志；核对wheel摘要与[PyPI官方发布](https://pypi.org/project/opencv-python/5.0.0.93/)一致，8个向量逐hash与[GnuTLS上游自检源码](https://github.com/gnutls/gnutls/blob/master/lib/crypto-selftests-pk.c)相等后，仅对精确文件/数量/hash集合识别为公开样本；没有关闭其他密钥检查。
- 新包/原生证据/发行正文独立复核P0/P1=0；三类非阻断P2观察保留：full轮1 semaphore退出清理告警；full轮sandbox文件诊断；empty与full两轮退出均出现`IMKCFRunLoopWakeUpReliable`消息通道诊断。没有宣称根因解决或日志零告警。后端/前端无Traceback、ERROR或5xx，输入搜索、保存、正常退出均通过。
- 既有CI action运行时迁移提示、Python依赖弃用及hdiutil弃用提示仍记录在日志，不作为正式兼容性承诺。新Mac、最低macOS14、Windows2.0、169页教材/任意复杂扫描全量质量和跨页联合DASH仍未验收。

## 公开发行与真实下载

- Release ID `425854475`，公开时间`2026-10-27T18:56:47Z`；`draft=false`、`prerelease=true`，Latest端点为404（未设置任何正式Latest）。远端tag解析到实际包源`ee808f671712e8795c89a4d4f1c1d3f6d6287115`，发行正文与已review正文一致。
- 恰好两个上传附件，服务端大小、SHA-256和uploaded状态与本页资产表一致。GitHub网页“Assets 4”包含额外两个自动源码归档，不是上传了Windows包或用户数据。
- 真实Codex内置浏览器以未登录状态打开公开发行页，确认Pre-release、仅Mac/未公证/三类诊断和未验范围。附件初始显示Loading，收起再展开后显示两个下载链接；随后实际点击校验文件与DMG。
- 校验文件下载事件返回Downloads实际路径；DMG的15秒、45秒下载事件等待超时，不记为成功。浏览器下载随后自行从`.crdownload`完成为`Downloads/MoxiOCR-macOS-arm64-1.3.0-rc.3.dmg`（本机12:00:02），未重点击DMG或绕过任何警告；对完成的两个实际文件重新核对字节数、全文SHA-256及校验文件内容，全部与本页表一致。文件完成校验才登记浏览器下载通过，未执行下载的App，不把此结果当Gatekeeper/Chrome兼容性保证。
- 另使用无认证公开URL独立下载相同两个附件到全新私有验证目录，HTTPS校验未关闭；大小/全文SHA-256相同，响应成功。这是独立回读证据，不替代上条真实浏览器点击路径。
- 独立review再次复算上述四个实际文件全部大小/hash；浏览器两文件的系统下载来源元数据均指向GitHub发行资产域，referrer为rc.3发行页，DMG于18:59:10Z创建、19:00:02Z完成，与点击后的下载时序一致。审计不公开临时签名下载查询参数。
- 私有审计根保存`release-draft-verification.json`、`release-public-verification.json`、`distribution-browser-verification.json`、`distribution-public-verification.json`、`release-public.png`及`release-assets.png`。元数据、浏览器下载与公开回读分别留证；这些记录/日志不作为发行附件上传。

## 分发后的保全与收尾

2026-10-27T19:06:16Z最终只读核对：现装App20602项与发布前清单相同、严格签名通过，data389/managed1.0 14/LM Studio1.0 7/managed2.0 13项内容/类型/权限相同；旧build8备份以及旧rc.2 DMG/SHA校验文件也未变。3000/18765关闭，DMG原生验证进程已退出；本次没有替换、重启现装App或操作Windows。

仅将本批`work/rc3/native-empty`、`native-full`两个全新合成support目录同卷可恢复归档至审计根`recovered-synthetic-support/`，移动前后逐项hash/类型/权限相同；不删除生产扫描或模型，不清理既有隔离模型和测试源文件。记录为`final-preservation.json`、`protected-final.json`及`synthetic-archive.json`（completed），可据映射恢复合成测试目录，不涉及业务数据回滚。

上述分发、保全归档及六份证据文档已完成独立末轮复核，新增P0/P1/P2=0，三类非阻断P2诊断仍保留；43本地链接、diff和两个版本测试通过。证据通过后续文档PR回填，只更新README/CHANGELOG/DEPLOYMENT/MAINTENANCE_RULES、本文件和rc.3说明；不改变DMG、tag及其源SHA。证据PR/CI/合并回执随最终交付提供，不再次构建或安装App。
