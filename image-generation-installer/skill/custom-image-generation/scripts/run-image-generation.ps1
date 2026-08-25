$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2.0

$scriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$cliPath = Join-Path $scriptDirectory "image_generation.py"
$appData = if ($env:APPDATA) {
    [string]$env:APPDATA
} else {
    Join-Path $HOME "AppData\Roaming"
}
$configPath = if ($env:IMAGE_GENERATION_CONFIG) {
    [string]$env:IMAGE_GENERATION_CONFIG
} else {
    Join-Path $appData "Codex Image Generation\image-generation.json"
}

$pythonExecutable = $null
if (Test-Path -LiteralPath $configPath -PathType Leaf) {
    try {
        $config = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($config.python_executable) {
            $pythonExecutable = [string]$config.python_executable
        }
    } catch {
        Write-Warning "无法读取生图 Skill 配置中的 Python 运行时信息，将尝试系统 Python 3。"
    }
}

if ($pythonExecutable -and (Test-Path -LiteralPath $pythonExecutable -PathType Leaf)) {
    & $pythonExecutable $cliPath @args
    exit $LASTEXITCODE
}

$pyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($pyLauncher) {
    & $pyLauncher.Source -3 --version *> $null
    if ($LASTEXITCODE -eq 0) {
        & $pyLauncher.Source -3 $cliPath @args
        exit $LASTEXITCODE
    }
}

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCommand) {
    $detectedVersion = & $pythonCommand.Source --version 2>&1
    if ($LASTEXITCODE -eq 0 -and "$detectedVersion" -match "Python 3") {
        & $pythonCommand.Source $cliPath @args
        exit $LASTEXITCODE
    }
}

Write-Error "未找到可用的 Python 3。请重新运行 Custom Image Generation 一键安装器。"
exit 1
