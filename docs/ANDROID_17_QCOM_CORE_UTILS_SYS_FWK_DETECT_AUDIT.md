# Stage 195 — Qualcomm core-utils-sys fwk-detect source and AOSP17 boundary

**2026-11-08. PE-Reborn:** independent pure Google AOSP android-17.0.0_r1. Current scope is qualifying 135 historical repositories and building a correct source dependency graph. No device tree, SM8475 integration, LineageOS import or optional features.

## Provenance and what the repository actually does

- Repo: https://github.com/PixelExperience-Reborn/vendor_qcom_opensource_core-utils-sys
- Unmodified historical seventeen HEAD: `5208eb34ee39a7514d10b7b109d1824b23564e85` (2022-11-20), root tree `ebef0c90bacd02fb94760483c60b5c855fc6fa51`, `fwk-detect` subtree `94c309eb51256fa9a3e1c5902d5b6517e09955ea`. Last commit merely adds `.gitupstream` pointing to CLO core-utils-sys.
- The archive contains **seven original tracked files** and four Soong modules, all within fwk-detect/Android.bp: `libqti_vndfwk_detect_system`, `vndfwk-test-system`, `libvndfwk_detect_jni.qti_system`, and `vndfwk.detect_system` (static Java library). Two C/JNI binaries are specifically system_ext libraries, with 32+64 bit builds.
- Its actual C logic reads two Qualcomm-specific properties via `property_get_bool(..., false)`: `ro.vendor.qti.va_aosp.support` and `ro.vendor.qti.va_odm.support`. `getVendorEnhancedInfo()` returns bit 0 for ODM enhanced and bit 1 for the Qualcomm-enhanced system framework. The default without properties is 0 (ordinary AOSP).
- The Java class `com.qualcomm.qti.VndFwkDetect` loads the JNI .so; the JNI layer uses `dlopen`, `dlsym` and `RegisterNatives`. This is a Qualcomm-private helper, not a Stable AIDL HAL, VINTF declaration or independent Android17 platform requirement.
- The old Java code catches `Exception` around `System.loadLibrary` but not `UnsatisfiedLinkError` (a `LinkageError`). This is a source-level caveat, not a reported real runtime crash. Do not change original code in an archive or claim the old module is Android17-compatible.

## Decision for the independent Google AOSP17 source graph

**Keep historical code and Git history unchanged. Do not select these Qualcomm value-added framework detection helpers in active or experimental AOSP17 profiles by accident.** The platform must not claim vendor value-added services are present, synthesize Qualcomm ro.vendor properties, or install JNI/Java shims without a proven direct consumer in the selected AOSP17 build.

Repo-wide GitHub code search of the available default-branch results for the key module/property names returned no matching consumers; that is a limited search, **not proof that no consumer exists in other branches or external proprietary modules**. If a real build later requests this library, re-evaluate the individual dependency and modern Android17 JNI/Soong/API/partition constraints, with a reviewed pinned source and build log.

This Qualcomm component cannot meaningfully be made 'newer' just by changing compilation flags, Soong names, Java SDK level or API versions. Modern alternatives should be based on verified AOSP17 ownership, actual module requirements and a testable consumer; do not manufacture a new feature.

## Implemented branch checks

1. Preserve original Git source tree and all original seven file objects. Add Python static/source checks for four Soong modules, exact properties/bit mapping, source-level JNI behavior and loader caveat, AOSP17 official source graph, default manifest isolation and absence of device tree content.
2. Compile the original `fwk-detect/vndfwk-detect.c` on GitHub Actions Linux host with Clang and a *test-only* stub `cutils/properties.h`. Link against a new C test that mocks `property_get_bool` and checks all four ODM/system truth-table combinations, default-false behavior, and expected read counts. This executes the original detector C logic **on host only**, not on Android17.
3. GitHub Actions workflow pins the PE-Reborn manifest source commit, runs all manifest tests and validates 135 repository entries. Host C compiler runs with `-std=c11 -Wall -Wextra -Werror`. No real Android sysprops, HALs, device trees or proprietary inputs.
4. Companion Manifest Draft PR #2: path + known-repository-alias exclusion across active and nondefault graphs, two negative tests, updated matrix row 195. Neither historical seventeen nor AOSP17 default.xml changes.

## Qualification still required before any adoption

A specific Android17 Soong module consumer, service and licensing/namespace policy must be demonstrated. If required, validate vendor/system_ext property access and SELinux property contexts, JNI class loader namespace, the actual target C/Java builds, ELF/ABI correctness and installed packaging. The current task remains **platform source/build restoration**, not Android device adaptation or feature implementation.

**No full AOSP17 repo sync, Soong build, system image, VINTF target HAL, Android execution or mondrian physical test is claimed.** A passing native-host C behavioral test is narrower than a product build.
