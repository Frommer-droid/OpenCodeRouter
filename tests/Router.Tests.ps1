#requires -Version 7.0
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
Import-Module "$PSScriptRoot/../Router.Core.psm1" -Force -DisableNameChecking
function Assert($Condition,$Message) { if (!$Condition) { throw $Message } }
$pipeFixture = [IO.Path]::GetTempFileName()
try {
    $pipeConfig = @{controllerPipe='verge-mihomo';secretSource=$pipeFixture}
    foreach ($scalar in @('\\.\pipe\verge-mihomo-sidecar-release-test', "'\\.\pipe\verge-mihomo-sidecar-release-test'", '"\\\\.\\pipe\\verge-mihomo-sidecar-release-test"')) {
        Set-Content -LiteralPath $pipeFixture -Value "external-controller-pipe: $scalar"
        Assert ((Resolve-RouterControllerPipe $pipeConfig) -eq 'verge-mihomo-sidecar-release-test') 'Runtime pipe follows Clash upgrade for YAML scalar formats'
    }
    Set-Content -LiteralPath $pipeFixture -Value 'external-controller-pipe: \\.\pipe\verge-mihomo-service-next'
    Assert ((Resolve-RouterControllerPipe $pipeConfig) -eq 'verge-mihomo-service-next') 'Runtime pipe is reread after core mode changes'
    $pipeConfig.controllerPipe='custom-pipe'
    Assert ((Resolve-RouterControllerPipe $pipeConfig) -eq 'custom-pipe') 'Explicit custom pipe is preserved'
    $pipeConfig.controllerPipe='verge-mihomo'
    Set-Content -LiteralPath $pipeFixture -Value "external-controller-pipe: ''"
    Assert ((Resolve-RouterControllerPipe $pipeConfig) -eq 'verge-mihomo') 'Empty runtime pipe preserves legacy configuration'
    Set-Content -LiteralPath $pipeFixture -Value 'mixed-port: 7897'
    Assert ((Resolve-RouterControllerPipe $pipeConfig) -eq 'verge-mihomo') 'Older Clash without runtime pipe remains compatible'
    Set-Content -LiteralPath $pipeFixture -Value 'external-controller-pipe: \\remote\pipe\other'
    $rejected=$false
    try { Resolve-RouterControllerPipe $pipeConfig } catch { $rejected=$true }
    Assert $rejected 'Remote pipe paths must be rejected'
} finally { Remove-Item -LiteralPath $pipeFixture }
Assert (Test-ApiResponse 401 'application/json' '{"error":{}}') '401 reachable'
Assert (Test-ApiResponse 403 'application/json' '{"error":{"code":403}}') 'JSON 403 reachable'
Assert (!(Test-ApiResponse 403 'text/html' '<html>Your client does not have permission</html>')) 'HTML block rejected'
Assert (!(Test-ApiResponse 403 'application/json' '{}')) 'Unknown 403 rejected'
Assert (!(Test-ApiResponse 404 'text/html' '<html>Not found</html>')) '404 not API success'
Assert (!(Test-ApiResponse 429 'application/json' '{"error":{}}')) 'Rate limited excluded'
Assert (!(Test-ApiResponse 403 'application/json' '{"error":{"message":"User location is not supported"}}')) 'JSON geographical block rejected'
Assert (Test-RouterNodeExcluded @{excludedNodes=@('Тестовый узел — исключён')} 'Тестовый узел — исключён') 'Exact excluded node recognized'
Assert (!(Test-RouterNodeExcluded @{excludedNodes=@('Тестовый узел — исключён')} 'Тестовый узел — доступен')) 'Allowed node retained'
foreach ($node in @('🇷🇺 Россия ⭐','Россия 🚀','россия 2','России','Российская Федерация','Russia ⭐','RUSSIA-Moscow','Russian Federation','RU','ru-01','[RUS] Moscow','🇷🇺 Москва')) {
    Assert (Test-RouterNodeExcluded @{excludedNodes=@()} $node) "Russia must always be excluded: $node"
    Assert (Test-RouterNodeExcluded @{} $node) "Russia exclusion must not depend on configuration: $node"
}
foreach ($node in @('🇩🇪 Германия ⭐','🇧🇾 Беларусь','Brussels 🚀','Peru ⭐','Australia','Русский сервер в Германии','RUSSELL','TRUST')) {
    Assert (!(Test-RouterNodeExcluded @{excludedNodes=@()} $node)) "Other locations must remain allowed: $node"
}
Assert ((@(Get-AllowedRouterNodes @{excludedNodes=@()} @('Россия ⭐','🇩🇪 Германия ⭐','RU-01')) -join ',') -eq '🇩🇪 Германия ⭐') 'Russia filtered from selectable candidates'
Assert (@(Get-AllowedRouterNodes @{excludedNodes=@('Тестовый узел — исключён')} @('Тестовый узел — доступен','Тестовый узел — исключён')).Count -eq 1) 'Excluded node filtered from lists'
$russianOrder=@('🇩🇪 Германия','🇬🇧 Великобритания','🇦🇹 Австрия') | Sort-Object @{Expression={Get-RouterNodeAlphabeticalKey $_}},@{Expression={$_}}
Assert (($russianOrder -join ',') -eq '🇦🇹 Австрия,🇬🇧 Великобритания,🇩🇪 Германия') 'Node order must follow Russian location names, not flag country codes'
& (Get-Module Router.Core) {
    $script:deletedConnections=@()
    function Invoke-Controller($Config,$Method,$Route,$Body=$null) {
        if ($Method -eq 'GET' -and $Route -eq '/connections') {
            return @{connections=@(
                @{id='opencode-current';metadata=@{process='opencode.exe';processPath='C:\Tools\opencode.exe'};chains=@('Австрия','OpenCode-Location');rule='ProcessName';rulePayload='opencode.exe'},
                @{id='opencode-other-group';metadata=@{process='opencode.exe';processPath='C:\Tools\opencode.exe'};chains=@('DIRECT','Other-Group');rule='ProcessName';rulePayload='opencode.exe'},
                @{id='browser-current';metadata=@{process='chrome.exe';processPath='C:\Chrome\chrome.exe'};chains=@('Австрия','OpenCode-Location');rule='Match';rulePayload=''}
            )}
        }
        if ($Method -eq 'DELETE') { $script:deletedConnections += $Route; return }
        throw "Unexpected controller request: $Method $Route"
    }
    $closed=Disconnect-OpenCodeConnections @{group='OpenCode-Location'}
    if ($closed -ne 1 -or ($script:deletedConnections -join ',') -ne '/connections/opencode-current') {
        throw 'Only OpenCode connections routed through OpenCode-Location may be closed'
    }
}
& (Get-Module Router.Core) {
    function Get-RouterGroup($Config) { @{now=$script:selected;all=@('Б 🇺🇸','Bad','A','🇷🇺 Россия 🚀')} }
    function Set-RouterNode($Config,$Node) { if ($Node -notin @('A','Б 🇺🇸','Bad')) { throw 'missing' }; $script:selected=$Node }
    function Measure-RouterNode($Config,$Node) {
        $script:measurements += $Node
        if ($script:explode -and $Node -eq 'Б 🇺🇸') { throw 'controller gone during scan' }
        @{node=$Node;ip=$(if($Node -eq 'A'){'192.0.2.1'}elseif($Node -eq 'Bad'){''}else{'198.51.100.2'});ok=($Node -ne 'Bad' -and !$script:allBad);latencyMs=$(if($Node -eq 'A'){500}else{100});checkedUtc=[DateTime]::UtcNow.ToString('o')}
    }
    function Write-RouterResult($Context,$Result,$Reason) { }
    function Set-KnownGood($Context,$Result) { }
    function Save-RouterJson($Path,$Value) { }
    function Disconnect-OpenCodeConnections($Config) { $script:disconnects += $script:selected; return 1 }
    $ctx=@{Config=@{excludedNodes=@();autoSwitch=@{cooldownSeconds=300;minimumImprovementMs=100}};State=@{lastSwitchUtc='';lastKnownGoodNode='A'};StatePath='unused'}
    $script:selected='A';$script:explode=$false;$script:allBad=$false;$script:measurements=@();$script:disconnects=@()
    $scan=@(Invoke-RouterScan $ctx)
    if ($scan.Count -ne 3 -or $script:selected -ne 'A') { throw 'Full scan must test every node and restore the original selection' }
    if ($script:disconnects.Count) { throw 'Full scan must not close OpenCode connections' }
    $script:explode=$true
    try { $null=Invoke-RouterScan $ctx; throw 'Expected full scan failure' } catch { if ($_.ToString() -eq 'Expected full scan failure') { throw } }
    if ($script:selected -ne 'A') { throw 'Failed full scan must restore the original selection' }
    $script:explode=$false
    $r=Invoke-RouterSelection $ctx test 'Б 🇺🇸'
    if ($script:selected -ne 'A' -or !$r.ok) { throw 'Test must restore original Unicode selection' }
    if ($script:disconnects.Count) { throw 'Temporary test must not close OpenCode connections' }
    $ctx.Config.excludedNodes=@('Б 🇺🇸')
    try { $null=Invoke-RouterSelection $ctx test 'Б 🇺🇸'; throw 'Expected excluded node rejection' } catch { if ($_.ToString() -eq 'Expected excluded node rejection') { throw } }
    if ($script:selected -ne 'A') { throw 'Excluded manual selection must preserve original node' }
    $ctx.Config.excludedNodes=@()
    try { $null=Invoke-RouterSelection $ctx use Bad; throw 'Expected use failure' } catch { if ($_.ToString() -eq 'Expected use failure') { throw } }
    if ($script:selected -ne 'A') { throw 'Failed use must restore' }
    $script:disconnects=@()
    $r=Invoke-RouterSelection $ctx use 'Б 🇺🇸'
    if ($script:selected -ne 'Б 🇺🇸' -or ($script:disconnects -join ',') -ne 'Б 🇺🇸' -or $r.connectionsRestarted -ne 1) { throw 'Successful use must reconnect OpenCode after committing a new node' }
    $script:selected='A';$script:disconnects=@();$ctx.State.lastSwitchUtc=''
    $r=Invoke-RouterSelection $ctx auto ''
    if ($script:selected -ne 'Б 🇺🇸') { throw 'Auto must choose healthy faster node' }
    if (($script:disconnects -join ',') -ne 'Б 🇺🇸' -or $r.connectionsRestarted -ne 1) { throw 'Committed auto selection must reconnect OpenCode' }
    $script:selected='A';$ctx.State.lastSwitchUtc='';$script:explode=$true
    try { $null=Invoke-RouterSelection $ctx auto ''; throw 'Expected scan failure' } catch { if ($_.ToString() -eq 'Expected scan failure') { throw } }
    if ($script:selected -ne 'A') { throw 'Exception must restore' }
    $script:explode=$false;$script:allBad=$true
    try { $null=Invoke-RouterSelection $ctx auto ''; throw 'Expected no healthy nodes' } catch { if ($_.ToString() -eq 'Expected no healthy nodes') { throw } }
    if ($script:selected -ne 'A') { throw 'All failed must restore' }
    $script:allBad=$false;$ctx.State.lastSwitchUtc=[DateTime]::UtcNow.ToString('o')
    $r=Invoke-RouterSelection $ctx auto ''
    if ($script:selected -ne 'A') { throw 'Cooldown must preserve healthy node' }
    $ctx.State.lastSwitchUtc=[DateTime]::UtcNow
    $r=Invoke-RouterSelection $ctx auto ''
    if ($script:selected -ne 'A') { throw 'Deserialized UTC timestamp must preserve cooldown' }
    $ctx.Config.excludedNodes=@('A')
    $r=Invoke-RouterSelection $ctx auto ''
    if ($script:selected -eq 'A') { throw 'Excluded current node must not be retained by cooldown' }
    $ctx.Config.excludedNodes=@();$script:selected='A'
    $ctx.State.lastSwitchUtc=''
    $script:measurements=@()
    $r=Invoke-RouterSelection $ctx auto '' -DifferentIp
    if ($r.ip -eq '192.0.2.1') { throw 'DifferentIp must enforce changed external IP' }
    if (($script:measurements -join ',') -ne 'A,Bad,Б 🇺🇸') { throw "DifferentIp must try nodes alphabetically after current and stop at first healthy node: $($script:measurements -join ',')" }
    if ($r.connectionsRestarted -ne 1) { throw 'DifferentIp must reconnect OpenCode after committing a new node' }
    $script:selected='Bad';$script:measurements=@()
    $r=Invoke-RouterSelection $ctx auto '' -DifferentIp
    if ($script:selected -ne 'Б 🇺🇸' -or ($script:measurements -join ',') -ne 'Bad,Б 🇺🇸') { throw 'DifferentIp must continue after a failed middle node instead of restarting at the first node' }
    $script:selected='Б 🇺🇸';$script:measurements=@()
    $r=Invoke-RouterSelection $ctx auto '' -DifferentIp
    if ($script:selected -ne 'A' -or ($script:measurements -join ',') -ne 'Б 🇺🇸,A') { throw 'DifferentIp must wrap from the last alphabetical node to the first and stop' }
    $script:selected='A';$script:allBad=$true;$script:measurements=@()
    try { $null=Invoke-RouterSelection $ctx auto '' -DifferentIp; throw 'Expected no different IP candidate' } catch { if ($_.ToString() -eq 'Expected no different IP candidate') { throw } }
    if ($script:selected -ne 'A' -or ($script:measurements -join ',') -ne 'A,Bad,Б 🇺🇸') { throw 'DifferentIp must restore the original node after one unsuccessful full cycle' }
}
& (Get-Module Router.Core) {
    $script:selected='🇩🇪 Германия ⭐'
    $script:measurements=@()
    function Get-RouterGroup($Config) { @{now=$script:selected;all=@('🇷🇺 Россия ⭐','🇩🇪 Германия ⭐','🇬🇧 Великобритания 🚀','🇦🇹 Австрия ⭐')} }
    function Set-RouterNode($Config,$Node) { $script:selected=$Node }
    function Measure-RouterNode($Config,$Node) { $script:measurements += $Node; @{node=$Node;ok=$true} }
    function Write-RouterResult($Context,$Result,$Reason) { }
    $ctx=@{Config=@{excludedNodes=@()}}
    $scan=@(Invoke-RouterScan $ctx)
    if (($script:measurements -join ',') -ne '🇦🇹 Австрия ⭐,🇬🇧 Великобритания 🚀,🇩🇪 Германия ⭐') { throw 'Full scan must follow Russian country names, ignoring flags and current selection' }
    if ($script:selected -ne '🇩🇪 Германия ⭐') { throw 'Alphabetical scan must restore initial route' }
    $ctx.Config.excludedNodes=@('🇬🇧 Великобритания 🚀');$script:measurements=@()
    $scan=@(Invoke-RouterScan $ctx)
    if (($script:measurements -join ',') -ne '🇦🇹 Австрия ⭐,🇩🇪 Германия ⭐') { throw 'Alphabetical scan must omit excluded locations' }
    foreach ($command in @('use','test')) {
        $script:measurements=@();$rejected=$false
        try { $null=Invoke-RouterSelection $ctx $command '🇷🇺 Россия ⭐' } catch {
            if ($_.ToString() -notlike 'Node is excluded for OpenCode:*') { throw }
            $rejected=$true
        }
        Assert $rejected "Manual $command must reject Russia"
        Assert ($script:selected -eq '🇩🇪 Германия ⭐' -and !$script:measurements.Count) 'Rejected Russia must not be selected or measured'
    }
}
Write-Host 'PASS: health classifications, Unicode, alphabetical full scan and recovery, test/use recovery, auto, exceptions, all-failed, cooldown, different IP.'
$errors=$null;$tokens=$null
foreach ($file in @('OpenCodeRouter.ps1','Router.Core.psm1')) {
    $null=[Management.Automation.Language.Parser]::ParseFile((Join-Path "$PSScriptRoot/.." $file),[ref]$tokens,[ref]$errors)
    if ($errors.Count) { throw ($errors | Out-String) }
}
Write-Host 'PASS: PowerShell parser.'
