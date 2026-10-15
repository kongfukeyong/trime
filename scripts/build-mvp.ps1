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
    & $Gradle @tasks @proxyArgs '-PmvpPrebuiltDir=app/build/mvp-prebuilt' '-PbuildABI=arm64-v8a,x86_64' '-PbuildVersionName=v3.3.12-mvp' '--console=plain' '--max-workers=4' 2>&1 | Tee-Object "$OutputDir/build-mvp.log"
    if ($LASTEXITCODE -ne 0) { throw "Gradle failed: $LASTEXITCODE (see build-mvp.log)" }
    $apks = @(Get-ChildItem 'app/build/outputs/apk/debug' -Filter '*.apk')
    if ($apks.Count -ne 2) { throw "Expected two ABI APKs, got $($apks.Count)" }
    foreach ($apk in $apks) {
        & "$env:ANDROID_HOME/build-tools/36.0.0/apksigner.bat" verify --verbose $apk.FullName
        if ($LASTEXITCODE -ne 0) { throw "APK signature validation failed: $apk" }
        $permissions = & "$env:ANDROID_HOME/build-tools/36.0.0/aapt.exe" dump permissions $apk.FullName
        if ($LASTEXITCODE -ne 0) { throw 'Cannot read APK permissions' }
        if ($permissions -match 'android.permission.INTERNET') { throw 'APK must not request INTERNET permission' }
        Copy-Item -LiteralPath $apk.FullName -Destination $OutputDir
    }
    Get-ChildItem $OutputDir -Filter '*.apk' | Get-FileHash -Algorithm SHA256 | Format-Table -AutoSize | Out-String -Width 300 | Set-Content "$OutputDir/apk-sha256.txt"
    Copy-Item 'app/build/mvp-prebuilt/provenance.json' "$OutputDir/native-provenance.json"
} finally { Pop-Location }
