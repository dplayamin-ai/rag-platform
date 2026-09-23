#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Run the tier-2 (Docker) deferred verification suite on a machine that actually has Docker
    (phase-6 plan docs/12-appendix/05-phase6-implementation-kit-plan.md §8; items tracked in
    docs/12-appendix/09-deferred-verification-ledger.md). This is the Windows/PowerShell twin of
    tools/verify/run-deferred.sh for a Docker Desktop machine; the VDI this repository was authored
    on cannot run either one (no Docker/WSL) — see the root HANDOFF.md for the full hand-off
    procedure.

.DESCRIPTION
    1. Brings up deploy/compose/compose.lite.yaml (PostgreSQL, Qdrant, Valkey) with
       `docker compose ... up --wait`. If that file does not exist yet in this checkout (a later
       work package adds it), prints a warning and continues without it.
    2. Runs `uv run pytest -q -m "needs_docker"` (only tier-2 tests; needs_model/needs_gpu/
       needs_network stay excluded by the default pyproject.toml addopts).
    3. Writes a machine-readable result record to tools/verify/results/deferred-<UTC date>.json and
       the full pytest log next to it.
    4. Tears the compose stack back down (`down -v`), even if pytest failed.

.PARAMETER PytestArgs
    Extra arguments forwarded to pytest after `-m "needs_docker"`.

.EXAMPLE
    tools/verify/run-deferred.ps1
    tools/verify/run-deferred.ps1 -k qdrant

.NOTES
    Exit code: pytest's exit code, except 5 ("no tests collected") is remapped to 0 — nothing is
    marked needs_docker yet in this revision, which is expected, not a failure (same convention as
    `tools/dev.py test-deferred` and run-deferred.sh).
#>
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$PytestArgs = @()
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $Root

$ComposeFile = 'deploy/compose/compose.lite.yaml'
$ResultsDir = 'tools/verify/results'
$Date = (Get-Date).ToUniversalTime().ToString('yyyy-MM-dd')
$Out = Join-Path $ResultsDir "deferred-$Date.json"
$Log = Join-Path $ResultsDir "deferred-$Date.log"
New-Item -ItemType Directory -Force -Path $ResultsDir | Out-Null

$ComposeUsed = $false
if (Test-Path $ComposeFile) {
    Write-Host "+ docker compose -f $ComposeFile up --wait"
    docker compose -f $ComposeFile up --wait
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose up failed with exit code $LASTEXITCODE"
    }
    $ComposeUsed = $true
}
else {
    Write-Warning "$ComposeFile does not exist yet (phase-6 plan section 8 work package not landed)."
    Write-Warning 'Proceeding without Docker services; a needs_docker test that actually needs them will fail loudly, not silently pass.'
}

$Code = 1
try {
    Write-Host "+ uv run pytest -q -m `"needs_docker`" $($PytestArgs -join ' ')"
    & uv run pytest -q -m "needs_docker" @PytestArgs 2>&1 | Tee-Object -FilePath $Log
    $Code = $LASTEXITCODE
}
finally {
    if (Test-Path $ComposeFile) {
        Write-Host "+ docker compose -f $ComposeFile down -v"
        docker compose -f $ComposeFile down -v
    }
}

if ($Code -eq 5) {
    $Status = 'no_tests_collected'
    $EffectiveCode = 0
}
elseif ($Code -eq 0) {
    $Status = 'passed'
    $EffectiveCode = 0
}
else {
    $Status = 'failed'
    $EffectiveCode = $Code
}

$SummaryMatch = Select-String -Path $Log -Pattern '^[0-9]+ (passed|failed|error|deselected)' -ErrorAction SilentlyContinue | Select-Object -Last 1
$SummaryLine = if ($SummaryMatch) { $SummaryMatch.Line } else { '(no summary line found)' }

try { $PythonVersion = (& uv run python -c "import sys; print('.'.join(map(str, sys.version_info[:3])))") } catch { $PythonVersion = 'unknown' }
try { $UvVersion = (& uv --version) } catch { $UvVersion = 'unknown' }

$Result = [ordered]@{
    generated_at     = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    marker           = 'needs_docker'
    compose_file     = $ComposeFile
    compose_used     = $ComposeUsed
    pytest_exit_code = $Code
    status           = $Status
    summary_line     = "$SummaryLine"
    python_version   = "$PythonVersion"
    uv_version       = "$UvVersion"
    log_file         = $Log
}
$Result | ConvertTo-Json | Set-Content -Path $Out -Encoding utf8

Write-Host "result written to $Out"
exit $EffectiveCode
