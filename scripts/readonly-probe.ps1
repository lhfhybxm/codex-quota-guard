[CmdletBinding()]
param(
    [int]$TimeoutSeconds = 20
)

$ErrorActionPreference = 'Stop'

function Send-JsonLine {
    param(
        [Parameter(Mandatory)]
        [System.Diagnostics.Process]$Process,

        [Parameter(Mandatory)]
        [hashtable]$Message
    )

    $json = $Message | ConvertTo-Json -Depth 12 -Compress
    $Process.StandardInput.WriteLine($json)
    $Process.StandardInput.Flush()
}

function Receive-Response {
    param(
        [Parameter(Mandatory)]
        [System.Diagnostics.Process]$Process,

        [Parameter(Mandatory)]
        [string]$Id,

        [Parameter(Mandatory)]
        [int]$TimeoutSeconds
    )

    $deadline = [DateTimeOffset]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTimeOffset]::UtcNow -lt $deadline) {
        $remaining = [Math]::Max(1, [int]($deadline - [DateTimeOffset]::UtcNow).TotalMilliseconds)
        $readTask = $Process.StandardOutput.ReadLineAsync()
        if (-not $readTask.Wait($remaining)) {
            throw "Timed out waiting for app-server response '$Id'."
        }

        $line = $readTask.Result
        if ($null -eq $line) {
            throw "App-server closed stdout before response '$Id'."
        }

        try {
            $message = $line | ConvertFrom-Json -Depth 30
        }
        catch {
            continue
        }

        if ([string]$message.id -eq $Id) {
            if ($null -ne $message.error) {
                $safeCode = $message.error.code
                $safeMessage = [string]$message.error.message
                throw "App-server request '$Id' failed ($safeCode): $safeMessage"
            }
            return $message.result
        }
    }

    throw "Timed out waiting for app-server response '$Id'."
}

function Convert-Window {
    param($Window)

    if ($null -eq $Window) {
        return $null
    }

    [ordered]@{
        usedPercent       = $Window.usedPercent
        resetsAt         = $Window.resetsAt
        windowDurationMins = $Window.windowDurationMins
    }
}

$startInfo = [System.Diagnostics.ProcessStartInfo]::new()
$startInfo.FileName = 'codex'
$startInfo.ArgumentList.Add('app-server')
$startInfo.ArgumentList.Add('--listen')
$startInfo.ArgumentList.Add('stdio://')
$startInfo.UseShellExecute = $false
$startInfo.RedirectStandardInput = $true
$startInfo.RedirectStandardOutput = $true
$startInfo.RedirectStandardError = $true
$startInfo.CreateNoWindow = $true

$process = [System.Diagnostics.Process]::new()
$process.StartInfo = $startInfo

try {
    if (-not $process.Start()) {
        throw 'Failed to start Codex app-server.'
    }

    Send-JsonLine -Process $process -Message @{
        id = 'initialize'
        method = 'initialize'
        params = @{
            clientInfo = @{ name = 'codex-quota-guard-probe'; version = '0.1.0' }
            capabilities = @{ experimentalApi = $true }
        }
    }
    $null = Receive-Response -Process $process -Id 'initialize' -TimeoutSeconds $TimeoutSeconds
    Send-JsonLine -Process $process -Message @{ method = 'initialized' }

    Send-JsonLine -Process $process -Message @{
        id = 'rate-limits'
        method = 'account/rateLimits/read'
        params = $null
    }
    $rateLimits = Receive-Response -Process $process -Id 'rate-limits' -TimeoutSeconds $TimeoutSeconds

    Send-JsonLine -Process $process -Message @{
        id = 'usage'
        method = 'account/usage/read'
        params = $null
    }

    $usageSupported = $true
    $usage = $null
    $usageError = $null
    try {
        $usage = Receive-Response -Process $process -Id 'usage' -TimeoutSeconds $TimeoutSeconds
    }
    catch {
        $usageSupported = $false
        $usageError = $_.Exception.Message -replace '(?i)(bearer|authorization|cookie|token)\s*[:=]?\s*\S+', '$1=[REDACTED]'
    }

    $snapshot = $rateLimits.rateLimits
    $safeOutput = [ordered]@{
        probedAtUtc = [DateTimeOffset]::UtcNow.ToString('O')
        source = 'Codex App Server'
        operations = @('account/rateLimits/read', 'account/usage/read')
        inferenceOperationsInvoked = $false
        rateLimits = [ordered]@{
            planType = $snapshot.planType
            primary = Convert-Window $snapshot.primary
            secondary = Convert-Window $snapshot.secondary
            hasCredits = if ($null -ne $snapshot.credits) { $snapshot.credits.hasCredits } else { $null }
            creditsUnlimited = if ($null -ne $snapshot.credits) { $snapshot.credits.unlimited } else { $null }
            hasMultipleLimitBuckets = $null -ne $rateLimits.rateLimitsByLimitId
        }
        accountUsage = [ordered]@{
            supported = $usageSupported
            dailyBucketCount = if ($null -ne $usage.dailyUsageBuckets) { @($usage.dailyUsageBuckets).Count } else { $null }
            lifetimeTokensAvailable = $null -ne $usage.summary.lifetimeTokens
            error = $usageError
        }
    }

    $safeOutput | ConvertTo-Json -Depth 10
}
finally {
    if ($null -ne $process -and -not $process.HasExited) {
        $process.Kill($true)
        $process.WaitForExit(5000)
    }
    $process.Dispose()
}
