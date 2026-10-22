import AppKit
import WebKit

private final class AppDelegate:
    NSObject,
    NSApplicationDelegate,
    WKNavigationDelegate,
    WKUIDelegate,
    WKDownloadDelegate
{
    private let localURL = URL(string: "http://127.0.0.1:3000/")!
    private var window: NSWindow!
    private var webView: WKWebView!
    private var loadingPanel: NSVisualEffectView!
    private var statusLabel: NSTextField!
    private var spinner: NSProgressIndicator!
    private var startProcess: Process?
    private var isTerminating = false

    private var runtimePath: String {
        Bundle.main.resourceURL?
            .appendingPathComponent("OCRStudioRuntime", isDirectory: true)
            .path ?? ""
    }

    private var supportPath: String {
        if let override = ProcessInfo.processInfo.environment["OCR_STUDIO_SUPPORT_DIR"],
           override.hasPrefix("/") {
            return override
        }
        let base = FileManager.default.urls(
            for: .applicationSupportDirectory,
            in: .userDomainMask
        ).first!
        return base
            .appendingPathComponent("墨析 OCR 工作台", isDirectory: true)
            .path
    }

    func applicationDidFinishLaunching(_ notification: Notification) {
        buildMenus()
        buildWindow()
        startLocalServices()
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        true
    }

    func applicationWillTerminate(_ notification: Notification) {
        isTerminating = true
        webView?.stopLoading()

        if let process = startProcess, process.isRunning {
            process.terminate()
        }

        runStopScript()
    }

    @objc private func reloadPage(_ sender: Any?) {
        if webView.isHidden {
            startLocalServices()
        } else {
            webView.reload()
        }
    }

    private func buildMenus() {
        let mainMenu = NSMenu()

        let appItem = NSMenuItem()
        mainMenu.addItem(appItem)
        let appMenu = NSMenu()
        appMenu.addItem(
            withTitle: "关于墨析 OCR 工作台",
            action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)),
            keyEquivalent: ""
        )
        appMenu.addItem(.separator())
        appMenu.addItem(
            withTitle: "退出墨析 OCR 工作台",
            action: #selector(NSApplication.terminate(_:)),
            keyEquivalent: "q"
        )
        appItem.submenu = appMenu

        let fileItem = NSMenuItem()
        mainMenu.addItem(fileItem)
        let fileMenu = NSMenu(title: "文件")
        fileMenu.addItem(
            withTitle: "关闭窗口",
            action: #selector(NSWindow.performClose(_:)),
            keyEquivalent: "w"
        )
        fileItem.submenu = fileMenu

        let viewItem = NSMenuItem()
        mainMenu.addItem(viewItem)
        let viewMenu = NSMenu(title: "显示")
        let reloadItem = NSMenuItem(
            title: "重新载入",
            action: #selector(reloadPage(_:)),
            keyEquivalent: "r"
        )
        reloadItem.target = self
        viewMenu.addItem(reloadItem)
        viewItem.submenu = viewMenu

        NSApp.mainMenu = mainMenu
    }

    private func buildWindow() {
        let frame = NSRect(x: 0, y: 0, width: 1320, height: 860)
        window = NSWindow(
            contentRect: frame,
            styleMask: [.titled, .closable, .miniaturizable, .resizable, .fullSizeContentView],
            backing: .buffered,
            defer: false
        )
        window.title = "墨析 OCR 工作台"
        window.titlebarAppearsTransparent = true
        window.titleVisibility = .hidden
        window.minSize = NSSize(width: 940, height: 640)
        window.isReleasedWhenClosed = false

        let rootView = NSView(frame: frame)
        rootView.autoresizingMask = [.width, .height]

        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .default()
        webView = WKWebView(frame: rootView.bounds, configuration: configuration)
        webView.autoresizingMask = [.width, .height]
        webView.navigationDelegate = self
        webView.uiDelegate = self
        webView.isHidden = true
        rootView.addSubview(webView)

        loadingPanel = NSVisualEffectView(frame: rootView.bounds)
        loadingPanel.autoresizingMask = [.width, .height]
        loadingPanel.material = .sidebar
        loadingPanel.blendingMode = .behindWindow
        loadingPanel.state = .active

        spinner = NSProgressIndicator()
        spinner.style = .spinning
        spinner.controlSize = .large
        spinner.translatesAutoresizingMaskIntoConstraints = false
        spinner.startAnimation(nil)

        statusLabel = NSTextField(labelWithString: "正在启动本机 OCR 引擎…")
        statusLabel.font = .systemFont(ofSize: 16, weight: .medium)
        statusLabel.textColor = .secondaryLabelColor
        statusLabel.alignment = .center
        statusLabel.maximumNumberOfLines = 3
        statusLabel.translatesAutoresizingMaskIntoConstraints = false

        loadingPanel.addSubview(spinner)
        loadingPanel.addSubview(statusLabel)
        NSLayoutConstraint.activate([
            spinner.centerXAnchor.constraint(equalTo: loadingPanel.centerXAnchor),
            spinner.centerYAnchor.constraint(equalTo: loadingPanel.centerYAnchor, constant: -24),
            statusLabel.topAnchor.constraint(equalTo: spinner.bottomAnchor, constant: 18),
            statusLabel.centerXAnchor.constraint(equalTo: loadingPanel.centerXAnchor),
            statusLabel.widthAnchor.constraint(lessThanOrEqualToConstant: 620)
        ])
        rootView.addSubview(loadingPanel)

        window.contentView = rootView
        window.center()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    private func startLocalServices() {
        guard startProcess?.isRunning != true else { return }
        guard !runtimePath.isEmpty else {
            showStartupError("应用缺少 OCR 运行文件。请重新安装本机应用。")
            return
        }

        let startScript = runtimePath + "/start.sh"
        guard FileManager.default.isExecutableFile(atPath: startScript) else {
            showStartupError("找不到 OCR 运行文件。请重新安装本机应用。")
            return
        }

        loadingPanel.isHidden = false
        spinner.startAnimation(nil)
        statusLabel.stringValue = "正在启动本机 OCR 引擎…"
        webView.isHidden = true

        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/bin/zsh")
        process.arguments = [startScript]
        process.currentDirectoryURL = URL(fileURLWithPath: runtimePath, isDirectory: true)
        var environment = ProcessInfo.processInfo.environment
        environment["OCR_STUDIO_SUPPORT_DIR"] = supportPath
        process.environment = environment

        let output = Pipe()
        process.standardOutput = output
        process.standardError = output
        startProcess = process

        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            guard let self else { return }
            do {
                try process.run()
                process.waitUntilExit()
                let messageData = output.fileHandleForReading.readDataToEndOfFile()
                let message = String(data: messageData, encoding: .utf8) ?? ""
                DispatchQueue.main.async {
                    guard !self.isTerminating else { return }
                    self.startProcess = nil
                    if process.terminationStatus == 0 {
                        self.webView.load(URLRequest(url: self.localURL))
                    } else {
                        let detail = message.trimmingCharacters(in: .whitespacesAndNewlines)
                        self.showStartupError(
                            detail.isEmpty
                                ? "OCR 引擎未能启动。请双击项目里的“安装或修复 OCR 工作台”。"
                                : detail
                        )
                    }
                }
            } catch {
                DispatchQueue.main.async {
                    guard !self.isTerminating else { return }
                    self.startProcess = nil
                    self.showStartupError("OCR 引擎未能启动：\(error.localizedDescription)")
                }
            }
        }
    }

    private func showStartupError(_ message: String) {
        spinner.stopAnimation(nil)
        statusLabel.stringValue = message + "\n\n可按 ⌘R 重试。"
        loadingPanel.isHidden = false
        webView.isHidden = true
    }

    private func runStopScript() {
        guard !runtimePath.isEmpty else { return }
        let stopScript = runtimePath + "/stop.sh"
        guard FileManager.default.isExecutableFile(atPath: stopScript) else { return }

        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/bin/zsh")
        process.arguments = [stopScript]
        process.currentDirectoryURL = URL(fileURLWithPath: runtimePath, isDirectory: true)
        var environment = ProcessInfo.processInfo.environment
        environment["OCR_STUDIO_SUPPORT_DIR"] = supportPath
        process.environment = environment
        process.standardOutput = FileHandle.nullDevice
        process.standardError = FileHandle.nullDevice

        do {
            try process.run()
            process.waitUntilExit()
        } catch {
            NSLog("Unable to stop OCR Studio services: \(error.localizedDescription)")
        }
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        spinner.stopAnimation(nil)
        loadingPanel.isHidden = true
        webView.isHidden = false
    }

    func webView(
        _ webView: WKWebView,
        didFailProvisionalNavigation navigation: WKNavigation!,
        withError error: Error
    ) {
        if isExpectedNavigationCancellation(error) {
            return
        }
        showStartupError("网页暂时无法打开：\(error.localizedDescription)")
    }

    private func isExpectedNavigationCancellation(_ error: Error) -> Bool {
        let nsError = error as NSError
        return (nsError.domain == "WebKitErrorDomain" && nsError.code == 102) ||
            (nsError.domain == NSURLErrorDomain && nsError.code == NSURLErrorCancelled)
    }

    func webView(
        _ webView: WKWebView,
        decidePolicyFor navigationAction: WKNavigationAction,
        decisionHandler: @escaping (WKNavigationActionPolicy) -> Void
    ) {
        decisionHandler(navigationAction.shouldPerformDownload ? .download : .allow)
    }

    func webView(
        _ webView: WKWebView,
        decidePolicyFor navigationResponse: WKNavigationResponse,
        decisionHandler: @escaping (WKNavigationResponsePolicy) -> Void
    ) {
        let httpResponse = navigationResponse.response as? HTTPURLResponse
        let contentDisposition = httpResponse?
            .value(forHTTPHeaderField: "Content-Disposition")?
            .lowercased() ?? ""
        let isAttachment = contentDisposition.contains("attachment")
        decisionHandler(
            isAttachment || !navigationResponse.canShowMIMEType ? .download : .allow
        )
    }

    func webView(
        _ webView: WKWebView,
        navigationAction: WKNavigationAction,
        didBecome download: WKDownload
    ) {
        download.delegate = self
    }

    func webView(
        _ webView: WKWebView,
        navigationResponse: WKNavigationResponse,
        didBecome download: WKDownload
    ) {
        download.delegate = self
    }

    func download(
        _ download: WKDownload,
        decideDestinationUsing response: URLResponse,
        suggestedFilename: String,
        completionHandler: @escaping (URL?) -> Void
    ) {
        let panel = NSSavePanel()
        panel.title = "导出识别结果"
        panel.prompt = "保存"
        panel.nameFieldStringValue = suggestedFilename
        panel.canCreateDirectories = true
        panel.isExtensionHidden = false

        let finish: (NSApplication.ModalResponse) -> Void = { [weak self] result in
            guard result == .OK, let destination = panel.url else {
                completionHandler(nil)
                return
            }

            do {
                if FileManager.default.fileExists(atPath: destination.path) {
                    try FileManager.default.removeItem(at: destination)
                }
                completionHandler(destination)
            } catch {
                completionHandler(nil)
                self?.showDownloadError(error)
            }
        }

        if let parentWindow = webView.window {
            panel.beginSheetModal(for: parentWindow, completionHandler: finish)
        } else {
            panel.begin(completionHandler: finish)
        }
    }

    func download(
        _ download: WKDownload,
        didFailWithError error: Error,
        resumeData: Data?
    ) {
        if isExpectedNavigationCancellation(error) {
            return
        }
        showDownloadError(error)
    }

    private func showDownloadError(_ error: Error) {
        let alert = NSAlert()
        alert.alertStyle = .warning
        alert.messageText = "导出失败"
        alert.informativeText = error.localizedDescription
        alert.addButton(withTitle: "知道了")
        if let parentWindow = webView.window {
            alert.beginSheetModal(for: parentWindow)
        } else {
            alert.runModal()
        }
    }

    func webView(
        _ webView: WKWebView,
        runOpenPanelWith parameters: WKOpenPanelParameters,
        initiatedByFrame frame: WKFrameInfo,
        completionHandler: @escaping ([URL]?) -> Void
    ) {
        let panel = NSOpenPanel()
        panel.title = "选择要扫描的文件"
        panel.prompt = "选择"
        panel.canChooseFiles = true
        panel.canChooseDirectories = parameters.allowsDirectories
        panel.allowsMultipleSelection = parameters.allowsMultipleSelection
        panel.canCreateDirectories = false
        panel.resolvesAliases = true

        let finish: (NSApplication.ModalResponse) -> Void = { response in
            completionHandler(response == .OK ? panel.urls : nil)
        }
        if let parentWindow = webView.window {
            panel.beginSheetModal(for: parentWindow, completionHandler: finish)
        } else {
            panel.begin(completionHandler: finish)
        }
    }
}

let application = NSApplication.shared
private let delegate = AppDelegate()
application.delegate = delegate
application.setActivationPolicy(.regular)
application.run()
