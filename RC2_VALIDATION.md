# rc.2 构建、分发与验证记录

## 当前状态（2026-10-22）

用户授权把阅读修复打入 Mac/Windows 新候选，按 PR/review/CI/合并/验证发布，不发布正式版。本次不替换 `/Applications`、不安装远端 Windows，不触发全量模型下载。

源码改动仅为六处打包版本/文件名、一个版本契约测试、Windows 安装说明与发布文档；阅读 CSS 已在 PR #7 合并。Mac 1.3.0(7)，Windows 1.3.0.2，发行 v1.3.0-rc.2。

已于 **2026-10-22 18:09:37 UTC** 公开 [v1.3.0-rc.2](https://github.com/cpcboy/ximo-ocr/releases/tag/v1.3.0-rc.2)，Release ID `421038848`，`draft=false`、`prerelease=true`，非 Latest。候选分发范围已完成新DMG原生路径、公开页面与下载验证；不等于完整OCR或Windows目标机验收。

## PR、CI 与实际包来源

- 准备提交 `31f9d7659964fb8c83b93976e5a5fc796f4a6cf6`；[PR #9](https://github.com/cpcboy/ximo-ocr/pull/9) 合并为 **`3e9a7e2ea2bc33fd58cafd33520a1928599a28c3`**。包内 `SOURCE_COMMIT`、clean main 构建源及实际 tag 均等于该 SHA，证据文档提交不改包来源。
- [PR CI 39821165263](https://github.com/cpcboy/ximo-ocr/actions/runs/39821165263)、[main CI 39822054430](https://github.com/cpcboy/ximo-ocr/actions/runs/39822054430) 全成功；57 Python、lint、构建+11 Node、语法检查通过，未声称遗留 `tsc --noEmit` 通过。
- Mac严格codesign、DMG校验通过，镜像10420文件与构建App一致；Windows解包CRC通过、3269 stage文件逐项一致，额外5项为NSIS正常文件。两包前端2573文件相同，源码摘要 `a20a78ae416d56c6b9f4e80125badd7109724f209fc9b3284f344ddba0493c75`，dirty=false；许可一致，无扫描/模型权重/日志/数据库/私钥入包。
- 公开EXE是在Mac交叉构建的二进制；Windows CI原生NSIS成功是另外一次构建，不冒充目标机安装或本EXE运行验收。pip构建报告宿主venv的torch/setuptools冲突，目标14个bootstrap依赖没有这两项，target安装/NSIS成功；不把警告隐藏或称作Windows运行验证。
- 代码、准备文档、实包、原生证据、发行正文各轮独立复核新增P0/P1/P2=0。后续公开分发结果仍单列，不提前宣称通过。
- 证据文档最后追加review发现1项P2：拟同步到Release正文的验收链接使用相对地址；已改为GitHub main绝对链接并经独立复核关闭，末轮P0/P1/P2=0。

## 四资产清单

草稿先核对服务端digest/size和已review正文，才公开；公开tag解析到上述commit。Latest接口为404（仓库目前无正式Latest），未把候选设为Latest。

| 文件 | 字节数 | SHA-256 |
| --- | ---: | --- |
| MoxiOCR-macOS-arm64-1.3.0-rc.2.dmg | 282825180 | d96cfa4be5218c0056b2115527dd370687e1518b53715c08d1d901e33f1e844b |
| MoxiOCR-macOS-arm64-1.3.0-rc.2.dmg.sha256 | 101 | f42d394d2a74a4299898c6b9ffd7532fcde3cda70abac41a02a8d0c62c40f4c5 |
| MoxiOCR-Windows-x64-1.3.0-rc.2-candidate.exe | 52748024 | f39679299d48ace609eb9276087c2840f0845789ec7d45fa82c8fcc22172c678 |
| MoxiOCR-Windows-x64-1.3.0-rc.2-candidate.exe.sha256 | 111 | 0c5e3dd15f08375154de94301ed2aa4f9b4d7fc3616f0afa5a4c7dfedfc41c8c |

## 新 DMG 原生验收与数据保全

用户确认已保存编辑，可正常退出现有App后测试，且不替换安装版。退出后建立新私有业务/模型基线，不复用上轮旧数量。只读挂载本次DMG、独立support、禁用legacy模型并清除继承模型路径；核对唯一实例PID与挂载包命令及support目录后才导入合成文件。

实际路径：文件框打开→取消→重开→选择735字节合成TXT→1页完成→阅读四主题（深色/明亮/护眼/跟随系统深色）→原始OCR/阅读版切换→原生保存完整ZIP→正常Cmd-Q退出。逐张截图正文、表头、代码及引用可读；ZIP3069字节/4条目CRC通过、原始文件字节一致、TXT/MD/JSON标记齐全、JSON1页。ZIP摘要 `4289ea94f6e23002fcd8238eb1b2145cd30ecd7729c05c496b8b295692611734`。

退出后三个测试进程均消失、3000/18765无监听；backend517行/frontend1行无ERROR/Traceback/HTTP5xx，unload200、正常shutdown。原生仍有输入法mach-port及既有sandbox文件诊断，不宣称零诊断。直接读取TXT没有加载模型，因此不证明模型OCR或加载后内存释放。

已安装App仍为1.3.0(6)，10420文件清单匹配测试前基线；4任务均completed，369业务文件619537203字节、13个应用模型文件6682783518字节、5个legacy文件92889字节全部哈希匹配。没有改历史任务、共享偏好或模型文件；测试目录只含合成内容，已可恢复移入废纸篓，DMG已卸载。

私有证据和旧包备份位于本机应用支持根下 `maintenance-backups/2026-10-22-rc2/`：`prebuild/`、`installed-before.json`、`business-model-before-test.json`、`evidence/`。证据含四主题截图、原生保存框/导出后页面、ZIP和服务日志；不提交Git、不上传Release。

## 公开分发验证

公开四文件均以不带凭据的公开下载URL独立回读，HTTP200，字节数与上表一致；SHA-256和逐字节cmp全部与发布本地源相同，公开回读通过。

Chrome连接不可用后停止该路径，用户明确选择“用内置浏览器继续验证”。在未登录的内置浏览器真实打开发行页，确认Pre-release、源码3e9a7e2、签名/未验收限制、四个资产链接；逐一点击两个安装器和两个校验文件，四文件均保存到本机Downloads，大小/SHA-256与上表一致。Mac大文件的工具等待曾超过30秒，但没有重试下载或绕过防护；恢复原页可见该链接为active，实际282825180字节DMG已保存且完整哈希匹配。其余三项均收到浏览器完成事件与保存路径。此结果不证明Chrome或Windows安全软件兼容性。

最终发行页截图 `evidence/public-release-page.png` 包含预览标识、来源、未验收边界和Assets；浏览器检查时无warn/error日志。独立curl回读与浏览器实际下载分别验收，没有互相替代。独立review再次逐字节核对两组下载、截图及最终六文档，末轮P0/P1/P2=0（追加链接P2修复见上文）；临时回读和浏览器下载副本已可恢复移入废纸篓，正式构建原包/备份及证据保留。原生/分发范围通过，完整OCR/Windows等下列边界继续保留。

## 未完成验收与已知边界

全量模型下载、真实图片/PDF OCR、模型加载后的内存释放、Windows目标机安装/杀毒/显存释放未验收。Mac仅ad-hoc签名、未Developer ID公证，Windows未商业签名；遇到系统/浏览器/杀毒拦截不绕过。遗留Cloudflare示例类型检查和原生诊断未修复。正式版未发布，本次也未自动更新本机App。

## 回退

发布只影响新候选页面；草稿阶段停止公开，公开后按 DEPLOYMENT 撤回标识并保留 tag/原包，不覆盖 rc.1。现安装 App 和用户数据不变，无需本机回滚。本机旧 App 回滚方案仍见 LOCAL_PREVIEW_UPDATE，不能使用 rc.2 构建备份替代原安装回退点。
