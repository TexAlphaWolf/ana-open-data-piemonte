# End to end inside the image, from Windows PowerShell: the ISTAT files that ship in the image are read and checked, the report
# is written and rebuilt exactly from its JSON, the tables are queried, the two implementations are compared and the benchmark runs
# small (read-only root, no capabilities, no network). Needs Docker Desktop.
# Usage: .\tools\docker_e2e.ps1 [-Image odp]
param([string]$Image = "odp")
$ErrorActionPreference = "Stop"

$id = Get-Random
$vol = "odp-e2e-$id"
$secure = @("--read-only", "--tmpfs", "/tmp", "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--network", "none", "-v", "${vol}:/data")

# Windows PowerShell 5.1 turns a program's message on stderr into an error under "Stop": the commands that are expected to
# fail run with errors not terminating, and only their exit code is looked at.
function Invoke-OdpCode([int[]]$Allowed, [string[]]$OdpArgs) {
    $old = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $out = docker run --rm @secure $Image @OdpArgs 2>&1
    $code = $LASTEXITCODE
    $ErrorActionPreference = $old
    if ($Allowed -notcontains $code) { throw "odp $OdpArgs exited with $code : $out" }
    ($out | Out-String)
}
function Invoke-Odp([string[]]$OdpArgs) { Invoke-OdpCode @(0) $OdpArgs }
function Read-Volume($path) {
    $out = docker run --rm --entrypoint cat -v "${vol}:/data" $Image $path 2>$null
    if ($LASTEXITCODE -ne 0) { throw "cannot read $path" }
    ($out | Out-String)
}
function Assert-Contains($text, $needle) { if ($text -notmatch [regex]::Escape($needle)) { throw "expected '$needle' in: $text" } }

try {
    docker volume create $vol | Out-Null
    docker run --rm --user 0 -v "${vol}:/data" --entrypoint chown $Image 10001 /data
    if ($LASTEXITCODE -ne 0) { throw "could not prepare the volume" }

    $chk = Invoke-Odp @("check-data")
    Assert-Contains $chk "1,180 municipalities, 107 provinces, 20 regions"
    Assert-Contains $chk "add up to the same population"

    $rep = Invoke-Odp @("report", "--out", "/data/out")
    Assert-Contains $rep "1,180 municipalities, 4,255,006 residents"
    Assert-Contains $rep "rank 8 of 20 regions"
    $md = Read-Volume "/data/out/report.md"
    Invoke-Odp @("render", "/data/out/report.json", "-o", "/data/out/again.md") | Out-Null
    if ((Read-Volume "/data/out/again.md") -ne $md) { throw "the report rebuilt from the JSON is not identical" }

    Assert-Contains (Invoke-Odp @("indicators", "--top", "3")) "006136 Ponzone"
    Assert-Contains (Invoke-Odp @("comune", "Biella")) "Biella (096004), province Biella"
    Assert-Contains (Invoke-Odp @("verify", "--draws", "5")) "8 of 8 comparisons agree with the literal implementation"

    Invoke-Odp @("bench", "--sizes", "200,400", "--ref-max", "400", "--repeat", "1", "--draws", "2", "--out", "/data/bench") | Out-Null
    Assert-Contains (Read-Volume "/data/bench/bench.json") '"ok": true'

    Invoke-OdpCode @(2) @("check-data", "--data", "/data/nope") | Out-Null
    Write-Host "docker end-to-end: OK"
}
finally {
    $ErrorActionPreference = "Continue"
    docker volume rm -f $vol 2>&1 | Out-Null
}
