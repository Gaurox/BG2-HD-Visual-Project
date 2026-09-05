[CmdletBinding()]
param(
    [Parameter(Mandatory)] [ValidateSet('Test','Apply','Restore')] [string]$Action,
    [Parameter(Mandatory)] [string]$GameRoot,
    [string]$CompatibilityManifestPath,
    [string]$StatePath,
    [string]$TemplatePath,
    [ValidateSet('core-steam','ui-mainmenu-x4')] [string]$Owner = 'core-steam'
)

$ErrorActionPreference = 'Stop'
if (-not $CompatibilityManifestPath) { $CompatibilityManifestPath = Join-Path $PSScriptRoot '..\manifests\runtime-compatibility.json' }
function Resolve-Absolute([string]$Path) { (Resolve-Path -LiteralPath $Path -ErrorAction Stop).Path }
function Read-Json([string]$Path) { Get-Content -LiteralPath $Path -Raw -Encoding utf8 | ConvertFrom-Json }
function Get-Hash([string]$Path) { $sha=[Security.Cryptography.SHA256]::Create();try{([BitConverter]::ToString($sha.ComputeHash([IO.File]::ReadAllBytes($Path)))).Replace('-','')}finally{$sha.Dispose()} }
function Write-JsonAtomic([string]$Path, [object]$Value) {
    $directory = Split-Path -Parent $Path; New-Item -ItemType Directory -Path $directory -Force | Out-Null
    $temporary = Join-Path $directory ('.' + [IO.Path]::GetFileName($Path) + '.' + [Guid]::NewGuid().ToString('N') + '.tmp')
    [IO.File]::WriteAllText($temporary, ($Value | ConvertTo-Json -Depth 32), [Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $temporary -Destination $Path -Force
}
function Read-TextPreservingEncoding([string]$Path) {
    $bytes = [IO.File]::ReadAllBytes($Path)
    $encoding = [Text.UTF8Encoding]::new($false)
    $bomLength = 0
    if ($bytes.Length -ge 3 -and $bytes[0..2] -ceq @(0xEF,0xBB,0xBF)) { $encoding=[Text.UTF8Encoding]::new($true); $bomLength=3 }
    elseif ($bytes.Length -ge 2 -and $bytes[0..1] -ceq @(0xFF,0xFE)) { $encoding=[Text.UnicodeEncoding]::new($false,$true); $bomLength=2 }
    elseif ($bytes.Length -ge 2 -and $bytes[0..1] -ceq @(0xFE,0xFF)) { $encoding=[Text.UnicodeEncoding]::new($true,$true); $bomLength=2 }
    [PSCustomObject]@{ Text=$encoding.GetString($bytes,$bomLength,$bytes.Length-$bomLength); Encoding=$encoding; NewLine=if($bytes -contains 13){"`r`n"}else{"`n"} }
}
function Set-OwnedValues([string]$Path, [object]$Values) {
    $text = Read-TextPreservingEncoding $Path; $lines=[Collections.Generic.List[string]]::new(); $text.Text -split "`r?`n",0 | ForEach-Object { $lines.Add($_) }
    $records=[Collections.Generic.List[object]]::new()
    foreach($sectionProperty in $Values.PSObject.Properties) {
        $section=$sectionProperty.Name; $sectionStart=-1; for($i=0;$i -lt $lines.Count;$i++){if($lines[$i] -match '^\s*\[(.+?)\]\s*$' -and $Matches[1] -ieq $section){$sectionStart=$i;break}}
        if($sectionStart -lt 0){$lines.Add('');$lines.Add("[$section]");$sectionStart=$lines.Count-1}
        $sectionEnd=$lines.Count; for($i=$sectionStart+1;$i -lt $lines.Count;$i++){if($lines[$i] -match '^\s*\['){$sectionEnd=$i;break}}
        foreach($keyProperty in $sectionProperty.Value.PSObject.Properties) {
            $key=$keyProperty.Name; $newValue=[string]$keyProperty.Value; $found=-1
            for($i=$sectionStart+1;$i -lt $sectionEnd;$i++){if($lines[$i] -match ('^\s*'+[regex]::Escape($key)+'\s*=\s*(?<value>.*?)(?<comment>\s*[;#].*)?$')){$found=$i;break}}
            if($found -ge 0){$original=$lines[$found]; $comment=''; if($original -match ('^\s*'+[regex]::Escape($key)+'\s*=\s*.*?(?<comment>\s*[;#].*)?$')){$comment=$Matches.comment}; $lines[$found]="$key = $newValue$comment"; $records.Add([ordered]@{section=$section;key=$key;prior_exists=$true;prior_line=$original;applied_value=$newValue})}
            else {$lines.Insert($sectionEnd,"$key = $newValue");$sectionEnd++;$records.Add([ordered]@{section=$section;key=$key;prior_exists=$false;prior_line=$null;applied_value=$newValue})}
        }
    }
    $temporary="$Path.bg2hd.tmp"; [IO.File]::WriteAllText($temporary,($lines -join $text.NewLine),$text.Encoding); Move-Item -LiteralPath $temporary -Destination $Path -Force
    @($records)
}
function Restore-OwnedValues([string]$Path,[object[]]$Records) {
    $text=Read-TextPreservingEncoding $Path; $lines=[Collections.Generic.List[string]]::new();$text.Text -split "`r?`n",0|ForEach-Object{$lines.Add($_)}
    foreach($record in $Records){$sectionStart=-1;for($i=0;$i -lt $lines.Count;$i++){if($lines[$i] -match '^\s*\[(.+?)\]\s*$' -and $Matches[1] -ieq $record.section){$sectionStart=$i;break}};if($sectionStart-lt 0){continue};$sectionEnd=$lines.Count;for($i=$sectionStart+1;$i-lt$lines.Count;$i++){if($lines[$i]-match '^\s*\['){$sectionEnd=$i;break}};$found=-1;for($i=$sectionStart+1;$i-lt$sectionEnd;$i++){if($lines[$i]-match ('^\s*'+[regex]::Escape($record.key)+'\s*=\s*(?<value>.*?)(?:\s*[;#].*)?$')){$found=$i;break}};if($found-ge 0 -and $Matches.value.Trim() -eq $record.applied_value){if($record.prior_exists){$lines[$found]=$record.prior_line}else{$lines.RemoveAt($found)}}}
    $temporary="$Path.bg2hd.tmp";[IO.File]::WriteAllText($temporary,($lines -join $text.NewLine),$text.Encoding);Move-Item -LiteralPath $temporary -Destination $Path -Force
}

$gameRoot=Resolve-Absolute $GameRoot; $manifest=Read-Json (Resolve-Absolute $CompatibilityManifestPath); if(-not $StatePath){$StatePath=Join-Path $gameRoot 'bg2hd/state/renderer-config.json'}
$ini=Join-Path $gameRoot 'InfinityEngine-Enhancer.ini'; if($Action -eq 'Test'){if(-not(Test-Path -LiteralPath $ini)){throw 'InfinityEngine-Enhancer.ini absent.'};exit 0}
if($Action -eq 'Apply'){
    if(Test-Path -LiteralPath $StatePath){
        $existing=Read-Json $StatePath
        if($existing.owner -eq $Owner -and (Test-Path -LiteralPath $ini) -and $existing.applied_sha256 -eq (Get-Hash $ini)){exit 0}
    }
    $createdByBg2hd=$false
    $templateSha256=$null
    if(-not(Test-Path -LiteralPath $ini)){
        if(-not $TemplatePath){throw 'InfinityEngine-Enhancer.ini absent et aucun modele renderer fourni.'}
        $template=Resolve-Absolute $TemplatePath
        Copy-Item -LiteralPath $template -Destination $ini -ErrorAction Stop
        $createdByBg2hd=$true
        $templateSha256=Get-Hash $template
        if((Get-Hash $ini) -ne $templateSha256){throw 'Copie du modele renderer invalide.'}
    }
    $stateDirectory=Split-Path -Parent $StatePath;New-Item -ItemType Directory -Path $stateDirectory -Force|Out-Null
    $stateName=[IO.Path]::GetFileNameWithoutExtension($StatePath)
    $backupName=if($stateName -eq 'renderer-config'){'InfinityEngine-Enhancer.ini.before-bg2hd'}else{"InfinityEngine-Enhancer.ini.before-$stateName"}
    $backupPath=Join-Path $stateDirectory $backupName
    if(-not $createdByBg2hd){Copy-Item -LiteralPath $ini -Destination $backupPath -Force}
    $records=Set-OwnedValues $ini $manifest.owned_ini_keys.$Owner
    Write-JsonAtomic $StatePath ([ordered]@{schema_version=2;owner=$Owner;ini_path=$ini;records=$records;created_by_bg2hd=$createdByBg2hd;template_sha256=$templateSha256;backup_path=if($createdByBg2hd){$null}else{$backupPath};backup_sha256=if($createdByBg2hd){$null}else{(Get-Hash $backupPath)};applied_sha256=(Get-Hash $ini)})
    exit 0
}
if(-not(Test-Path -LiteralPath $StatePath)){throw 'Etat renderer absent.'}
$state=Read-Json $StatePath
if($state.created_by_bg2hd){
    if(-not(Test-Path -LiteralPath $state.ini_path)){exit 0}
    if((Get-Hash $state.ini_path) -eq $state.applied_sha256){Remove-Item -LiteralPath $state.ini_path;exit 0}
    Restore-OwnedValues $state.ini_path @($state.records)
    if((Get-Hash $state.ini_path) -eq $state.template_sha256){Remove-Item -LiteralPath $state.ini_path}
    exit 0
}
# A failed component Apply can trigger WeiDU rollback against a journal left by
# the previous lifecycle after Core already removed the INI. There is then
# nothing to restore, and hashing the missing file would only mask the primary
# error with a second exception.
if(-not(Test-Path -LiteralPath $state.ini_path -PathType Leaf)){exit 0}
if($state.backup_path -and (Test-Path -LiteralPath $state.backup_path) -and (Get-Hash $state.backup_path) -eq $state.backup_sha256 -and (Test-Path -LiteralPath $state.ini_path) -and (Get-Hash $state.ini_path) -eq $state.backup_sha256){exit 0}
if($state.backup_path -and (Test-Path -LiteralPath $state.backup_path) -and (Get-Hash $state.backup_path) -eq $state.backup_sha256 -and (Get-Hash $state.ini_path) -eq $state.applied_sha256){Copy-Item -LiteralPath $state.backup_path -Destination $state.ini_path -Force;exit 0}
Restore-OwnedValues $state.ini_path @($state.records);exit 0
