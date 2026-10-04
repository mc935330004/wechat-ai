param(
    [ValidateSet('start', 'stop', 'receipts')][string]$Action = 'start',
    [ValidateRange(1024, 65535)][int]$Port = 8997
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$testRuntime = Join-Path $projectRoot 'runtime'
$jarPath = Join-Path $projectRoot 'target\wechat-ai-0.0.1-SNAPSHOT.jar'
$pidPath = Join-Path $testRuntime 'probe-backend.pid'
$tokenPath = Join-Path $testRuntime 'probe-token.txt'
$baseUrl = "http://127.0.0.1:$Port"

if ($Action -eq 'stop') {
    if (-not (Test-Path -LiteralPath $pidPath)) { Write-Output 'No probe backend PID recorded.'; return }
    $testProcessId = [int](Get-Content -Raw -LiteralPath $pidPath)
    $testProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$testProcessId"
    if ($testProcess) {
        if ($testProcess.ExecutablePath -ne 'D:\java\jdk-17\bin\java.exe' -or
            -not $testProcess.CommandLine.Contains($jarPath) -or
            -not $testProcess.CommandLine.Contains("--server.port=$Port")) {
            throw 'Recorded PID does not match this probe backend; refusing to stop it.'
        }
        Stop-Process -Id $testProcessId
    }
    Remove-Item -LiteralPath $pidPath
    Write-Output 'Probe backend stopped. Token remains in the ignored runtime folder.'
    return
}

if ($Action -eq 'receipts') {
    $testToken = (Get-Content -Raw -LiteralPath $tokenPath).Trim()
    Invoke-RestMethod -Uri "$baseUrl/api/v1/dev/probe-messages" -Headers @{ 'X-Probe-Token' = $testToken } |
        ConvertTo-Json -Depth 8
    return
}

if (-not (Test-Path -LiteralPath $jarPath)) { throw 'Build the project with scripts/dev.ps1 -Action package first.' }
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
    throw "Port $Port is already in use. No existing service was stopped."
}
New-Item -ItemType Directory -Path $testRuntime -Force | Out-Null
if (-not (Test-Path -LiteralPath $tokenPath)) {
    $testToken = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
    Set-Content -LiteralPath $tokenPath -Value $testToken -NoNewline -Encoding ascii
}
$testToken = (Get-Content -Raw -LiteralPath $tokenPath).Trim()
if ($testToken -notmatch '^[A-Za-z0-9_-]{32,128}$') { throw 'Invalid probe token file.' }
$previousProbeEnabled = $env:WECHAT_PROBE_ENABLED
$previousProbeToken = $env:WECHAT_PROBE_TOKEN
try {
    $env:WECHAT_PROBE_ENABLED = 'true'
    $env:WECHAT_PROBE_TOKEN = $testToken
    $testProcess = Start-Process -FilePath 'D:\java\jdk-17\bin\java.exe' -WindowStyle Hidden -PassThru -WorkingDirectory $projectRoot `
        -ArgumentList @('-jar', ('"' + $jarPath + '"'), '--spring.profiles.active=dev', '--server.address=127.0.0.1', "--server.port=$Port") `
        -RedirectStandardOutput (Join-Path $testRuntime 'probe-backend.out.log') `
        -RedirectStandardError (Join-Path $testRuntime 'probe-backend.err.log')
    Set-Content -LiteralPath $pidPath -Value $testProcess.Id -Encoding ascii
} finally {
    $env:WECHAT_PROBE_ENABLED = $previousProbeEnabled
    $env:WECHAT_PROBE_TOKEN = $previousProbeToken
}
Write-Output "Probe backend starting at $baseUrl (PID $($testProcess.Id)); check /actuator/health."
