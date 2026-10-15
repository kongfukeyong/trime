param(
    [Parameter(Mandatory=$true)][string]$JavaHome,
    [Parameter(Mandatory=$true)][string]$AndroidSdk,
    [string]$Gradle = "$PSScriptRoot/../gradlew.bat",
    [string]$OutputDir = "$PSScriptRoot/../../outputs",
    [string]$ProxyUrl = '',
    [switch]$RunTests
)
$ErrorActionPreference = 'Stop'
$env:JAVA_HOME = (Resolve-Path $JavaHome).Path
$env:ANDROID_HOME = (Resolve-Path $AndroidSdk).Path
$env:ANDROID_SDK_ROOT = $env:ANDROID_HOME
$env:Path = "$env:JAVA_HOME/bin;$env:Path"
if ($ProxyUrl) { $env:HTTPS_PROXY = $ProxyUrl }
& python "$PSScriptRoot/verify-wanxiang.py"
if ($LASTEXITCODE -ne 0) { throw 'Wanxiang resources missing or invalid; run download-wanxiang.py and import-wanxiang.py first' }
& "$PSScriptRoot/prepare-mvp-native.ps1"
if (!$?) { throw 'Native preparation failed' }
New-Item -ItemType Directory -Force $OutputDir | Out-Null
$OutputDir = (Resolve-Path $OutputDir).Path
Push-Location "$PSScriptRoot/.."
try {
    $tasks = @(':app:assembleDebug')
    if ($RunTests) { $tasks += ':app:testDebugUnitTest' }
    $proxyArgs = @()
    if ($ProxyUrl) {
        $proxyUri = [Uri]$ProxyUrl
        $proxyArgs = @("-Dhttps.proxyHost=$($proxyUri.Host)", "-Dhttps.proxyPort=$($proxyUri.Port)", "-Dhttp.proxyHost=$($proxyUri.Host)", "-Dhttp.proxyPort=$($proxyUri.Port)")
    }
    & $Gradle @tasks @proxyArgs '-PmvpPrebuiltDir=app/build/mvp-prebuilt' '-PbuildABI=arm64-v8a,x86_64' '-PbuildVersionName=v3.3.12-mvp' '--console=plain' '--max-workers=4' '-Dorg.gradle.internal.http.socketTimeout=30000' '-Dorg.gradle.internal.http.connectionTimeout=30000' 2>&1 | Tee-Object "$OutputDir/build-mvp.log"
    if ($LASTEXITCODE -ne 0) { throw "Gradle failed: $LASTEXITCODE (see build-mvp.log)" }
    & "$PSScriptRoot/verify-mvp-apks.ps1" -AndroidSdk $env:ANDROID_HOME -OutputDir $OutputDir
} finally { Pop-Location }
