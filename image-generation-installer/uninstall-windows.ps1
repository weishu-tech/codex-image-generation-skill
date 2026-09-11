$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2.0
Set-Location -LiteralPath $PSScriptRoot

$manifestPath = Join-Path $PSScriptRoot "python-runtime.json"
$skillName = "custom-image-generation"
$legacySkillName = "ccws-image-generation"
$runtimeMarkerName = ".codex-image-generation-managed-python-runtime"
$assumeYes = $false
$refusedTargets = $false

foreach ($argument in $args) {
    switch ([string]$argument) {
        "--yes" { $assumeYes = $true }
        "-y" { $assumeYes = $true }
        default { throw "未知参数：$argument。可用参数：--yes" }
    }
}

if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
    throw "缺少 Python 运行时清单：$manifestPath"
}

$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$pythonVersion = [string]$manifest.version
$userHome = if ($env:USERPROFILE) {
    [string]$env:USERPROFILE
} elseif ($HOME) {
    [string]$HOME
} else {
    throw "无法确定当前用户目录，卸载已停止。"
}

function Get-NormalizedPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        throw "卸载目标路径不能为空。"
    }
    $expanded = [Environment]::ExpandEnvironmentVariables($Path)
    return [IO.Path]::GetFullPath($expanded)
}

function Test-SamePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Left,
        [Parameter(Mandatory = $true)]
        [string]$Right
    )

    return [string]::Equals(
        (Get-NormalizedPath -Path $Left).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar),
        (Get-NormalizedPath -Path $Right).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar),
        [StringComparison]::OrdinalIgnoreCase
    )
}

function Get-PathEntry {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    try {
        return Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    } catch [System.Management.Automation.ItemNotFoundException] {
        return $null
    }
}

function Test-ImageGenerationConfig {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    try {
        $configuration = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
        return ([string]$configuration.model -in @(
            "gpt-image-2",
            "gpt-image-2.5",
            "gpt-image-2.5-flare",
            "gpt-image-2.5-sunburst"
        ))
    } catch {
        return $false
    }
}

function Test-RuntimeMarker {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RuntimeRoot
    )

    $markerPath = Join-Path $RuntimeRoot $runtimeMarkerName
    try {
        $actual = ([string](Get-Content -LiteralPath $markerPath -Raw -Encoding UTF8)).Trim()
        return ($actual -eq "custom-image-generation:$pythonVersion")
    } catch {
        return $false
    }
}

$targets = New-Object System.Collections.Generic.List[object]
$seenTargets = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)

function Add-ExistingTarget {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Kind,
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $normalized = Get-NormalizedPath -Path $Path
    $entry = Get-PathEntry -Path $normalized
    if ($null -eq $entry) {
        return
    }
    if ($seenTargets.Add($normalized)) {
        $targets.Add([PSCustomObject]@{ Kind = $Kind; Path = $normalized }) | Out-Null
    }
}

function Remove-Target {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Kind,
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $entry = Get-PathEntry -Path $Path
    if ($null -eq $entry) {
        return
    }

    $isReparsePoint = (($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)
    if ($Kind -eq "配置" -or $isReparsePoint -or -not $entry.PSIsContainer) {
        Remove-Item -LiteralPath $Path -Force
    } else {
        Remove-Item -LiteralPath $Path -Recurse -Force
    }
}

function Remove-EmptyDirectory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    try {
        Remove-Item -LiteralPath $Path -Force -ErrorAction Stop
    } catch {
        # Keep non-empty or unavailable parent directories.
    }
}

$homePath = Get-NormalizedPath -Path $userHome
$modernSkill = Join-Path (Join-Path (Join-Path $homePath ".agents") "skills") $skillName
$legacySkill = Join-Path (Join-Path (Join-Path $homePath ".codex") "skills") $skillName
Add-ExistingTarget -Kind "Skill" -Path $modernSkill
Add-ExistingTarget -Kind "Skill" -Path $legacySkill
Add-ExistingTarget -Kind "旧版 Skill" -Path (Join-Path (Join-Path (Join-Path $homePath ".agents") "skills") $legacySkillName)
Add-ExistingTarget -Kind "旧版 Skill" -Path (Join-Path (Join-Path (Join-Path $homePath ".codex") "skills") $legacySkillName)

$codexHomePath = $null
if ($env:CODEX_HOME) {
    $codexHomePath = Get-NormalizedPath -Path ([string]$env:CODEX_HOME)
    Add-ExistingTarget -Kind "Skill" -Path (Join-Path (Join-Path $codexHomePath "skills") $skillName)
    Add-ExistingTarget -Kind "旧版 Skill" -Path (Join-Path (Join-Path $codexHomePath "skills") $legacySkillName)
}

$appData = if ($env:APPDATA) {
    [string]$env:APPDATA
} else {
    Join-Path (Join-Path $homePath "AppData") "Roaming"
}
$defaultConfig = Get-NormalizedPath -Path (Join-Path (Join-Path $appData "Codex Image Generation") "image-generation.json")
$configPath = if ($env:IMAGE_GENERATION_CONFIG) {
    Get-NormalizedPath -Path ([string]$env:IMAGE_GENERATION_CONFIG)
} else {
    $defaultConfig
}
$configEntry = Get-PathEntry -Path $configPath
if ($null -ne $configEntry) {
    if ((Test-SamePath -Left $configPath -Right $defaultConfig) -or (Test-ImageGenerationConfig -Path $configPath)) {
        Add-ExistingTarget -Kind "配置" -Path $configPath
    } else {
        Write-Warning "为避免误删，未识别的自定义配置文件不会删除：$configPath"
        $refusedTargets = $true
    }
}

$localAppData = if ($env:LOCALAPPDATA) {
    [string]$env:LOCALAPPDATA
} else {
    Join-Path (Join-Path $homePath "AppData") "Local"
}
$defaultPythonRoot = Join-Path (Join-Path $localAppData "Codex Image Generation") "Python"
$defaultRuntime = Get-NormalizedPath -Path (Join-Path $defaultPythonRoot $pythonVersion)
$runtimePath = if ($env:IMAGE_GENERATION_PYTHON_RUNTIME_ROOT) {
    Get-NormalizedPath -Path ([string]$env:IMAGE_GENERATION_PYTHON_RUNTIME_ROOT)
} else {
    $defaultRuntime
}
$runtimeEntry = Get-PathEntry -Path $runtimePath
if ($null -ne $runtimeEntry) {
    if ((Test-SamePath -Left $runtimePath -Right $defaultRuntime) -or (Test-RuntimeMarker -RuntimeRoot $runtimePath)) {
        Add-ExistingTarget -Kind "Python" -Path $runtimePath
    } else {
        Write-Warning "为避免误删，没有生图 Skill 安全标记的自定义 Python 目录不会删除：$runtimePath"
        $refusedTargets = $true
    }
}

if ($targets.Count -eq 0) {
    if ($refusedTargets) {
        Write-Host "未删除任何内容。请检查上面的安全提示。" -ForegroundColor Red
        exit 1
    }
    Write-Host "未检测到需要卸载的 Custom Image Generation 当前安装。"
    Write-Host "以下历史 Skill 备份不会删除："
    Write-Host "  - $(Join-Path (Join-Path $homePath '.agents') 'skill-backups')"
    Write-Host "  - $(Join-Path (Join-Path $homePath '.codex') 'skill-backups')"
    if ($codexHomePath) {
        Write-Host "  - $(Join-Path $codexHomePath 'skill-backups')"
    }
    exit 0
}

Write-Host "Custom Image Generation 卸载器"
Write-Host ""
Write-Host "将删除以下当前安装内容："
foreach ($target in $targets) {
    Write-Host "  - $($target.Kind)：$($target.Path)"
}
Write-Host ""
Write-Host "以下历史 Skill 备份不会删除："
Write-Host "  - $(Join-Path (Join-Path $homePath '.agents') 'skill-backups')"
Write-Host "  - $(Join-Path (Join-Path $homePath '.codex') 'skill-backups')"
if ($codexHomePath) {
    Write-Host "  - $(Join-Path $codexHomePath 'skill-backups')"
}
Write-Host ""
Write-Host "系统 Python、PATH、其他 Skill 和上述历史备份不会修改。"

if (-not $assumeYes) {
    $answer = Read-Host "确认卸载？输入 y 继续，直接回车取消"
    if ([string]$answer -notmatch '^(?i:y|yes)$') {
        Write-Host "已取消卸载，未删除任何内容。"
        exit 0
    }
}

$failure = $false
Write-Host ""
foreach ($target in $targets) {
    try {
        Remove-Target -Kind $target.Kind -Path $target.Path
        if ($null -ne (Get-PathEntry -Path $target.Path)) {
            throw "目标仍然存在"
        }
        Write-Host "已删除 $($target.Kind)：$($target.Path)"
    } catch {
        Write-Host "删除失败 $($target.Kind)：$($target.Path)`n$($_.Exception.Message)" -ForegroundColor Red
        $failure = $true
    }
}

Remove-EmptyDirectory -Path $defaultPythonRoot
Remove-EmptyDirectory -Path (Join-Path $localAppData "Codex Image Generation")
Remove-EmptyDirectory -Path (Join-Path $appData "Codex Image Generation")

if ($refusedTargets) {
    $failure = $true
}
if ($failure) {
    Write-Host "`n卸载未完全完成，请保留上面的错误信息。" -ForegroundColor Red
    exit 1
}

Write-Host "`n卸载完成。请重启 Codex，或新开一个 Codex 任务。" -ForegroundColor Green
Write-Host "可以关闭此窗口。"
exit 0
