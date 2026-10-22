param(
    [switch]$SkipFrontendBuild
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$buildRoot = Join-Path $projectRoot "build\windows"
$cacheRoot = Join-Path $buildRoot "cache"
$stageRoot = Join-Path $buildRoot "stage"
$outputRoot = Join-Path $buildRoot "output"
$pythonVersion = "3.12.10"
$nodeVersion = "22.23.2"
$installerName = "MoxiOCR-Windows-x64-1.3.0-candidate.exe"
$installerFile = Join-Path $outputRoot $installerName
$pythonZip = Join-Path $cacheRoot "python-$pythonVersion-embed-amd64.zip"
$nodeZip = Join-Path $cacheRoot "node-v$nodeVersion-win-x64.zip"
$iconFile = Join-Path $PSScriptRoot "AppIcon.ico"

function Assert-LastExitCode([string]$label) {
    if ($LASTEXITCODE -ne 0) {
        throw "$label 失败，退出代码 $LASTEXITCODE"
    }
}

function Download-IfMissing([string]$url, [string]$destination, [string]$expected) {
    if (Test-Path $destination) {
        if ((Get-FileHash $destination -Algorithm SHA256).Hash.ToLower() -eq $expected) {
            return
        }
    }
    $partial = "$destination.part"
    Invoke-WebRequest -Uri $url -OutFile $partial -UseBasicParsing
    if ((Get-FileHash $partial -Algorithm SHA256).Hash.ToLower() -ne $expected) {
        throw "Runtime checksum failed: $destination"
    }
    Move-Item -Force $partial $destination
}

function Resolve-MakeNsis {
    $command = Get-Command "makensis.exe" -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }
    $candidates = @(
        (Join-Path ${env:ProgramFiles(x86)} "NSIS\makensis.exe"),
        (Join-Path $env:ProgramFiles "NSIS\makensis.exe")
    )
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return $candidate
        }
    }
    throw "没有找到 makensis.exe，请先安装 NSIS 3.x。"
}

function Resolve-Python312 {
    $launcher = Get-Command "py.exe" -ErrorAction SilentlyContinue
    if ($launcher) {
        & $launcher.Source -3.12 -c "import sys; assert sys.version_info[:2] == (3, 12)"
        Assert-LastExitCode "检查 Python 3.12"
        return @{
            Executable = $launcher.Source
            Prefix = @("-3.12")
        }
    }
    $python = Get-Command "python.exe" -ErrorAction SilentlyContinue
    if (-not $python) {
        throw "没有找到 Python 3.12 x64。"
    }
    & $python.Source -c "import sys; assert sys.version_info[:2] == (3, 12)"
    Assert-LastExitCode "检查 Python 3.12"
    return @{
        Executable = $python.Source
        Prefix = @()
    }
}

if (-not $SkipFrontendBuild) {
    if (-not (Get-Command "npm.cmd" -ErrorAction SilentlyContinue)) {
        throw "没有找到 npm，请先安装 Node.js 22。"
    }
    Push-Location $projectRoot
    try {
        & npm.cmd ci
        Assert-LastExitCode "npm ci"
        & npm.cmd run build
        Assert-LastExitCode "前端构建"
    }
    finally {
        Pop-Location
    }
}

$standaloneServer = Join-Path $projectRoot "dist\standalone\server.js"
$sourceCommit = & node (Join-Path $projectRoot "scripts\build_identity.mjs")
Assert-LastExitCode "核对前端源码版本"
if (-not (Test-Path $standaloneServer)) {
    throw "缺少 dist\standalone\server.js，请先构建前端。"
}
if (-not (Test-Path $iconFile)) {
    throw "缺少 windows\AppIcon.ico。"
}

if (Test-Path $installerFile) { throw "请先归档旧安装包: $installerFile" }
foreach ($target in @($stageRoot)) {
    if (Test-Path $target) {
        Remove-Item -Recurse -Force $target
    }
}
New-Item -ItemType Directory -Force -Path `
    $cacheRoot,
    (Join-Path $stageRoot "app"),
    (Join-Path $stageRoot "runtime\python\Lib\site-packages"),
    (Join-Path $stageRoot "runtime\node"),
    $outputRoot | Out-Null

Download-IfMissing `
    "https://www.python.org/ftp/python/$pythonVersion/python-$pythonVersion-embed-amd64.zip" `
    $pythonZip "4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3"
Download-IfMissing `
    "https://nodejs.org/dist/v$nodeVersion/node-v$nodeVersion-win-x64.zip" `
    $nodeZip "1177b4137ba5adaa56354ae40f1080c7450e8ae09cecb47da459d1c52ac99f97"

$pythonRuntime = Join-Path $stageRoot "runtime\python"
Expand-Archive -Path $pythonZip -DestinationPath $pythonRuntime -Force
Copy-Item (Join-Path $PSScriptRoot "python312._pth") `
    (Join-Path $pythonRuntime "python312._pth") -Force
Copy-Item (Join-Path $PSScriptRoot "backend_bootstrap.py") `
    (Join-Path $pythonRuntime "backend_bootstrap.py") -Force
Copy-Item (Join-Path $PSScriptRoot "windows_launcher.py") `
    (Join-Path $pythonRuntime "windows_launcher.py") -Force

$builderPython = Resolve-Python312
$builderPythonExecutable = $builderPython.Executable
$pipArguments = @()
$pipArguments += $builderPython.Prefix
$pipArguments += @(
    "-m",
    "pip",
    "install",
    "--disable-pip-version-check",
    "--no-compile",
    "--only-binary=:all:",
    "--target",
    (Join-Path $pythonRuntime "Lib\site-packages"),
    "-r",
    (Join-Path $PSScriptRoot "requirements-bootstrap.txt")
)
& $builderPythonExecutable @pipArguments
Assert-LastExitCode "安装 Windows 内嵌 Python 依赖"

$nodeTemp = Join-Path $buildRoot "node-extracted"
if (Test-Path $nodeTemp) {
    Remove-Item -Recurse -Force $nodeTemp
}
Expand-Archive -Path $nodeZip -DestinationPath $nodeTemp -Force
Copy-Item `
    (Join-Path $nodeTemp "node-v$nodeVersion-win-x64\node.exe") `
    (Join-Path $stageRoot "runtime\node\node.exe") `
    -Force
Copy-Item (Join-Path $nodeTemp "node-v$nodeVersion-win-x64\LICENSE") `
    (Join-Path $stageRoot "runtime\node\LICENSE") -Force
Copy-Item (Join-Path $projectRoot "LICENSE"), (Join-Path $projectRoot "THIRD_PARTY_NOTICES.md") `
    $stageRoot -Force

$backendTarget = Join-Path $stageRoot "app\backend"
New-Item -ItemType Directory -Force -Path $backendTarget | Out-Null
Copy-Item (Join-Path $projectRoot "backend\*") $backendTarget -Recurse -Force
Get-ChildItem $backendTarget -Directory -Filter "__pycache__" -Recurse |
    Remove-Item -Recurse -Force

Copy-Item `
    (Join-Path $projectRoot "dist\standalone") `
    (Join-Path $stageRoot "app\frontend") `
    -Recurse `
    -Force
Copy-Item `
    (Join-Path $PSScriptRoot "THIRD_PARTY_NOTICES.txt") `
    (Join-Path $stageRoot "THIRD_PARTY_NOTICES.txt") `
    -Force

$makeNsis = Resolve-MakeNsis
$finalSourceCommit = & node (Join-Path $projectRoot "scripts\build_identity.mjs")
Assert-LastExitCode "打包后复核源码版本"
if ($finalSourceCommit -ne $sourceCommit) { throw "打包期间源码改变，停止生成安装包。" }
$sourceCommit | Set-Content (Join-Path $stageRoot "SOURCE_COMMIT") -Encoding ascii
$launcherFile = Join-Path $stageRoot "MoxiOCRStudio.exe"
& $makeNsis `
    "/INPUTCHARSET" "UTF8" `
    "/DOUTPUT_FILE=$launcherFile" `
    "/DICON_FILE=$iconFile" `
    (Join-Path $PSScriptRoot "launcher.nsi")
Assert-LastExitCode "编译应用启动器"

& $makeNsis `
    "/INPUTCHARSET" "UTF8" `
    "/DSTAGE_FILES=$(Join-Path $stageRoot '*')" `
    "/DOUTPUT_FILE=$installerFile" `
    "/DICON_FILE=$iconFile" `
    (Join-Path $PSScriptRoot "installer.nsi")
Assert-LastExitCode "编译安装包"

$hash = Get-FileHash -Path $installerFile -Algorithm SHA256
"$($hash.Hash.ToLower())  $installerName" |
    Set-Content -Path "$installerFile.sha256" -Encoding ascii
Copy-Item `
    (Join-Path $PSScriptRoot "Windows安装说明.txt") `
    (Join-Path $outputRoot "Windows安装说明.txt") `
    -Force

Get-Item $installerFile, "$installerFile.sha256" |
    Select-Object FullName, Length, LastWriteTime
