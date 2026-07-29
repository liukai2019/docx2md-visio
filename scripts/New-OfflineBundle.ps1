[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Destination,
    [string]$PandocPath,
    [string]$NodePath,
    [string]$Convert2MermaidPath,
    [string]$WheelhousePath
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$destinationFull = [System.IO.Path]::GetFullPath($Destination)
if (Test-Path -LiteralPath $destinationFull) {
    throw "Destination already exists: $destinationFull"
}

New-Item -ItemType Directory -Path $destinationFull | Out-Null
$projectDestination = Join-Path $destinationFull "project"
New-Item -ItemType Directory -Path $projectDestination | Out-Null

$excluded = @(".git", ".pytest_cache", "__pycache__", ".venv")
Get-ChildItem -LiteralPath $projectRoot -Force | Where-Object {
    $_.Name -notin $excluded
} | Copy-Item -Destination $projectDestination -Recurse

function Copy-OptionalTool {
    param([string]$Source, [string]$Name)
    if (-not $Source) { return }
    $resolved = (Resolve-Path -LiteralPath $Source).Path
    $tools = Join-Path $destinationFull "tools"
    New-Item -ItemType Directory -Path $tools -Force | Out-Null
    Copy-Item -LiteralPath $resolved -Destination (Join-Path $tools $Name) -Recurse
}

Copy-OptionalTool -Source $PandocPath -Name "pandoc"
Copy-OptionalTool -Source $NodePath -Name "node"
Copy-OptionalTool -Source $Convert2MermaidPath -Name "convert2mermaid"
if ($WheelhousePath) {
    Copy-OptionalTool -Source $WheelhousePath -Name "wheelhouse"
}

$inventory = @(
    "Created: $(Get-Date -Format o)"
    "Project: docx2md-visio"
    "Pandoc bundled: $([bool]$PandocPath)"
    "Node bundled: $([bool]$NodePath)"
    "convert2mermaid bundled: $([bool]$Convert2MermaidPath)"
    "Wheelhouse bundled: $([bool]$WheelhousePath)"
)
Set-Content -LiteralPath (Join-Path $destinationFull "BUNDLE-INVENTORY.txt") `
    -Value $inventory -Encoding utf8

$zipPath = "$destinationFull.zip"
Compress-Archive -LiteralPath $destinationFull -DestinationPath $zipPath
Write-Output "Created $zipPath"

