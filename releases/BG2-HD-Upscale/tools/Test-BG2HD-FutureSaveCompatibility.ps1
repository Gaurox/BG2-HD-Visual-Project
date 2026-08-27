[CmdletBinding()]
param(
    [string]$ReleaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path,
    [string]$SaveDirectory
)

$ErrorActionPreference = 'Stop'

function Require([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

function Get-Sha256([string]$Path) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash([IO.File]::ReadAllBytes($Path)))).Replace('-', '') }
    finally { $sha.Dispose() }
}

function Count-Ascii([byte[]]$Bytes, [string]$Needle) {
    $text = [Text.Encoding]::ASCII.GetString($Bytes)
    return [regex]::Matches($text, [regex]::Escape($Needle)).Count
}

function Count-SavSignature([string]$Path, [string]$Signature) {
    $file = [IO.File]::OpenRead($Path)
    $reader = [IO.BinaryReader]::new($file, [Text.Encoding]::ASCII, $true)
    $count = 0
    try {
        Require ([Text.Encoding]::ASCII.GetString($reader.ReadBytes(8)) -eq 'SAV V1.0') "Signature SAV invalide : $Path"
        while ($file.Position -lt $file.Length) {
            Require ($file.Length - $file.Position -ge 12) "Entree SAV tronquee : $Path"
            $nameLength = $reader.ReadUInt32()
            Require ($nameLength -ge 1 -and $nameLength -le 1024) "Nom d entree SAV invalide : $Path"
            [void]$reader.ReadBytes([int]$nameLength)
            $expectedLength = $reader.ReadUInt32()
            $compressedLength = $reader.ReadUInt32()
            Require ($compressedLength -le $file.Length - $file.Position) "Entree SAV hors limites : $Path"
            $compressed = $reader.ReadBytes([int]$compressedLength)
            $compressedStream = [IO.MemoryStream]::new($compressed, $false)
            $zlib = [IO.Compression.ZLibStream]::new($compressedStream, [IO.Compression.CompressionMode]::Decompress)
            $output = [IO.MemoryStream]::new()
            try { $zlib.CopyTo($output) }
            finally { $zlib.Dispose(); $compressedStream.Dispose() }
            $raw = $output.ToArray()
            $output.Dispose()
            Require ($raw.Length -eq $expectedLength) "Taille decompressee SAV invalide : $Path"
            $count += Count-Ascii $raw $Signature
        }
    }
    finally { $reader.Dispose(); $file.Dispose() }
    return $count
}

$release = (Resolve-Path -LiteralPath $ReleaseRoot).Path
$manifestRoot = if (Test-Path -LiteralPath (Join-Path $release 'manifests') -PathType Container) {
    Join-Path $release 'manifests'
} elseif (Test-Path -LiteralPath (Join-Path $release 'bg2hd\manifests') -PathType Container) {
    Join-Path $release 'bg2hd\manifests'
} else {
    throw "Manifestes BG2HD introuvables sous $release"
}
$runtimePath = Join-Path $manifestRoot 'runtime-compatibility.json'
$rendererManifestPath = Join-Path $manifestRoot 'renderer-bundle.json'
$luaPath = Join-Path $release 'bg2hd\renderer\override\M_IEEE.lua'
$runtime = Get-Content -LiteralPath $runtimePath -Raw -Encoding utf8 | ConvertFrom-Json
$renderer = Get-Content -LiteralPath $rendererManifestPath -Raw -Encoding utf8 | ConvertFrom-Json
$contract = $runtime.save_compatibility_contract

Require ($contract.scope -eq 'future-save-chains-from-vanilla-compatible-state') 'Perimetre de compatibilite des sauvegardes absent.'
Require ($contract.target -eq 'BG2EE Steam 2.7.3.0 vanilla') 'Cible vanilla des sauvegardes incorrecte.'
Require ($contract.eeex_extra_creature_marshalling -eq 'disabled') 'Le marshalling etendu EEex doit etre desactive.'
Require ($contract.forbidden_signature -eq 'X-BIV1.0') 'Signature EEex interdite non declaree.'
Require ($contract.legacy_save_policy -eq 'detect-only-no-automatic-migration') 'La politique des anciennes sauvegardes est incorrecte.'

$lua = Get-Content -LiteralPath $luaPath -Raw -Encoding utf8
$flagMatch = [regex]::Match($lua, '(?m)^\s*EEex_Debug_DisableExtraCreatureMarshalling\s*=\s*true\s*$')
$initMatch = [regex]::Match($lua, '(?m)^\s*EEex_InitLuaBindings\s*\(')
Require $flagMatch.Success 'Le garde de compatibilite des sauvegardes manque dans M_IEEE.lua.'
Require $initMatch.Success 'L initialisation du renderer manque dans M_IEEE.lua.'
Require ($flagMatch.Index -lt $initMatch.Index) 'Le garde de sauvegarde doit etre defini avant l initialisation du renderer.'
Require (-not [regex]::IsMatch($lua, '(?m)^\s*EEex_Debug_DisableExtraCreatureMarshalling\s*=\s*false\s*$')) 'Le garde de sauvegarde est reinitialise a false.'

$luaRecord = @($renderer.files | Where-Object { $_.path -eq 'override/M_IEEE.lua' })
Require ($luaRecord.Count -eq 1) 'M_IEEE.lua doit avoir une entree unique dans le manifeste renderer.'
Require ((Get-Item -LiteralPath $luaPath).Length -eq [int64]$luaRecord[0].bytes) 'Taille M_IEEE.lua differente du manifeste.'
Require ((Get-Sha256 $luaPath) -eq $luaRecord[0].sha256) 'Hash M_IEEE.lua different du manifeste.'

if ($SaveDirectory) {
    $save = (Resolve-Path -LiteralPath $SaveDirectory).Path
    $gamPath = Join-Path $save 'BALDUR.GAM'
    $savPath = Join-Path $save 'BALDUR.SAV'
    Require (Test-Path -LiteralPath $gamPath -PathType Leaf) "BALDUR.GAM absent : $save"
    Require (Test-Path -LiteralPath $savPath -PathType Leaf) "BALDUR.SAV absent : $save"
    $gamCount = Count-Ascii ([IO.File]::ReadAllBytes($gamPath)) $contract.forbidden_signature
    $savCount = Count-SavSignature $savPath $contract.forbidden_signature
    Require ($gamCount + $savCount -eq 0) "Sauvegarde non vanilla-compatible : $gamCount bloc(s) dans BALDUR.GAM, $savCount dans BALDUR.SAV."
    Write-Output "SAVE_COMPATIBILITY_SCAN=PASSED; GAM=$gamCount; SAV=$savCount; PATH=$save"
}

Write-Output 'FUTURE_SAVE_COMPATIBILITY_CONTRACT=PASSED'
