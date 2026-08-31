[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateNotNullOrEmpty()]
    [string]$SourceRoot,

    [Parameter(Mandatory)]
    [ValidateNotNullOrEmpty()]
    [string]$OutputRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Drawing

function Get-SourceFiles {
    param(
        [Parameter(Mandatory)][string]$Folder,
        [Parameter(Mandatory)][string]$GroupName
    )

    if (-not (Test-Path -LiteralPath $Folder -PathType Container)) {
        throw "Le dossier source '$GroupName' est introuvable : $Folder"
    }

    $files = @(Get-ChildItem -LiteralPath $Folder -File -Filter '*.png' | Sort-Object -Property Name)
    if ($files.Count -ne 44) {
        throw "Le dossier '$GroupName' doit contenir exactement 44 PNG. Trouvé : $($files.Count)."
    }

    return $files
}

function Get-CropRectangle {
    param(
        [Parameter(Mandatory)][int]$SourceWidth,
        [Parameter(Mandatory)][int]$SourceHeight,
        [Parameter(Mandatory)][int]$TargetWidth,
        [Parameter(Mandatory)][int]$TargetHeight
    )

    $targetRatio = $TargetWidth / $TargetHeight
    $sourceRatio = $SourceWidth / $SourceHeight

    if ($sourceRatio -ge $targetRatio) {
        $cropWidth = [Math]::Round($SourceHeight * $targetRatio)
        $cropHeight = $SourceHeight
        $cropX = [Math]::Floor(($SourceWidth - $cropWidth) / 2)
        $cropY = 0
    }
    else {
        $cropWidth = $SourceWidth
        $cropHeight = [Math]::Round($SourceWidth / $targetRatio)
        $cropX = 0
        # Les portraits sont cadrés sur le visage : préserver le haut de l'image
        # évite de couper les coiffures pour les sources plus étroites que la cible.
        $cropY = [Math]::Floor(($SourceHeight - $cropHeight) * 0.15)
    }

    return [System.Drawing.Rectangle]::new($cropX, $cropY, $cropWidth, $cropHeight)
}

function Save-Bmp24 {
    param(
        [Parameter(Mandatory)][System.Drawing.Image]$SourceImage,
        [Parameter(Mandatory)][int]$TargetWidth,
        [Parameter(Mandatory)][int]$TargetHeight,
        [Parameter(Mandatory)][string]$Destination
    )

    $crop = Get-CropRectangle -SourceWidth $SourceImage.Width -SourceHeight $SourceImage.Height -TargetWidth $TargetWidth -TargetHeight $TargetHeight
    $canvas = [System.Drawing.Bitmap]::new($TargetWidth, $TargetHeight, [System.Drawing.Imaging.PixelFormat]::Format24bppRgb)
    $canvas.SetResolution(200, 200)
    $graphics = [System.Drawing.Graphics]::FromImage($canvas)

    try {
        $graphics.CompositingMode = [System.Drawing.Drawing2D.CompositingMode]::SourceCopy
        $graphics.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
        $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
        $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
        $graphics.DrawImage($SourceImage, [System.Drawing.Rectangle]::new(0, 0, $TargetWidth, $TargetHeight), $crop.X, $crop.Y, $crop.Width, $crop.Height, [System.Drawing.GraphicsUnit]::Pixel)
        $canvas.Save($Destination, [System.Drawing.Imaging.ImageFormat]::Bmp)
    }
    finally {
        $graphics.Dispose()
        $canvas.Dispose()
    }
}

function Assert-Bmp24 {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][int]$ExpectedWidth,
        [Parameter(Mandatory)][int]$ExpectedHeight
    )

    $header = [System.IO.File]::ReadAllBytes($Path)
    if ($header.Length -lt 54 -or $header[0] -ne 0x42 -or $header[1] -ne 0x4D) {
        throw "Le fichier n'est pas un BMP valide : $Path"
    }
    if ([BitConverter]::ToInt32($header, 18) -ne $ExpectedWidth -or [BitConverter]::ToInt32($header, 22) -ne $ExpectedHeight) {
        throw "Dimensions BMP incorrectes : $Path"
    }
    if ([BitConverter]::ToUInt16($header, 28) -ne 24 -or [BitConverter]::ToUInt32($header, 30) -ne 0) {
        throw "Le BMP doit être RGB 24 bits non compressé : $Path"
    }
}

$resolvedSource = (Resolve-Path -LiteralPath $SourceRoot).Path
if (Test-Path -LiteralPath $OutputRoot) {
    throw "Le dossier de sortie existe déjà. Pour protéger les fichiers existants, choisissez un nouveau chemin : $OutputRoot"
}

$femaleFiles = Get-SourceFiles -Folder (Join-Path $resolvedSource 'F') -GroupName 'F'
$maleFiles = Get-SourceFiles -Folder (Join-Path $resolvedSource 'H') -GroupName 'H'

$overrideDirectory = Join-Path $OutputRoot 'override'
$docsDirectory = Join-Path $OutputRoot 'docs'
New-Item -ItemType Directory -Path $overrideDirectory -Force | Out-Null
New-Item -ItemType Directory -Path $docsDirectory -Force | Out-Null

$variants = @(
    [PSCustomObject]@{ Suffix = 'L'; Width = 210; Height = 330; Label = 'Grande' },
    [PSCustomObject]@{ Suffix = 'M'; Width = 169; Height = 266; Label = 'Icône' }
)

$manifest = [System.Collections.Generic.List[object]]::new()
foreach ($entry in @(
        [PSCustomObject]@{ OutputPrefix = 'F'; SourceGroup = 'F'; Gender = 2; Files = $femaleFiles },
        [PSCustomObject]@{ OutputPrefix = 'M'; SourceGroup = 'H'; Gender = 1; Files = $maleFiles }
    )) {
    for ($index = 0; $index -lt $entry.Files.Count; $index++) {
        $sourceFile = $entry.Files[$index]
        $portraitId = '{0}{1:D2}' -f $entry.OutputPrefix, ($index + 1)
        $sourceImage = [System.Drawing.Image]::FromFile($sourceFile.FullName)

        try {
            foreach ($variant in $variants) {
                $destination = Join-Path $overrideDirectory ("{0}{1}.bmp" -f $portraitId, $variant.Suffix)
                Save-Bmp24 -SourceImage $sourceImage -TargetWidth $variant.Width -TargetHeight $variant.Height -Destination $destination
                Assert-Bmp24 -Path $destination -ExpectedWidth $variant.Width -ExpectedHeight $variant.Height
            }
        }
        finally {
            $sourceImage.Dispose()
        }

        $manifest.Add([PSCustomObject]@{
                PortraitId = $portraitId
                SourceGroup = $entry.SourceGroup
                Gender = $entry.Gender
                SourceFile = $sourceFile.Name
                SourcePath = $sourceFile.FullName
                Large = "${portraitId}L.bmp"
                Medium = "${portraitId}M.bmp"
            })
    }
}

$manifest | Export-Csv -LiteralPath (Join-Path $docsDirectory 'portrait-index.csv') -NoTypeInformation -Encoding utf8

$luaLines = [System.Collections.Generic.List[string]]::new()
$luaLines.Add('-- BGEE/BG2EE portrait gender registration. Engine convention: 1 = male, 2 = female.')
$luaLines.Add('function addPortrait(name, gender)')
$luaLines.Add('    table.insert(portraits, {name, gender})')
$luaLines.Add('end')
foreach ($portrait in $manifest) {
    $luaLines.Add(("addPortrait('{0}', {1})" -f $portrait.PortraitId, $portrait.Gender))
}
Set-Content -LiteralPath (Join-Path $overrideDirectory 'M_BGPORT.lua') -Value $luaLines -Encoding ascii

$readme = @"
# BGEE Portrait Pack - Beamdog

Ce pack contient 88 portraits personnalisés pour Baldur's Gate: Enhanced Edition et Baldur's Gate II: Enhanced Edition.

## Nomenclature

- `F01` à `F44` : portraits féminins, issus du dossier source `F`.
- `M01` à `M44` : portraits masculins, issus du dossier source `H`.
- Suffixe `L` : 210 x 330 px (grande image).
- Suffixe `M` : 169 x 266 px (icône de la barre latérale).

Tous les fichiers sont des BMP RGB 24 bits non compressés. BGEE/BG2EE n'utilisent plus de fichier `S` pour les portraits personnalisés. `M_BGPORT.lua` inscrit explicitement chaque portrait dans la table interne du jeu (1 = homme, 2 = femme), afin que la sélection soit filtrée par genre. Son nom respecte la limite de 8 caractères imposée aux ressources Infinity Engine.

## Installation

1. Fermez le jeu.
2. Copiez **le contenu** du dossier `override` dans le dossier `override` de l'installation du jeu, à côté de `chitin.key` (créez-le s'il n'existe pas). Exemples Steam :
   - `Steam\steamapps\common\Baldur's Gate Enhanced Edition\override`
   - `Steam\steamapps\common\Baldur's Gate II Enhanced Edition\override`
3. Ne copiez pas les BMP dans `Portraits`, sinon le jeu les ajoute une seconde fois sans filtre de genre.
4. Relancez le jeu, puis choisissez le portrait dans la sélection normale de création de personnage.

Le même dossier `override` est compatible avec les deux jeux. En multijoueur, chaque joueur doit disposer des mêmes portraits et du même fichier Lua.

`docs\portrait-index.csv` conserve la correspondance entre chaque nom normalisé et son master source ; les masters ne sont ni renommés ni modifiés.
"@
Set-Content -LiteralPath (Join-Path $docsDirectory 'README_FR.md') -Value $readme -Encoding utf8

$outputFiles = @(Get-ChildItem -LiteralPath $overrideDirectory -File -Filter '*.bmp')
if ($outputFiles.Count -ne 176) {
    throw "Génération incomplète : $($outputFiles.Count) BMP produits au lieu de 176."
}

Write-Host "Pack généré avec succès : $OutputRoot"
Write-Host "Portraits : $($outputFiles.Count) BMP RGB 24 bits dans $overrideDirectory"
Write-Host "Index : $(Join-Path $docsDirectory 'portrait-index.csv')"
