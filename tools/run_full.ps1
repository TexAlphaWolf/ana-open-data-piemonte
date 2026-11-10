# The full measurement on your own computer, in Docker (no network, read-only root, no capabilities), from Windows
# PowerShell: how fast the ISTAT files are read and the indicators computed, and that the two implementations agree.
# Optional: -National "C:\path\POSAS_2026_it_Comuni.csv" also times reading the 27 MB file with all 7,896 Italian municipalities.
# Usage: .\tools\run_full.ps1 [-Sizes 10000,100000] [-RefMax 100000] [-Repeat 5] [-Draws 50] [-National FILE] [-Out results]
param(
    [string]$Sizes = "10000,100000",
    [int]$RefMax = 100000,
    [int]$Repeat = 5,
    [int]$Draws = 50,
    [string]$National = "",
    [string]$Out = "results"
)
# Windows PowerShell 5.1 turns anything a program writes on stderr into an error under "Stop": docker and odp print
# their progress there, so only the exit code is looked at.
$ErrorActionPreference = "Continue"
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$outFull = (Resolve-Path -LiteralPath $Out).Path

docker build -t odp .
if ($LASTEXITCODE -ne 0) { Write-Host "docker build failed"; exit 1 }

$mount = @()
$extra = @()
if ($National -ne "") {
    $natFull = (Resolve-Path -LiteralPath $National).Path
    $mount = @("-v", "$(Split-Path -Parent $natFull):/national:ro")
    $extra = @("--national", "/national/$(Split-Path -Leaf $natFull)")
}

Write-Host "== bench (sizes $Sizes, $Repeat runs each, $Draws random tables compared) =="
docker run --rm --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges --network none -v "${outFull}:/out" @mount odp bench --sizes $Sizes --ref-max $RefMax --repeat $Repeat --draws $Draws @extra --out /out
if ($LASTEXITCODE -ne 0) { Write-Host "bench failed (exit code $LASTEXITCODE)"; exit 1 }
Write-Host "Done. Send me $Out\bench.json, $Out\bench.md and $Out\summary.png."
