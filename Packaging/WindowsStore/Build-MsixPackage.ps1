<#
.SYNOPSIS
  Packages a cooked Win64 build of Cris Cyborg Boxing into an MSIX package
  for Microsoft Store submission.

.DESCRIPTION
  This script assumes you have already produced a packaged Win64 build with
  Unreal Engine's RunUAT BuildCookRun (see README.md in this folder), and
  that the Windows 10/11 SDK (which provides MakeAppx.exe and
  SignTool.exe) is installed.

.PARAMETER BuildDirectory
  Path to the cooked/packaged Win64 build output (the folder containing
  CrisCyborgBoxing.exe).

.PARAMETER OutputPackage
  Path to write the resulting .msix package to.

.PARAMETER CertificatePath
  Optional path to a .pfx code-signing certificate used to self-sign the
  package for local testing. Store submissions are re-signed by Microsoft,
  so this is only required for sideloading/local testing.
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$BuildDirectory,

    [Parameter(Mandatory = $true)]
    [string]$OutputPackage,

    [string]$CertificatePath
)

$ErrorActionPreference = "Stop"
$PackagingRoot = $PSScriptRoot
$StagingDir = Join-Path $env:TEMP "CrisCyborgBoxing-MsixStaging"

if (Test-Path $StagingDir) {
    Remove-Item -Recurse -Force $StagingDir
}
New-Item -ItemType Directory -Path $StagingDir | Out-Null

Write-Host "Staging build output from $BuildDirectory ..."
Copy-Item -Recurse -Force (Join-Path $BuildDirectory "*") $StagingDir

Write-Host "Copying manifest and assets ..."
Copy-Item -Force (Join-Path $PackagingRoot "Package.appxmanifest") (Join-Path $StagingDir "AppxManifest.xml")
Copy-Item -Recurse -Force (Join-Path $PackagingRoot "Assets") $StagingDir

Write-Host "Building MSIX package with MakeAppx ..."
& makeappx.exe pack /d $StagingDir /p $OutputPackage /o
if ($LASTEXITCODE -ne 0) {
    throw "makeappx.exe failed with exit code $LASTEXITCODE"
}

if ($CertificatePath) {
    Write-Host "Signing package with $CertificatePath ..."
    & signtool.exe sign /fd SHA256 /a /f $CertificatePath $OutputPackage
    if ($LASTEXITCODE -ne 0) {
        throw "signtool.exe failed with exit code $LASTEXITCODE"
    }
}

Write-Host "Done: $OutputPackage"
