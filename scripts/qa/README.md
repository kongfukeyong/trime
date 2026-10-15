# Cloud Android emulator smoke

These development-only tools do not modify Trime's product code or require Gradle. Use a **fresh disposable emulator**; the runner refuses a physical device or an already-installed product. No credentials are needed. The helper APK has no permissions and uses a dedicated disposable test key.

From the repository root, with JDK 21 and Android SDK build-tools 36.0.0 / platform 36 installed:

```sh
python scripts/qa/build-editor.py --output outputs/qa-editor
python scripts/qa/emulator-smoke.py \
  --apk downloaded-apk \
  --editor outputs/qa-editor/trime-qa-editor.apk \
  --deploy-timeout 600 \
  --output outputs/emulator-smoke
```

`--apk` accepts either the x86_64 APK or the entire downloaded build artifact directory. Selection inspects ZIP contents for `lib/x86_64/librime_jni.so` and rejects zero/multiple matches. Package is `com.osfans.trime.debug`. Use `--serial emulator-5554` when needed. Without a serial, adb must have exactly one device.

## Assertions

1. Fresh installation succeeds; source APK SHA-256 is saved.
2. Trime is enabled and selected as default IME; MainActivity is launched and its process appears. No preference or Rime configuration is patched by the tests.
3. A separately built Java editor focuses an ordinary multiline text field. It supports Clear, hello and 你好 seed buttons, plus the `text` intent extra.
4. Wait at most 600 seconds (plus bounded adb call overhead) for the real deployment success callback, nonempty compiled `wanxiang.schema.yaml`, `.prism.bin`, `.table.bin`, and first schema `wanxiang` in deployed `default.yaml`. Verify the runtime `.gram` SHA-256 against `docs/wanxiang-resources.lock.json` (additional 120-second command bound). Merely copying assets is not success.
5. UI hierarchy contains Auto / Chinese / English (or corresponding Simplified Chinese labels).
6. AUTO with an empty ordinary field: type `nihao`, require selected Chinese mode after **each** key; space selects the first Rime candidate and must produce a Han character. Capture composition before commit.
7. AUTO with committed `hello`: type `abc`, require exact `helloabc` and current mode EN.
8. Force Chinese with committed Latin context: type `nihao`, require Chinese throughout and a Chinese candidate commit after the Latin prefix.
9. Force English with committed `你好`: type `abc`, require exact `你好abc` and English override.

Alphabetic events use `adb shell input keyevent KEYCODE_*`, which the checked-in service routes through `onKeyDown` → `forwardKeyEvent` → `prepareLanguageForKey` → Rime. Mode buttons are touched at bounds obtained from the actual UI hierarchy. **Soft-keyboard letter-key touch/gesture behavior is not covered.** `input text` is never used to claim IME coverage. Exact committed text and Chinese conversion prevent direct editor insertion from falsely passing all language cases.

UI tests support English and Simplified Chinese labels. Other app locales, theme changes, missing deployment debug logs or unreadable runtime files cause a failure/timeout with evidence; there is no fallback that claims success. Candidate selection uses space, not a guessed candidate coordinate. This verifies a Han commit, not an exact dictionary ranking or model prediction quality. The grammar hash proves the runtime file matches the model; it does not separately benchmark model inference.

Deployment log source was checked in product code: JNI calls `Rime.handleRimeMessage(type, params)`, which constructs the native message and executes `Timber.d("Handling $message")`. `DeployMessage.toString()` emits `DeployMessage(state=Success)`. `TrimeApplication.onCreate()` plants a `Timber.DebugTree` for `BuildConfig.DEBUG` and its override delegates to `super.log`, so these debug messages reach Android logcat. This smoke job requires the debug APK; release builds filter out DEBUG messages and must not silently pass this assertion.

## Results and CI integration

`summary.json` has PASS / FAIL / NOT_RUN per case. Exit code is nonzero unless every case passes. Core setup failures leave downstream cases NOT_RUN. Extended cases run independently after resetting text/mode so later cases can still provide evidence. Full logcat begins before product installation; commands, screenshots, UI XML, runtime file list, compiled configurations, model hash and final dumps are retained even after most failures. A killed CI job may interrupt finalization; configure an `always()` artifact upload.

Use Linux KVM with API 35/default/x86_64 and 4 GB emulator RAM. Allow 30 minutes for job setup, emulator boot, full dictionary/model deployment and tests. No emulator cache should retain product state. The integration fragment is delivered separately in the workspace at `work/qa/cloud-smoke-job.yml`; it expects the existing `apk` job's `trime-offline-language-mvp` artifact. It does not change `.github/workflows/mvp-build.yml`.

Runner configuration follows the [android-emulator-runner documentation](https://github.com/ReactiveCircus/android-emulator-runner#running-hardware-accelerated-emulators-on-linux-runners). The proposed job and Linux/device runtime have **not been executed** by this task. Local checks and any limitations are recorded in the accompanying work/qa validation report; no cloud/device PASS is claimed.
