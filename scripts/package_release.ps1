param(
    [string]$Version = (Get-Date -Format "yyyyMMdd-HHmm")
)

$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$packageRoot = Join-Path $projectRoot "release_packages"
$stageRoot = Join-Path $packageRoot "GrassGuy-Football-Designer-$Version"
$zipPath = Join-Path $packageRoot "GrassGuy-Football-Designer-$Version.zip"

if (Test-Path $stageRoot) {
    Remove-Item -LiteralPath $stageRoot -Recurse -Force
}

New-Item -ItemType Directory -Path $stageRoot -Force | Out-Null

$include = @(
    "app.py",
    "requirements.txt",
    "packages.txt",
    "README.md",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.tunnel.yml",
    "deploy_start_server.sh",
    ".dockerignore",
    ".env.example",
    ".streamlit",
    "assets",
    "scripts",
    "config",
    "src",
    "docs",
    "wechat-miniprogram",
    "knowledge",
    "reference_templates",
    "template_knowledge"
)

foreach ($item in $include) {
    $source = Join-Path $projectRoot $item
    if (-not (Test-Path $source)) {
        continue
    }
    $target = Join-Path $stageRoot $item
    if ((Get-Item $source).PSIsContainer) {
        Copy-Item -LiteralPath $source -Destination $target -Recurse -Force
    } else {
        Copy-Item -LiteralPath $source -Destination $target -Force
    }
}

foreach ($dir in @("output/images", "output/pdf", "output/excel", "logs")) {
    New-Item -ItemType Directory -Path (Join-Path $stageRoot $dir) -Force | Out-Null
}

Get-ChildItem -LiteralPath $stageRoot -Directory -Recurse -Filter "__pycache__" |
    Remove-Item -Recurse -Force

if (Test-Path $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}

Compress-Archive -Path (Join-Path $stageRoot "*") -DestinationPath $zipPath -Force

Write-Host "Release package created: $zipPath"
