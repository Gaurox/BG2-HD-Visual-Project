"""One-use migration: all map selection data out of historical compiler code."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
R=ROOT/'releases/BG2-HD-Upscale'
def replace(p,old,new):
    s=p.read_text(encoding='utf-8-sig')
    if new in s:return
    assert s.count(old)==1,(str(p),old,s.count(old))
    p.write_text(s.replace(old,new),encoding='utf-8',newline='\n')
p=R/'tools/New-BG2HD-ContentManifest.ps1';s=p.read_text(encoding='utf-8-sig')
if '$legacyMapSpecs = @(' in s:
    start=s.index('$legacyMapSpecs = @(');end=s.index('$candidateMapSpecs = @()',start)
    s=s[:start]+'# All map variants are now explicit data; historical component IDs remain stable.\n'+s[end:]
s=s.replace('$mapSpecs = @($legacyMapSpecs) + @($candidateMapSpecs)','$mapSpecs = @($candidateMapSpecs)')
assert '$legacyMapSpecs' not in s
p.write_text(s,encoding='utf-8',newline='\n')
replace(p,"    [string]$MapCandidatesPath = (Join-Path $PSScriptRoot '..\\manifests\\map-release-candidates.csv'),","    [string]$MapCandidatesPath = (Join-Path $PSScriptRoot '..\\manifests\\map-release-candidates.csv'),\n    [string]$MapAssembliesPath = (Join-Path $PSScriptRoot '..\\manifests\\map-release-assemblies.json'),")
replace(p,"    $candidateMapSpecs = @(Import-Csv", "    & python (Join-Path $WorkspaceRoot 'pipeline/scripts/verify_map_release_candidates.py') --workspace-root $WorkspaceRoot --candidates $MapCandidatesPath --assemblies $MapAssembliesPath --metadata-only\n    Require ($LASTEXITCODE -eq 0) 'Acquired map selection / final water assembly verification failed.'\n    $candidateMapSpecs = @(Import-Csv")
replace(p,"            CandidateModel = [string]$_.model", "            CandidateModel = [string]$_.model\n            CatalogSourcePath = [string]$_.catalog_source_path")
replace(p,"$path = ([string]$spec.Path).Replace('\\', '/')", "$path = ([string]$spec.CatalogSourcePath).Replace('\\', '/')")
# The source snapshot may be frozen under a new run; the catalog identity is checked separately.
replace(p,"# bootstrap and explicit map candidates are compiled.","# explicit map candidates are compiled.")
replace(R/'tools/Test-BG2HD-Phase2.ps1',"    @('content.json', 'content.schema.json'),","    @('content.json', 'content.schema.json'),\n    @('map-release-assemblies.json', 'map-release-assemblies.schema.json'),")
replace(R/'tools/Test-BG2HD-Phase2.ps1',"$animationQaSchema =", "& python (Join-Path $workspace 'pipeline/scripts/verify_map_release_candidates.py') --workspace-root $workspace --content (Join-Path $ReleaseRoot 'manifests/content.json') --metadata-only\nRequire ($LASTEXITCODE -eq 0) 'Map projection / acquired QA / runtime contract verification failed.'\n\n$animationQaSchema =")
sync=R/'tools/Sync-BG2HD-PackageMetadata.ps1'
replace(sync,"    'content.json',", "    'content.json',\n    'map-release-candidates.csv',\n    'map-release-assemblies.json',")
replace(R/'tools/Validate-BG2HD-Assets.py',"map_tis = [entry for entry in maps if entry[\"source\"].upper().endswith(\".TIS\")]", "# Local water overlay TIS belong to their map component; count base TIS separately.\n    map_tis = [entry for entry in maps if Path(entry[\"source\"]).name.upper() == entry[\"area\"] + \".TIS\"]")
replace(R/'tools/Validate-BG2HD-Assets.py',"\"pvrz\": len(maps) - len(map_tis)", "\"pvrz\": sum(entry[\"source\"].upper().endswith(\".PVRZ\") for entry in maps), \"local_overlay_tis\": sum(entry[\"source\"].upper().endswith(\".TIS\") for entry in maps) - len(map_tis), \"wed\": sum(entry[\"source\"].upper().endswith(\".WED\") for entry in maps)")
# AR3000 final local overlays travel with the map; no dependency on old shared WTSWAM aliases.
replace(R/'tools/New-BG2HD-ComponentManifest.ps1',"$mapOverlayDependencies = @{\n    AR3000 = @(70, 80, 90, 95)\n}","$mapOverlayDependencies = @{} # Final map-local overlays are packaged with their map.")
# Exercise all 64 promoted map assemblies in the archive installation/rollback fixture.
replace(R/'tests/Test-BG2HD-Phase4Archive.ps1',"$componentIds=@(@(0,100,110,1000,1010,1020,1030,1040,1050,1060,1580)+@($animationSamples|ForEach-Object{[int]$_.component_id})|Sort-Object -Unique)","$mapAssemblies=(Get-Content -LiteralPath (Join-Path $game 'bg2hd/manifests/map-release-assemblies.json') -Raw -Encoding utf8|ConvertFrom-Json).variants\n        $mapSamples=@($mapAssemblies|Where-Object{$_.frozen_assembly})\n        Require ($mapSamples.Count-eq64) 'Final map sample set incomplete.'\n        $componentIds=@(@(0,100,110,1000,1010,1020,1030,1040,1050,1060,1580)+@($animationSamples|ForEach-Object{[int]$_.component_id})+@($mapSamples|ForEach-Object{[int]$_.component_id})|Sort-Object -Unique)")
replace(R/'tests/Test-BG2HD-Phase4Archive.ps1',"'EnableMenuX2Test\\s*=\\s*false'", "'EnableMenuX2Test\\s*=\\s*false','EnableWaterOverlayRoute2\\s*=\\s*true','WaterOverlayStrength\\s*=\\s*1\\.00'")
replace(R/'tests/Test-BG2HD-ConfigEncoding.ps1',"Foreign = avant`r`n\"", "EnableWaterOverlayRoute2 = false ; original water`r`nWaterOverlayStrength = 0.27`r`nForeign = avant`r`n\"")
replace(R/'tests/Test-BG2HD-ConfigEncoding.ps1',"        Require ($text.Contains('; préserver éè')", "        Require ($text-match'(?m)^EnableWaterOverlayRoute2 = true ; original water\\r?$' -and $text-match'(?m)^WaterOverlayStrength = 1\\.00\\r?$') \"Water activation/strength missing: $i\"\n        Require ($text.Contains('; préserver éè')")
replace(R/'tests/Test-BG2HD-ConfigEncoding.ps1',"$text.Contains('EnableAreaAnimationX4 = false ; original')", "$text.Contains('EnableAreaAnimationX4 = false ; original') -and $text.Contains('EnableWaterOverlayRoute2 = false ; original water') -and $text.Contains('WaterOverlayStrength = 0.27')")
print('MAP COMPILER, PROJECTIONS, CONFIG AND ARCHIVE FIXTURES UPDATED')
