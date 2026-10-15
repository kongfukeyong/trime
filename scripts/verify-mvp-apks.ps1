param(
    [Parameter(Mandatory=$true)][string]$AndroidSdk,
    [string]$ApkDir = "$PSScriptRoot/../app/build/outputs/apk/debug",
    [string]$OutputDir = "$PSScriptRoot/../../outputs"
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path "$PSScriptRoot/..").Path
$AndroidSdk = (Resolve-Path $AndroidSdk).Path
New-Item -ItemType Directory -Force $OutputDir | Out-Null
$OutputDir = (Resolve-Path $OutputDir).Path
Add-Type -AssemblyName System.IO.Compression.FileSystem
function Get-EntryHash($Entry) {
    if (!$Entry) { throw 'Expected ZIP entry is missing' }
    $stream = $Entry.Open()
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($sha.ComputeHash($stream)).Replace('-', '').ToLowerInvariant() }
    finally { $stream.Dispose(); $sha.Dispose() }
}
function Read-EntryText($Entry) {
    if (!$Entry) { throw 'Expected ZIP text entry is missing' }
    $reader = [IO.StreamReader]::new($Entry.Open())
    try { return $reader.ReadToEnd() } finally { $reader.Dispose() }
}
$manifest = Get-Content "$repo/docs/wanxiang-assets.manifest.json" -Raw | ConvertFrom-Json
if (!$manifest.model_complete) { throw 'Wanxiang manifest marks model incomplete' }
$apks = @(Get-ChildItem $ApkDir -Filter '*.apk')
if ($apks.Count -ne 2) { throw "Expected two ABI APKs, got $($apks.Count)" }
$report = @()
foreach ($apk in $apks) {
    & "$AndroidSdk/build-tools/36.0.0/apksigner.bat" verify --verbose --print-certs $apk.FullName
    if ($LASTEXITCODE -ne 0) { throw "APK signature validation failed: $apk" }
    & "$AndroidSdk/build-tools/36.0.0/zipalign.exe" -c -p 4 $apk.FullName
    if ($LASTEXITCODE -ne 0) { throw "APK alignment validation failed: $apk" }
    $permissions = & "$AndroidSdk/build-tools/36.0.0/aapt.exe" dump permissions $apk.FullName
    if ($LASTEXITCODE -ne 0) { throw 'Cannot read APK permissions' }
    if ($permissions -match 'android.permission.INTERNET') { throw 'APK must not request INTERNET permission' }
    $zip = [IO.Compression.ZipFile]::OpenRead($apk.FullName)
    try {
        $nativeEntries = @($zip.Entries | Where-Object { $_.FullName -match '^lib/(arm64-v8a|x86_64)/librime_jni\.so$' })
        if ($nativeEntries.Count -ne 1) { throw 'Each APK must contain exactly one supported JNI ABI' }
        $abi = $nativeEntries[0].FullName.Split('/')[1]
        $nativeHash = Get-EntryHash $nativeEntries[0]
        if ($nativeHash -ne (Get-FileHash "$repo/app/build/mvp-prebuilt/jniLibs/$abi/librime_jni.so").Hash) {
            throw "Packaged native library changed for $abi"
        }
        $defaultEntry = $zip.GetEntry('assets/shared/default.yaml')
        $defaultText = Read-EntryText $defaultEntry
        if (!$defaultText.Contains('schema_list:')) { throw 'APK default.yaml lacks real Rime configuration' }
        foreach ($entry in $zip.Entries) {
            if ($entry.FullName.StartsWith('assets/') -and $entry.Length -lt 256 -and !$entry.FullName.EndsWith('/')) {
                if ((Read-EntryText $entry).Trim().StartsWith('../../../../data/rime/')) { throw "APK contains symlink placeholder: $($entry.FullName)" }
            }
        }
        foreach ($resource in $manifest.files) {
            $entry = $zip.GetEntry("assets/rime/$($resource.path)")
            if (!$entry -or $entry.Length -ne $resource.bytes -or (Get-EntryHash $entry) -ne $resource.sha256) {
                throw "Packaged Wanxiang resource mismatch: $($resource.path)"
            }
        }
        $checksums = (Read-EntryText $zip.GetEntry('assets/checksums.json')) | ConvertFrom-Json
        $verifiedFiles = 0
        foreach ($property in $checksums.files.PSObject.Properties) {
            if ($property.Value) {
                if ((Get-EntryHash $zip.GetEntry("assets/$($property.Name)")) -ne $property.Value) {
                    throw "APK asset checksum mismatch: $($property.Name)"
                }
                $verifiedFiles++
            }
        }
        $report += [ordered]@{
            file = $apk.Name; abi = $abi; bytes = $apk.Length
            sha256 = (Get-FileHash $apk.FullName).Hash.ToLowerInvariant()
            native_sha256 = $nativeHash; default_yaml_sha256 = (Get-EntryHash $defaultEntry)
            wanxiang_files_verified = $manifest.files.Count; checksums_files_verified = $verifiedFiles
            signature_verified = $true; zipalign_verified = $true; internet_permission = $false
            permissions = $permissions
        }
    } finally { $zip.Dispose() }
}
if (@($report.abi | Sort-Object -Unique).Count -ne 2) { throw 'Missing one required ABI' }
# Export only after both APKs have passed every check.
foreach ($apk in $apks) {
    if ($apk.DirectoryName -ne $OutputDir) { Copy-Item -LiteralPath $apk.FullName -Destination $OutputDir }
}
$report | ForEach-Object { "$($_.sha256)  $($_.file)" } | Set-Content "$OutputDir/apk-sha256.txt"
[ordered]@{ passed = $true; scope = 'Static APK validation only; installation/runtime not tested'; apks = $report } |
    ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 "$OutputDir/apk-validation.json"
Copy-Item "$repo/app/build/mvp-prebuilt/provenance.json" "$OutputDir/native-provenance.json"
Write-Host "Both APKs verified and exported to $OutputDir"
