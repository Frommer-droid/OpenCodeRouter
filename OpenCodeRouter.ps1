#requires -Version 7.0
[CmdletBinding()]
param(
    [Parameter(Position=0)][ValidateSet('status','list','scan','use','check','auto','test','menu')][string]$Command='status',
    [Parameter(Position=1)][string]$Node,
    [string]$ConfigPath=(Join-Path $PSScriptRoot 'OpenCodeRouter.config.json'),
    [switch]$DifferentIp,
    [switch]$Json
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'Router.Core.psm1') -Force -DisableNameChecking
$lock=$null
try {
    if (!(Test-Path -LiteralPath $ConfigPath)) {
        $templatePath=Join-Path $PSScriptRoot 'OpenCodeRouter.config.example.json'
        if (!(Test-Path -LiteralPath $templatePath)) { throw "Config not found: $ConfigPath" }
        Copy-Item -LiteralPath $templatePath -Destination $ConfigPath
    }
    $config=Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json -AsHashtable
    foreach ($key in 'controller','group','testProxy','timeoutSeconds','ipCheckUrls','healthProfiles','healthProfile','excludedNodes','autoSwitch') {
        if (!$config.Contains($key)) { throw "Missing config field: $key" }
    }
    if (!$config.Contains('secret')) { $config.secret='' }
    if (!$config.Contains('secretSource')) { $config.secretSource='' }
    if ($config.secretSource) { $config.secretSource=[Environment]::ExpandEnvironmentVariables([string]$config.secretSource) }
    if ([int]$config.timeoutSeconds -lt 1 -or [int]$config.timeoutSeconds -gt 30) { throw 'timeoutSeconds must be 1..30.' }
    foreach ($dir in 'logs','cache') { $null=New-Item -ItemType Directory -Path (Join-Path $PSScriptRoot $dir) -Force }
    # One lock for all CLI copies controlling the same selector.
    $hash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($config.controller+'/'+$config.group))).Substring(0,24)
    $lock=[Threading.Mutex]::new($false, "Local\OpenCodeRouter-$hash")
    $held=$false
    try { $held=$lock.WaitOne(0) } catch [Threading.AbandonedMutexException] { $held=$true }
    if (!$held) { throw 'Another router command is running. Wait for it to finish.' }
    $statePath=Join-Path $PSScriptRoot 'cache/state.json'
    $state=@{results=@{};lastKnownGoodNode='';lastKnownGoodIp='';lastSuccessUtc='';lastSwitchUtc=''}
    if (Test-Path -LiteralPath $statePath) { $saved=Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json -AsHashtable; foreach ($key in $saved.Keys) { $state[$key]=$saved[$key] } }
    $ctx=@{Config=$config;State=$state;StatePath=$statePath;Root=$PSScriptRoot}
    do {
        $action=$Command
        if ($Command -eq 'menu') {
            $g=Get-RouterGroup $config
            $availableNodes=@(Get-AllowedRouterNodes $config $g.all)
            Write-Host "`nOpenCode Router — $($g.now)`nA. Auto  S. Status  L. List  0. Exit"
            for ($i=0;$i -lt $availableNodes.Count;$i++) { Write-Host "$($i+1). $($availableNodes[$i])" }
            $choice=Read-Host 'Select'
            if ($choice -eq '0') { break }
            $number=0
            if ($choice -eq 'a') { $action='auto' }
            elseif ($choice -eq 's') { $action='status' }
            elseif ($choice -eq 'l') { $action='list' }
            elseif ([int]::TryParse($choice,[ref]$number) -and $number -ge 1 -and $number -le $availableNodes.Count) { $action='use';$Node=$availableNodes[$number-1] }
            else { continue }
        }
        $result=$null
        if ($action -eq 'list') {
            $g=Get-RouterGroup $config
            $rows=foreach ($name in @(Get-AllowedRouterNodes $config $g.all)) {
                $r=$state.results[$name]
                [pscustomobject]@{Node=$name;Selected=($name -ceq $g.now);IP=$(if($r){$r.ip}else{'—'});API=$(if(!$r){'untested'}elseif($r.ok){'OK'}else{'FAIL'});LatencyMs=$(if($r){$r.latencyMs}else{$null});CheckedUtc=$(if($r){$r.checkedUtc}else{''})}
            }
            if ($Json) { $rows | ConvertTo-Json -Depth 10 } else { $rows | Format-Table -AutoSize; Write-Host 'Cached checks; run test <node> or auto to refresh.' }
        } elseif ($action -eq 'scan') {
            $g=Get-RouterGroup $config
            $scanResults=@(Invoke-RouterScan $ctx)
            $rows=foreach ($r in $scanResults) {
                [pscustomobject]@{Node=$r.node;Selected=($r.node -ceq $g.now);IP=$(if($r.ip){$r.ip}else{'—'});API=$(if($r.ok){'OK'}else{'FAIL'});LatencyMs=$r.latencyMs;CheckedUtc=$r.checkedUtc}
            }
            if ($Json) { ConvertTo-Json -InputObject @($rows) -Depth 10 }
            else { $rows | Format-Table -AutoSize }
        } elseif ($action -in 'status','check') {
            $g=Get-RouterGroup $config
            $result=Measure-RouterNode $config $g.now
            Write-RouterResult $ctx $result $action
            if ($result.ok) { Set-KnownGood $ctx $result }
        } else {
            if ($action -in 'use','test' -and !$Node) { throw 'Provide the exact node name from list.' }
            $result=Invoke-RouterSelection $ctx $action $Node -DifferentIp:$DifferentIp
        }
        if ($result) {
            if ($Json) { $result | ConvertTo-Json -Depth 10 }
            else {
                Write-Host "`nOpenCode Router`nGroup: $($config.group)`nNode: $($result.node)`nDiagnostic external IP: $($result.ip)`nAPI health: $($result.ok)`nLatency: $($result.latencyMs) ms`nClash controller: OK"
                $result.checks | ForEach-Object { Write-Host "  $($_.url): HTTP $($_.status), OK=$($_.ok)" }
                if ($action -eq 'test') { Write-Host 'Original selection restored.' }
            }
            if (!$result.ok -and $Command -ne 'menu') { exit 2 }
        }
    } while ($Command -eq 'menu')
} catch { Write-Error $_ -ErrorAction Continue; exit 1 }
finally { if ($lock) { if ($held) { $lock.ReleaseMutex() }; $lock.Dispose() } }
