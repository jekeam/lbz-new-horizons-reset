param(
    [string]$Python27 = "C:\Python27\python.exe"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Source = Join-Path $RepoRoot "mod_lbz_dynamic_reset.py"
$Pyc = Join-Path $RepoRoot "mod_lbz_dynamic_reset.pyc"

$GameVersion = "1.43.0.0"
$ReleaseName = "1.43"
$PackageName = "lbz_new_horizons_reset_1.43.mtmod"
$ModuleName = "mod_lbz_dynamic_reset_v037.pyc"
$ZipName = "lbz-new-horizons-reset.zip"

$BuildRoot = Join-Path $RepoRoot "_build\release_1.43"
$MtmodRoot = Join-Path $BuildRoot "mtmod"
$MtmodModsDir = Join-Path $MtmodRoot "res\scripts\client\gui\mods"
$PackagePath = Join-Path $BuildRoot $PackageName

$ReleaseRoot = Join-Path $RepoRoot "release\$ReleaseName"
$ReleasePayload = Join-Path $ReleaseRoot "payload"
$ReleaseModsDir = Join-Path $ReleasePayload "mods\$GameVersion"
$ReleaseZip = Join-Path $ReleaseRoot $ZipName

if (-not (Test-Path -LiteralPath $Python27)) {
    throw "Python 2.7 not found: $Python27"
}

Remove-Item -LiteralPath $BuildRoot -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $ReleaseRoot -Recurse -Force -ErrorAction SilentlyContinue

New-Item -ItemType Directory -Force -Path $MtmodModsDir | Out-Null
New-Item -ItemType Directory -Force -Path $ReleaseModsDir | Out-Null

& $Python27 -m py_compile $Source
Copy-Item -LiteralPath $Pyc -Destination (Join-Path $MtmodModsDir $ModuleName) -Force

& $Python27 -c "import os,zipfile; root=r'$MtmodRoot'; out=r'$PackagePath'; z=zipfile.ZipFile(out,'w',zipfile.ZIP_STORED); [z.write(os.path.join(dp,f), os.path.relpath(os.path.join(dp,f), root).replace('\\','/')) for dp,dn,fs in os.walk(root) for f in fs]; z.close()"

Copy-Item -LiteralPath $PackagePath -Destination (Join-Path $ReleaseModsDir $PackageName) -Force

if (Test-Path -LiteralPath $ReleaseZip) {
    Remove-Item -LiteralPath $ReleaseZip -Force
}

Compress-Archive -LiteralPath (Join-Path $ReleasePayload "mods") -DestinationPath $ReleaseZip -Force

Write-Output "MTMOD: $PackagePath"
Write-Output "Release: $ReleaseZip"
