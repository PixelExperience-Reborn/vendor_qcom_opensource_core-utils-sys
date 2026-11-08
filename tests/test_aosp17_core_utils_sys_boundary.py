#!/usr/bin/env python3
"""AOSP17 stage 195: historical Qualcomm framework-detection boundary.

Host-only source checks for PE-Reborn clean AOSP17 platform, not device HAL,
Qualcomm service implementation, modern runtime ABI or actual Android build.
"""
from pathlib import Path
import os
import re
import subprocess
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_COMMIT = "5208eb34ee39a7514d10b7b109d1824b23564e85"
ARCHIVE_TREE = "ebef0c90bacd02fb94760483c60b5c855fc6fa51"
LEGACY_PATH = "vendor/qcom/opensource/core-utils-sys"
LEGACY_NAME = "vendor_qcom_opensource_core-utils-sys"


def git(*args):
    return subprocess.run(
        ["git", "-C", str(ROOT), *args], check=True,
        capture_output=True, text=True,
    ).stdout.strip()


def entry(ref, path):
    data = git("ls-tree", ref, "--", path)
    if not data:
        raise AssertionError("missing historical object " + path)
    metadata, name = data.split("\t", 1)
    if name != path:
        raise AssertionError("mismatched object " + name)
    mode, kind, sha = metadata.split()
    return (mode, kind, sha)


def source(path):
    return (ROOT / path).read_text(encoding="utf-8")


def pinned_reference(name):
    path = os.environ.get(name)
    if not path or not Path(path).is_file():
        raise AssertionError("required pinned AOSP17 source " + name)
    return Path(path).read_text(encoding="utf-8")


class QcomFwkDetectArchiveBoundary(unittest.TestCase):
    def test_historic_git_ancestor_and_tree(self):
        x = subprocess.run(
            ["git", "-C", str(ROOT), "merge-base", "--is-ancestor",
             ARCHIVE_COMMIT, "HEAD"], capture_output=True, text=True
        )
        self.assertEqual(x.returncode, 0, x.stderr)
        self.assertEqual(git("rev-parse", ARCHIVE_COMMIT + "^{tree}"), ARCHIVE_TREE)

    def test_original_fwk_detect_tree_unchanged(self):
        self.assertEqual(entry("HEAD", "fwk-detect"),
                         ("040000", "tree", "94c309eb51256fa9a3e1c5902d5b6517e09955ea"))
        self.assertEqual(entry("HEAD", ".gitupstream"),
                         ("100644", "blob", "a37a2845c6910ce8405f1f45abb5b2a32bbf20e2"))
        self.assertEqual(entry("HEAD", "fwk-detect"),
                         entry(ARCHIVE_COMMIT, "fwk-detect"))

    def test_exact_four_qualcomm_modules_and_partition_metadata(self):
        bp = source("fwk-detect/Android.bp")
        modules = re.findall(r'\bname:\s*"([^"]+)"', bp)
        self.assertEqual(modules, [
            "libqti_vndfwk_detect_system", "vndfwk-test-system",
            "libvndfwk_detect_jni.qti_system", "vndfwk.detect_system",
        ])
        self.assertEqual(bp.count("cc_library_shared {"), 2)
        self.assertEqual(bp.count("cc_test {"), 1)
        self.assertEqual(bp.count("java_library_static {"), 1)
        self.assertEqual(bp.count("system_ext_specific: true"), 2)
        self.assertIn('compile_multilib: "both"', bp)
        self.assertIn('sdk_version: "current"', bp)
        self.assertIn('"libcutils"', bp)

    def test_property_names_and_default_false_are_historical_qti_only(self):
        c = source("fwk-detect/vndfwk-detect.c")
        self.assertIn('"ro.vendor.qti.va_aosp.support"', c)
        self.assertIn('"ro.vendor.qti.va_odm.support"', c)
        self.assertEqual(c.count("property_get_bool("), 2)
        self.assertIn("property_get_bool(VALUEADD_AOSP_SUPPORT_PROPERTY, false)", c)
        self.assertIn("property_get_bool(VALUEADD_ODM_SUPPORT_PROPERTY, false)", c)
        self.assertIn("#define VND_ENHANCED_ODM_STATUS_BIT 0x01", c)
        self.assertIn("#define VND_ENHANCED_SYS_STATUS_BIT 0x02", c)

    def test_aosp_unmodified_is_default_not_assumed_vendor_enhanced(self):
        header = source("fwk-detect/vndfwk-detect.h")
        self.assertIn("int isRunningWithVendorEnhancedFramework(void)", header)
        self.assertIn("int getVendorEnhancedInfo(void)", header)
        self.assertNotIn("persist.sys.", source("fwk-detect/vndfwk-detect.c"))
        # No need to add Qualcomm "enhanced" properties to a pure AOSP base.

    def test_java_jni_dependency_chain_is_not_a_platform_public_api(self):
        bp = source("fwk-detect/Android.bp")
        java = source("fwk-detect/src/com/qualcomm/qti/VndFwkDetect.java")
        jni = source("fwk-detect/jni/com_qualcomm_qti_VndFwkDetect.cpp")
        self.assertIn("System.loadLibrary(\"vndfwk_detect_jni.qti_system\")", java)
        self.assertIn("private native int native_getVendorEnhancedInfo()", java)
        self.assertIn("libqti_vndfwk_detect_system.so", jni)
        self.assertIn("JNI_OnLoad(JavaVM *jvm", jni)
        self.assertIn("RegisterNatives", jni)
        self.assertIn('"jni_headers"', bp)
        self.assertNotIn("aidl_interface", bp)
        # It is an optional Qualcomm-private JNI bridge, not modern Stable AIDL.

    def test_jni_error_handling_requires_future_runtime_review(self):
        java = source("fwk-detect/src/com/qualcomm/qti/VndFwkDetect.java")
        self.assertIn("catch (Exception ex)", java)
        self.assertNotIn("catch (UnsatisfiedLinkError", java)
        # UnsatisfiedLinkError extends LinkageError, not Exception.
        # Do not silently "fix" historical code without a proven consumer.

    def test_no_device_tree_hal_or_framework_change_inside_archive(self):
        for path in ("BoardConfig.mk", "device.mk", "AndroidProducts.mk",
                     "Android.bp", "system", "product", "vendor",
                     "init.mondrian.rc"):
            with self.subTest(path=path):
                self.assertFalse((ROOT / path).exists())
        self.assertFalse((ROOT / "fwk-detect/aidl").exists())

    def test_source_test_not_misclassified_as_platform_integration(self):
        c = source("fwk-detect/vndfwk-test.c")
        self.assertIn("isRunningWithVendorEnhancedFramework()", c)
        self.assertIn("getVendorEnhancedInfo()", c)
        self.assertIn("printf(", c)
        self.assertNotIn("AIDL", c)
        # vndfwk-test-system only exercises the historical detector; it is
        # not a platform bring-up or device compatibility test.

    def test_official_aosp17_graph_does_not_select_qualcomm_detector(self):
        root = ET.fromstring(pinned_reference("PE_AOSP17_REFERENCE"))
        self.assertEqual(root.find("default").get("revision"),
                         "refs/tags/android-17.0.0_r1")
        paths = {p.get("path"): p.get("name") for p in root.iter("project")}
        self.assertEqual(paths["build/soong"], "platform/build/soong")
        self.assertEqual(paths["hardware/interfaces"], "platform/hardware/interfaces")
        self.assertNotIn(LEGACY_PATH, paths)
        self.assertNotIn(LEGACY_NAME, paths.values())

    def test_selected_default_entrypoint_stays_unmodified(self):
        root = ET.fromstring(pinned_reference("PE_AOSP17_DEFAULT"))
        self.assertEqual(
            [p.get("name") for p in root.findall("include")],
            ["aosp17_pe_p2_kernel_configs.xml"],
        )
        self.assertFalse(any(
            p.get("path") == LEGACY_PATH or p.get("name") == LEGACY_NAME
            for p in root.iter("project")
        ))

if __name__ == "__main__":
    unittest.main(verbosity=2)
