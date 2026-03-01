# CortexCode Version Bump Script
# Usage: .\bump-version.ps1 [major|minor|patch]

param(
    [string]$type = "patch"
)

$packageJson = "package.json"
$content = Get-Content $packageJson -Raw | ConvertFrom-Json
$version = $content.version -split '\.'
$major = [int]$version[0]
$minor = [int]$version[1]
$patch = [int]$version[2]

switch ($type) {
    "major" { $major++; $minor = 0; $patch = 0 }
    "minor" { $minor++; $patch = 0 }
    "patch" { $patch++ }
}

$newVersion = "$major.$minor.$patch"
$content.version = $newVersion
$content | ConvertTo-Json -Depth 10 | Set-Content $packageJson

Write-Host "Bumped version to $newVersion"

# Also update the VSIX filename
$oldVsix = Get-ChildItem *.vsix -ErrorAction SilentlyContinue
if ($oldVsix) {
    $newVsix = "cortexcode-$newVersion.vsix"
    Rename-Item $oldVsix.FullName $newVsix -Force
    Write-Host "Renamed VSIX to $newVsix"
}
