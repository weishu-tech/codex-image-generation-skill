$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2.0
Set-Location -LiteralPath $PSScriptRoot

$manifestPath = Join-Path $PSScriptRoot "python-runtime.json"
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$pythonVersion = [string]$manifest.version
$runtimeMarkerName = ".codex-image-generation-managed-python-runtime"

$architecture = [string]$env:PROCESSOR_ARCHITECTURE
if ($env:PROCESSOR_ARCHITEW6432) {
    $architecture = [string]$env:PROCESSOR_ARCHITEW6432
}

switch ($architecture.ToUpperInvariant()) {
    "AMD64" { $runtimeArtifact = $manifest.windows.amd64 }
    "ARM64" { $runtimeArtifact = $manifest.windows.arm64 }
    default { throw "仅支持 64 位 Windows（AMD64 或 ARM64），当前架构：$architecture" }
}

$pythonFilename = [string]$runtimeArtifact.filename
$pythonSha256 = ([string]$runtimeArtifact.sha256).ToLowerInvariant()
$pythonRelativePath = [string]$manifest.windows.python_relative_path
$localAppData = if ($env:LOCALAPPDATA) {
    [string]$env:LOCALAPPDATA
} else {
    Join-Path $HOME "AppData\Local"
}
$pythonRuntimeRoot = if ($env:IMAGE_GENERATION_PYTHON_RUNTIME_ROOT) {
    [string]$env:IMAGE_GENERATION_PYTHON_RUNTIME_ROOT
} else {
    Join-Path $localAppData "Codex Image Generation\Python\$pythonVersion"
}
$pythonExecutable = Join-Path $pythonRuntimeRoot $pythonRelativePath

function Test-ManagedPython {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Executable
    )

    if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
        return $false
    }

    try {
        $detectedVersion = & $Executable -c "import ssl, sys, urllib.request; ssl.create_default_context(); print('.'.join(map(str, sys.version_info[:3])))" 2>$null
        $normalizedVersion = ([string]$detectedVersion).Trim()
        return ($LASTEXITCODE -eq 0 -and $normalizedVersion -eq $pythonVersion)
    } catch {
        return $false
    }
}

function Write-RuntimeMarker {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RuntimeRoot
    )

    $markerPath = Join-Path $RuntimeRoot $runtimeMarkerName
    Set-Content -LiteralPath $markerPath -Value "custom-image-generation:$pythonVersion" -Encoding UTF8
}

function Get-PythonArchive {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Destination
    )

    $candidates = @()
    if ($env:IMAGE_GENERATION_PYTHON_DOWNLOAD_URL) {
        $candidates += [string]$env:IMAGE_GENERATION_PYTHON_DOWNLOAD_URL
    } else {
        foreach ($templateValue in $manifest.download_url_templates) {
            $candidate = ([string]$templateValue).Replace("{version}", $pythonVersion).Replace("{filename}", $pythonFilename)
            $candidates += $candidate
        }
    }

    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

    foreach ($source in $candidates) {
        Write-Host "正在下载 Python ${pythonVersion}：$source"
        if (Test-Path -LiteralPath $Destination) {
            Remove-Item -LiteralPath $Destination -Force
        }

        try {
            if (Test-Path -LiteralPath $source -PathType Leaf) {
                Copy-Item -LiteralPath $source -Destination $Destination
            } elseif ($source.StartsWith("file:", [StringComparison]::OrdinalIgnoreCase)) {
                $localPath = ([Uri]$source).LocalPath
                Copy-Item -LiteralPath $localPath -Destination $Destination
            } else {
                Invoke-WebRequest -Uri $source -OutFile $Destination -UseBasicParsing -TimeoutSec 900
            }

            $actualSha256 = (Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash.ToLowerInvariant()
            if ($actualSha256 -eq $pythonSha256) {
                Write-Host "Python 安装包 SHA256 校验通过。"
                return
            }

            Write-Warning "下载文件 SHA256 校验失败，已拒绝使用该文件。期望：$pythonSha256；实际：$actualSha256"
        } catch {
            Write-Warning "下载源失败：$source`n$($_.Exception.Message)"
        }
    }

    throw "所有 Python 下载源均失败。请检查网络后重新运行安装器。"
}

function Install-ManagedPython {
    if (Test-ManagedPython -Executable $pythonExecutable) {
        Write-RuntimeMarker -RuntimeRoot $pythonRuntimeRoot
        Write-Host "已检测到生图 Skill 托管 Python ${pythonVersion}：$pythonRuntimeRoot"
        return
    }

    $runtimeParent = Split-Path -Parent $pythonRuntimeRoot
    New-Item -ItemType Directory -Path $runtimeParent -Force | Out-Null

    $temporaryRoot = Join-Path ([IO.Path]::GetTempPath()) ("image-generation-python-" + [Guid]::NewGuid().ToString("N"))
    $stagingRoot = "${pythonRuntimeRoot}.staging-$PID-$([Guid]::NewGuid().ToString('N'))"
    $backupPath = $null
    New-Item -ItemType Directory -Path $temporaryRoot -Force | Out-Null

    try {
        $archivePath = Join-Path $temporaryRoot $pythonFilename
        Get-PythonArchive -Destination $archivePath

        Expand-Archive -LiteralPath $archivePath -DestinationPath $stagingRoot -Force
        $stagingPython = Join-Path $stagingRoot $pythonRelativePath
        if (-not (Test-ManagedPython -Executable $stagingPython)) {
            throw "下载的 Python 运行时未通过启动验证，安装已停止。"
        }
        Write-RuntimeMarker -RuntimeRoot $stagingRoot

        if (Test-Path -LiteralPath $pythonRuntimeRoot) {
            $backupPath = "${pythonRuntimeRoot}.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')-$([Guid]::NewGuid().ToString('N').Substring(0, 8))"
            Move-Item -LiteralPath $pythonRuntimeRoot -Destination $backupPath
            Write-Host "原有异常运行时已备份到：$backupPath"
        }

        try {
            Move-Item -LiteralPath $stagingRoot -Destination $pythonRuntimeRoot
        } catch {
            if ($backupPath -and -not (Test-Path -LiteralPath $pythonRuntimeRoot) -and (Test-Path -LiteralPath $backupPath)) {
                Move-Item -LiteralPath $backupPath -Destination $pythonRuntimeRoot
            }
            throw
        }
        Write-Host "Python $pythonVersion 已安装到当前用户目录：$pythonRuntimeRoot"
    } finally {
        if (Test-Path -LiteralPath $temporaryRoot) {
            Remove-Item -LiteralPath $temporaryRoot -Recurse -Force
        }
        if (Test-Path -LiteralPath $stagingRoot) {
            Remove-Item -LiteralPath $stagingRoot -Recurse -Force
        }
    }
}

try {
    Install-ManagedPython

    $installerPath = Join-Path $PSScriptRoot "install.py"
    $installerArguments = @($installerPath, "--yes")
    if ($args.Count -eq 0) {
        $installerArguments += "--interactive"
    } else {
        $installerArguments += $args
    }
    $installerArguments += @("--python-executable", $pythonExecutable)

    & $pythonExecutable @installerArguments
    $installerExitCode = $LASTEXITCODE

    if ($installerExitCode -eq 0) {
        Write-Host "`nCustom Image Generation 安装完成，可以关闭此窗口。" -ForegroundColor Green
    } else {
        Write-Host "`n安装失败，请保留上面的错误信息。" -ForegroundColor Red
    }
    exit $installerExitCode
} catch {
    Write-Host "`n安装失败：$($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
