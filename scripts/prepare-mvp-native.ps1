param(
    [string]$CacheDir = "$PSScriptRoot/../../work/native-release",
    [string]$OutputDir = "$PSScriptRoot/../app/build/mvp-prebuilt"
)
$ErrorActionPreference = 'Stop'
$release = 'v3.3.12'
# Pinned from https://api.github.com/repos/osfans/trime/releases/tags/v3.3.12
$hashes = [ordered]@{
    'arm64-v8a' = 'c727d509cbae8ba6a6b3616f57ea299d46bb13072812342811d03aea0bc3cb98'
    'x86_64' = '0b32fee993f59614a69269aea30f817c48d7af67b35965ed4eb107e68340ee6f'
}
New-Item -ItemType Directory -Force $CacheDir, $OutputDir | Out-Null
$CacheDir = (Resolve-Path $CacheDir).Path
$OutputDir = (Resolve-Path $OutputDir).Path
Add-Type -AssemblyName System.IO.Compression.FileSystem
$records = @()
foreach ($abi in $hashes.Keys) {
    $name = "com.osfans.trime-v3.3.12-0-ge09ac711-$abi-release.apk"
    $url = "https://github.com/osfans/trime/releases/download/$release/$name"
    $apk = Join-Path $CacheDir $name
    if (!(Test-Path $apk)) {
        & curl.exe --fail --location --retry 3 --connect-timeout 30 --output "$apk.part" $url
        if ($LASTEXITCODE -ne 0) { throw "Download failed: $url" }
        Move-Item -LiteralPath "$apk.part" -Destination $apk
    }
    $actual = (Get-FileHash -Algorithm SHA256 $apk).Hash.ToLowerInvariant()
    if ($actual -ne $hashes[$abi]) { throw "SHA-256 mismatch: $apk (expected $($hashes[$abi]), actual $actual)" }
    $zip = [IO.Compression.ZipFile]::OpenRead($apk)
    $files = @()
    try {
        foreach ($entry in $zip.Entries) {
            $relative = $null
            if ($entry.FullName -match "^lib/$abi/([^/]+\.so)$") {
                $relative = "jniLibs/$abi/$($Matches[1])"
            } elseif ($abi -eq 'arm64-v8a' -and $entry.FullName -match '^assets/shared/opencc/([^/]+)$') {
                $relative = $entry.FullName
            }
            if ($relative) {
                $dest = Join-Path $OutputDir $relative
                New-Item -ItemType Directory -Force (Split-Path $dest) | Out-Null
                [IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $dest, $true)
                $files += [ordered]@{ path = $relative; sha256 = (Get-FileHash $dest).Hash.ToLowerInvariant() }
            }
        }
    } finally { $zip.Dispose() }
    if (!(Test-Path "$OutputDir/jniLibs/$abi/librime_jni.so")) { throw "JNI library absent for $abi" }
    $records += [ordered]@{ abi = $abi; url = $url; sha256 = $actual; files = $files }
}
[ordered]@{ release = $release; upstreamCommit = 'e09ac711'; sources = $records } |
    ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 "$OutputDir/provenance.json"
Write-Host "Verified official native libraries and OpenCC fallback: $OutputDir"
