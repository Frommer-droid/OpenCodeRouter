#requires -Version 7.0
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# QProcess starts pwsh without a terminal, so Windows can otherwise fall back
# to an OEM code page and irreversibly replace emoji before Python sees JSON.
$script:RouterUtf8Encoding = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = $script:RouterUtf8Encoding
[Console]::OutputEncoding = $script:RouterUtf8Encoding
$global:OutputEncoding = $script:RouterUtf8Encoding

function Resolve-RouterControllerPipe($Config) {
    $pipe = [string]$Config.controllerPipe
    # Legacy Clash configurations follow the active runtime pipe after upgrades.
    # Explicit custom pipes remain authoritative; never discover arbitrary pipes.
    if ($pipe -eq 'verge-mihomo' -and $Config.secretSource) {
        $line = Get-Content -LiteralPath $Config.secretSource | Where-Object { $_ -match '^external-controller-pipe:' } | Select-Object -First 1
        if ($line) {
            $value = ($line -replace '^external-controller-pipe:\s*', '').Trim()
            if ($value.StartsWith('"')) { $value = $value | ConvertFrom-Json }
            elseif ($value.StartsWith("'")) { $value = $value.Trim("'").Replace("''", "'") }
            else { $value = ($value -replace '\s+#.*$', '').Trim() }
            if ($value) { $pipe = $value }
        }
    }
    if ($pipe.StartsWith('\\.\pipe\')) { $pipe = $pipe.Substring(9) }
    if (!$pipe -or $pipe -match '[\\/\r\n]') { throw 'Invalid local controller pipe name.' }
    return $pipe
}

function Invoke-Controller($Config, [string]$Method, [string]$Route, $Body = $null) {
    $uri = [uri]$Config.controller
    if ($uri.Scheme -ne 'http' -or $uri.Host -ne '127.0.0.1') { throw 'Controller must be http://127.0.0.1:<port>.' }
    $secret = $Config.secret
    if (!$secret -and $Config.secretSource) {
        $line = Get-Content -LiteralPath $Config.secretSource | Where-Object { $_ -match '^secret:' } | Select-Object -First 1
        if ($line) {
            $secret = ($line -replace '^secret:\s*', '').Trim()
            if ($secret.StartsWith('"')) { $secret = $secret | ConvertFrom-Json }
            elseif ($secret.StartsWith("'")) { $secret = $secret.Trim("'").Replace("''", "'") }
        }
    }
    if ($Config.Contains('controllerPipe') -and $Config.controllerPipe) {
        $controllerPipe = Resolve-RouterControllerPipe $Config
        if (!( 'RouterPipeHttp' -as [type])) { Add-Type -Path (Join-Path $PSScriptRoot 'NamedPipeHttp.cs') }
        $jsonBody = if ($null -ne $Body) { $Body | ConvertTo-Json -Depth 30 -Compress } else { $null }
        try {
            $raw = [RouterPipeHttp]::Send($controllerPipe, $Method, $Route, $jsonBody, $secret, $Config.timeoutSeconds)
            if ($raw) { return ($raw | ConvertFrom-Json) }
            return
        } catch { throw "Named pipe controller request failed ($Method $Route). Check Clash; $($_.Exception.GetType().Name)." }
    }
    $args = @{ Uri = $Config.controller.TrimEnd('/') + $Route; Method = $Method; TimeoutSec = $Config.timeoutSeconds; NoProxy = $true; Headers = @{} }
    if ($secret) { $args.Headers.Authorization = "Bearer $secret" }
    if ($null -ne $Body) { $args.Body = $Body | ConvertTo-Json -Depth 30 -Compress; $args.ContentType = 'application/json; charset=utf-8' }
    try { Invoke-RestMethod @args } catch { throw "Controller request failed ($Method $Route). Check Clash and localhost controller; $($_.Exception.GetType().Name)." }
}

function Get-RouterGroup($Config) {
    $g = Invoke-Controller $Config GET ('/proxies/' + [uri]::EscapeDataString($Config.group))
    if ($g.type -ne 'Selector' -or !$g.all -or !$g.now) { throw 'OpenCode group is missing or is not a populated Selector.' }
    return $g
}

function Test-RouterNodeExcluded($Config, [string]$Node) {
    # Keep Russia unavailable even when a subscription renames its directions.
    if ($Node -match '🇷🇺|(?i)(?<![\p{L}\p{N}])(?:россия|россии|российская\s+федерация|russia|russian\s+federation|ru|rus)(?![\p{L}\p{N}])') { return $true }
    return $Config.Contains('excludedNodes') -and $Node -cin @($Config.excludedNodes)
}

function Get-AllowedRouterNodes($Config, $Nodes) {
    return @($Nodes | Where-Object { !(Test-RouterNodeExcluded $Config $_) })
}

function Get-RouterNodeAlphabeticalKey([string]$Node) {
    $trimmed = $Node.Trim()
    $russianName = [regex]::Match($trimmed, '[А-Яа-яЁё]')
    if ($russianName.Success) { return $trimmed.Substring($russianName.Index) }
    return $trimmed
}

function Set-RouterNode($Config, [string]$Node) {
    $g = Get-RouterGroup $Config
    if ($Node -cnotin $g.all) { throw "Unknown node: $Node. Run list; subscription may have changed." }
    $null = Invoke-Controller $Config PUT ('/proxies/' + [uri]::EscapeDataString($Config.group)) @{name=$Node}
    if ((Get-RouterGroup $Config).now -cne $Node) { throw 'Controller did not confirm selection.' }
}

function Get-RouterPropertyValue($InputObject, [string]$Name) {
    if ($null -eq $InputObject) { return $null }
    if ($InputObject -is [Collections.IDictionary]) {
        if ($InputObject.Contains($Name)) { return $InputObject[$Name] }
        return $null
    }
    $property = $InputObject.PSObject.Properties[$Name]
    if ($null -ne $property) { return $property.Value }
    return $null
}

function Disconnect-OpenCodeConnections($Config) {
    $snapshot = Invoke-Controller $Config GET '/connections'
    $connections = @(Get-RouterPropertyValue $snapshot 'connections')
    $closed = 0
    foreach ($connection in $connections) {
        $metadata = Get-RouterPropertyValue $connection 'metadata'
        $processName = [string](Get-RouterPropertyValue $metadata 'process')
        $processPath = [string](Get-RouterPropertyValue $metadata 'processPath')
        $processLeaf = if ($processPath) { [IO.Path]::GetFileName($processPath) } else { '' }
        $rulePayload = [string](Get-RouterPropertyValue $connection 'rulePayload')
        $chains = @(Get-RouterPropertyValue $connection 'chains')
        $isOpenCode = (
            $processName -ieq 'opencode.exe' -or
            $processLeaf -ieq 'opencode.exe' -or
            $rulePayload -ieq 'opencode.exe'
        )
        $usesRouterGroup = @($chains | Where-Object { $_ -ceq $Config.group }).Count -gt 0
        $id = [string](Get-RouterPropertyValue $connection 'id')
        if ($isOpenCode -and $usesRouterGroup -and $id) {
            $null = Invoke-Controller $Config DELETE ('/connections/' + [uri]::EscapeDataString($id))
            $closed++
        }
    }
    return $closed
}

function Test-ApiResponse([int]$Status, [string]$ContentType, [string]$Body) {
    if ($Body -match '(?i)user location is not supported|unsupported_country_region_territory|not available in your (country|region)|country.*not supported') { return $false }
    if ($Status -eq 403 -and ($ContentType -match 'html' -or $Body -match '(?i)<html|<!doctype|Your client does not have permission')) { return $false }
    if ($Status -in 200,400,401) { return $true }
    if ($Status -eq 403) {
        try { $data = $Body | ConvertFrom-Json -AsHashtable; return ($data -is [System.Collections.IDictionary] -and $data.Contains('error')) } catch { return $false }
    }
    return $false
}

function Get-HealthUrls($Config) {
    if ($Config.Contains('healthCheckUrls') -and $Config.healthCheckUrls.Count) { return @($Config.healthCheckUrls) }
    if (!$Config.healthProfiles.Contains($Config.healthProfile) -or !$Config.healthProfiles[$Config.healthProfile].Count) { throw 'Health profile must contain at least one HTTPS endpoint.' }
    return @($Config.healthProfiles[$Config.healthProfile])
}

function Measure-RouterNode($Config, [string]$Node) {
    $urls = @(Get-HealthUrls $Config)
    $proxyUri = [uri]$Config.testProxy
    if ($proxyUri.Scheme -ne 'http' -or $proxyUri.Host -ne '127.0.0.1') { throw 'Diagnostic proxy must use localhost HTTP.' }
    foreach ($url in @($Config.ipCheckUrls) + $urls) { if (([uri]$url).Scheme -ne 'https') { throw 'Checks require HTTPS.' } }
    $handler = [System.Net.Http.HttpClientHandler]::new()
    $handler.Proxy = [System.Net.WebProxy]::new($proxyUri)
    $handler.UseProxy = $true
    $handler.AllowAutoRedirect = $false
    $client = [System.Net.Http.HttpClient]::new($handler)
    $client.Timeout = [TimeSpan]::FromSeconds($Config.timeoutSeconds)
    $cancel = [System.Threading.CancellationTokenSource]::new([TimeSpan]::FromSeconds($Config.timeoutSeconds))
    $watch = [Diagnostics.Stopwatch]::StartNew()
    $checks = [Collections.Generic.List[object]]::new()
    $pending = @()
    $ip = ''
    try {
        # All endpoints start together, with one deadline per node. No keep-alive crosses nodes.
        foreach ($url in @($Config.ipCheckUrls) + $urls) {
            $pending += @{url=$url; isIp=($url -in $Config.ipCheckUrls); task=$client.GetAsync($url, $cancel.Token)}
        }
        while ($pending.Count -gt 0 -and (!$ip -or $checks.Count -lt $urls.Count)) {
            $index = [Threading.Tasks.Task]::WaitAny([Threading.Tasks.Task[]]@($pending | ForEach-Object { $_.task }))
            $item = $pending[$index]
            $pending = @($pending | Where-Object { $_ -ne $item })
            $response = $null
            try {
                $response = $item.task.GetAwaiter().GetResult()
                $body = $response.Content.ReadAsStringAsync($cancel.Token).GetAwaiter().GetResult()
                $status = [int]$response.StatusCode
                if ($item.isIp) {
                    $parsed = $null
                    if (!$ip -and $status -eq 200 -and [Net.IPAddress]::TryParse($body.Trim(), [ref]$parsed) -and $parsed.AddressFamily -eq [Net.Sockets.AddressFamily]::InterNetwork) { $ip = $parsed.ToString() }
                } else {
                    $checks.Add(@{url=$item.url; status=$status; ok=(Test-ApiResponse $status ([string]$response.Content.Headers.ContentType) $body)})
                }
            } catch {
                if (!$item.isIp) { $checks.Add(@{url=$item.url; status=0; ok=$false}) }
            } finally { if ($response) { $response.Dispose() } }
        }
    } finally { $watch.Stop(); $cancel.Cancel(); $client.Dispose(); $cancel.Dispose() }
    $good = !!$ip -and $checks.Count -gt 0 -and @($checks | Where-Object { !$_.ok }).Count -eq 0
    return @{node=$Node; ip=$ip; ok=$good; latencyMs=[int]$watch.ElapsedMilliseconds; checks=@($checks.ToArray()); checkedUtc=[DateTime]::UtcNow.ToString('o'); profile=$Config.healthProfile}
}

function Save-RouterJson([string]$Path, $Value) {
    $temp = $Path + '.tmp'
    try { $Value | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $temp -Encoding utf8; Move-Item -LiteralPath $temp -Destination $Path -Force }
    finally { if (Test-Path -LiteralPath $temp) { Remove-Item -LiteralPath $temp } }
}

function Write-RouterResult($Context, $Result, [string]$Reason) {
    $Context.State.results[$Result.node] = $Result
    $event = @{timestamp=[DateTime]::UtcNow.ToString('o'); node=$Result.node; ip=$Result.ip; health=$Result.ok; latencyMs=$Result.latencyMs; reason=$Reason}
    $event | ConvertTo-Json -Compress | Add-Content -LiteralPath (Join-Path $Context.Root ('logs/router-' + (Get-Date -Format yyyy-MM-dd) + '.log')) -Encoding utf8
    Save-RouterJson $Context.StatePath $Context.State
}

function Set-KnownGood($Context, $Result) {
    $Context.State.lastKnownGoodNode = $Result.node
    $Context.State.lastKnownGoodIp = $Result.ip
    $Context.State.lastSuccessUtc = $Result.checkedUtc
    Save-RouterJson $Context.StatePath $Context.State
}

function Invoke-RouterScan($Context) {
    $config = $Context.Config
    $initial = (Get-RouterGroup $config).now
    $eligible = @(Get-AllowedRouterNodes $config (Get-RouterGroup $config).all |
        Sort-Object @{Expression={Get-RouterNodeAlphabeticalKey $_}}, @{Expression={$_}})
    if (!$eligible.Count) { throw 'All nodes are excluded.' }
    $results = @()
    $needsRestore = $false
    try {
        foreach ($candidate in $eligible) {
            Write-Host "Testing: $candidate"
            if ($candidate -cne $initial) {
                $needsRestore = $true
                Set-RouterNode $config $candidate
            }
            $result = Measure-RouterNode $config $candidate
            Write-RouterResult $Context $result 'full scan'
            $results += $result
        }
        return @($results)
    } finally {
        if ($needsRestore) {
            try { Set-RouterNode $config $initial }
            catch { throw "RESTORE FAILED: select '$initial' in Clash manually. Controller unavailable or node removed." }
        }
    }
}

function Invoke-RouterSelection($Context, [string]$Command, [string]$Node, [switch]$DifferentIp) {
    $config = $Context.Config
    $initial = (Get-RouterGroup $config).now
    $restore = $initial
    $committed = $false
    try {
        if ($Command -in 'use','test') {
            if (Test-RouterNodeExcluded $config $Node) { throw "Node is excluded for OpenCode: $Node." }
            Set-RouterNode $config $Node
            $result = Measure-RouterNode $config $Node
            Write-RouterResult $Context $result $Command
            if ($Command -eq 'use') {
                if (!$result.ok) { throw "Node health failed: $Node. Original selection will be restored." }
                Set-KnownGood $Context $result
                $Context.State.lastSwitchUtc = [DateTime]::UtcNow.ToString('o')
                Save-RouterJson $Context.StatePath $Context.State
                $committed = $true
                $result.connectionsRestarted = if ($Node -cne $initial) { Disconnect-OpenCodeConnections $config } else { 0 }
            }
            return $result
        }
        $current = Measure-RouterNode $config $initial
        Write-RouterResult $Context $current 'auto baseline'
        $cooldown = [Math]::Max(300, [int]$config.autoSwitch.cooldownSeconds)
        if ($Context.State.lastSwitchUtc -and $current.ok -and !(Test-RouterNodeExcluded $config $initial) -and !$DifferentIp -and
            ([DateTime]::UtcNow - ([DateTime]$Context.State.lastSwitchUtc).ToUniversalTime()).TotalSeconds -lt $cooldown) {
            Set-KnownGood $Context $current
            $committed = $true
            return $current
        }
        $eligible = @(Get-AllowedRouterNodes $config (Get-RouterGroup $config).all)
        if (!$eligible.Count) { throw 'All nodes are excluded.' }
        if ($DifferentIp) {
            $ordered = @($eligible | Sort-Object @{Expression={Get-RouterNodeAlphabeticalKey $_}}, @{Expression={$_}})
            $initialIndex = -1
            for ($index = 0; $index -lt $ordered.Count; $index++) {
                if ($ordered[$index] -ceq $initial) { $initialIndex = $index; break }
            }
            $candidates = @()
            if ($initialIndex -ge 0) {
                for ($offset = 1; $offset -lt $ordered.Count; $offset++) {
                    $candidates += $ordered[($initialIndex + $offset) % $ordered.Count]
                }
            } else {
                $candidates = @($ordered)
            }
            foreach ($candidate in $candidates) {
                Write-Host "Testing: $candidate"
                Set-RouterNode $config $candidate
                $result = Measure-RouterNode $config $candidate
                Write-RouterResult $Context $result 'different IP sequence'
                if ($result.ok -and (!$current.ip -or $result.ip -ne $current.ip)) {
                    Set-KnownGood $Context $result
                    $Context.State.lastSwitchUtc = [DateTime]::UtcNow.ToString('o')
                    Save-RouterJson $Context.StatePath $Context.State
                    $committed = $true
                    $result.connectionsRestarted = Disconnect-OpenCodeConnections $config
                    return $result
                }
            }
            throw 'No healthy eligible node with a different IP found after a full cycle.'
        }
        $results = @()
        foreach ($candidate in $eligible) {
            Write-Host "Testing: $candidate"
            if ($candidate -ceq $initial) { $r = $current }
            else {
                Set-RouterNode $config $candidate
                $r = Measure-RouterNode $config $candidate
                Write-RouterResult $Context $r 'auto scan'
            }
            $results += $r
        }
        $valid = @($results | Where-Object { $_.ok -and (!$DifferentIp -or $_.ip -ne $current.ip) } | Sort-Object @{Expression={
            $candidateName=$_.node
            if ($config.Contains('preferredRegions') -and @($config.preferredRegions | Where-Object { $candidateName.Contains($_, [StringComparison]::OrdinalIgnoreCase) }).Count) { 0 } else { 1 }
        }},latencyMs)
        if (!$valid.Count) {
            # Prefer a freshly verified last-known-good, otherwise finally restores the original.
            $known = $Context.State.lastKnownGoodNode
            if ($known -and $known -cin (Get-RouterGroup $config).all -and !(Test-RouterNodeExcluded $config $known)) {
                Set-RouterNode $config $known
                $recheck = Measure-RouterNode $config $known
                Write-RouterResult $Context $recheck 'fallback recheck'
                if ($recheck.ok) { $restore = $known }
            }
            throw 'No healthy eligible node found; restoring a safe selection.'
        }
        $best = $valid[0]
        if (!$DifferentIp -and $current.ok -and $initial -cin $eligible -and
            ($current.latencyMs - $best.latencyMs) -lt [int]$config.autoSwitch.minimumImprovementMs) { $best = $current }
        Set-RouterNode $config $best.node
        $confirmed = Measure-RouterNode $config $best.node
        Write-RouterResult $Context $confirmed 'auto final verification'
        if (!$confirmed.ok -or ($DifferentIp -and $confirmed.ip -eq $current.ip)) { throw 'Selected route failed final verification; restoring original.' }
        $best = $confirmed
        Set-KnownGood $Context $best
        if ($best.node -cne $initial) { $Context.State.lastSwitchUtc = [DateTime]::UtcNow.ToString('o') }
        Write-RouterResult $Context $best 'auto selected'
        $committed = $true
        $best.connectionsRestarted = if ($best.node -cne $initial) { Disconnect-OpenCodeConnections $config } else { 0 }
        return $best
    } finally {
        if (!$committed) {
            try { Set-RouterNode $config $restore }
            catch { throw "RESTORE FAILED: select '$restore' in Clash manually. Controller unavailable or node removed." }
        }
    }
}

Export-ModuleMember -Function *
