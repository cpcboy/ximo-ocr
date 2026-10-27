# rc.3：Mac Unlimited-OCR 2.0 候选构建与发布验证

## 当前阶段（2026-10-27）

**准备阶段，尚未创建新Release、尚未生成本批次DMG。** 用户已明确确认“仅发布Mac 2.0候选安装包”，保持候选/非正式/非Latest，不再次更新本机，不操作Windows。

本机现装版仍为1.3.0(8)、源`cfb7c929266fe43c352ae9aadf84b021d675010b`，此前验证见[2.0本机记录](UNLIMITED_OCR2_VALIDATION.md)。当前公开仍是rc.2（不含2.0）；本次新DMG与新tag的真实来源必须单独记录，不能沿用现装版SHA。

## 最小变更与Review

基础源码为PR #18合并`130ac4139e308aa9097d9a7a2f4455dc2e0f9fd2`。

- `mac-app/Info.plist`：build8→9，产品版本仍1.3.0。
- `mac-app/build-installer.sh`：独立rc.3输出名，保留同名拒绝覆盖、clean main及来源/签名门禁。
- `tests/release-version.test.mjs`：Mac新候选与Windows原rc.2分别校验，新增1项Node测试。
- README/CHANGELOG/DEPLOYMENT/MAINTENANCE_RULES及本文件、候选说明：记录仅Mac范围、来源、签名限制、实测门禁和回退。

三文件代码、六份文档及私有归档脚本自查与独立对抗review末轮新增P0/P1/P2=0。审计脚本初轮1项P2（基线/目录持久化）已用flush/fsync及原子状态替换修复；两个定向版本测试、脚本语法、plist、diff、43个文档本地链接检查通过。无OCR逻辑、模型清单、Windows代码、权限或业务数据变更。

本机完整回归：178项Python通过（6条依赖告警）、lint通过、前端构建与12项Node测试通过。PR/main CI及新包原生/分发验收尚待执行，不用本机回归代替。

## 构建、保护与发布门禁

按[DEPLOYMENT](DEPLOYMENT.md)本批次流程执行。审计根为本机忽略目录`~/cpcsoft/OCR/.maintenance-backups/2026-10-27-rc3/`，不上传Git或Release。

1. 旧构建App须先归档并核对清单/签名；现安装版与上次已审计清单一致，数据、两处1.0及现有2.0模型建立只读基线。
2. PR、main CI成功后从干净合并源构建；DMG仅App/运行时和许可，不含模型、扫描/笔记/API配置、日志、测试依赖或备份。包内SOURCE_COMMIT、前端构建摘要与tag实际提交必须一致。
3. 只读挂载新DMG，在全新隔离支持目录操作无模型提示/文件选择/合成OCR/阅读/ZIP保存/退出。只用现有已校验隔离2.0权重，不重新下载生产模型、不使用真实扫描或远程接口密钥。
4. 新包/说明/验收独立review后才建草稿；核对两资产digest/size、真实tag目标、prerelease和非Latest后公开；再用真实浏览器点击下载并独立公开回读hash。
5. 完成后复核现安装App/数据/模型不变、临时服务与端口退出；合成任务可恢复归档。实际包SHA、资产、CI、截图、下载及失败边界通过证据PR回填。

## 已知限制与撤回

沿用2.0预览的两项非阻断P2观察：退出信号量清理告警、原生sandbox文件诊断；未宣称修复。新包仍须检查无关键路径或保全失败；失败不公开。

Mac包仅ad-hoc签名，未Developer ID公证，不绕过Gatekeeper或浏览器拦截。仅此Mac硬件/系统的合成样本验收，不代表全新Mac、最低macOS14或全数据集质量。Windows不提供本次新包，CI Windows artifact不是发行或实机验收。

分发失败保留草稿；公开后异常醒目标记撤回并保留原tag/包，修复走新PR及新候选，不覆写旧资产。本次没有安装到本机，因此不执行本机回滚；既有App/数据/模型和旧公开rc.2均保留。详细步骤见DEPLOYMENT。
