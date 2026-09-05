# Re-applique 'Debug Mode'=1 dans Baldur.lua (BG2EE), que le jeu reecrit a chaque fermeture.
# Le mode debug active la console (Ctrl+Espace) et les commandes C:/CLUAConsole:.
#
# -Profile vise un dossier de profil autre que celui par defaut : chaque installation a son
# propre Baldur.lua sous Documents, et le mode debug de l'un ne vaut pas pour l'autre.
#   .\Enable-BG2Debug.ps1
#   .\Enable-BG2Debug.ps1 -Profile "Baldur's Gate II - Enhanced Edition - VANILLA"
param(
    [string]$Profile = "Baldur's Gate II - Enhanced Edition",
    [switch]$NoPause
)
$ErrorActionPreference = 'Stop'

$luaPath = Join-Path $env:USERPROFILE (Join-Path "Documents" (Join-Path $Profile "Baldur.lua"))

if (-not (Test-Path -LiteralPath $luaPath)) {
    Write-Host "Introuvable : $luaPath" -ForegroundColor Red
    if (-not $NoPause) { Read-Host "Appuie sur Entree pour fermer" }
    exit 1
}

$running = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -match 'Baldur|InfinityLoader' }
if ($running) {
    Write-Host "Le jeu tourne actuellement : Baldur.lua sera reecrit a sa fermeture." -ForegroundColor Yellow
    Write-Host "Relance ce script juste avant le PROCHAIN lancement si le mode debug ne prend pas." -ForegroundColor Yellow
}

$content = Get-Content -LiteralPath $luaPath -Raw
$debugLinePattern = "(?m)^SetPrivateProfileString\('Program Options','Debug Mode','\d+'\)\s*$"

if ($content -match $debugLinePattern) {
    $content = $content -replace $debugLinePattern, "SetPrivateProfileString('Program Options','Debug Mode','1')"
    Write-Host "Ligne 'Debug Mode' deja presente : valeur forcee a 1."
} else {
    $timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    Copy-Item -LiteralPath $luaPath -Destination "$luaPath.bak-avant-cheats-$timestamp"
    $marker = "SetPrivateProfileString('Program Options','3D Acceleration','1')"
    if ($content -match [regex]::Escape($marker)) {
        $content = $content -replace [regex]::Escape($marker), "$marker`r`nSetPrivateProfileString('Program Options','Debug Mode','1')"
    } else {
        $content = "SetPrivateProfileString('Program Options','Debug Mode','1')`r`n" + $content
    }
    Write-Host "Ligne 'Debug Mode' ajoutee (backup : $luaPath.bak-avant-cheats-$timestamp)."
}

Set-Content -LiteralPath $luaPath -Value $content -NoNewline

Write-Host ""
Write-Host "Mode debug actif au prochain lancement pour le profil : $Profile" -ForegroundColor Green
Write-Host "Console en jeu   : Ctrl+Espace"
Write-Host "Teleport groupe  : C:MoveToArea(""ARxxxx"")"
Write-Host "Reveler la zone  : C:ExploreArea()"
Write-Host ""
if (-not $NoPause) { Read-Host "Appuie sur Entree pour fermer" }
