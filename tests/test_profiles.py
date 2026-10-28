"""型号匹配的单元测试。"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from adoff import profiles  # noqa: E402


class DetectProfileTest(unittest.TestCase):
    def test_redmi_matches_xiaomi_profile(self):
        self.assertEqual(profiles.detect_profile("Redmi K70").key, "xiaomi")

    def test_lowercase_model_still_matches(self):
        self.assertEqual(profiles.detect_profile("redmi k70").key, "xiaomi")

    def test_chinese_model_matches(self):
        self.assertEqual(profiles.detect_profile("红米 K70").key, "xiaomi")

    def test_unknown_model_falls_back_to_generic(self):
        self.assertEqual(profiles.detect_profile("SM-G9910").key, "generic")

    def test_empty_model_falls_back_to_generic(self):
        self.assertEqual(profiles.detect_profile("").key, "generic")


class ProfileDataTest(unittest.TestCase):
    def test_xiaomi_exposes_system_ad_package(self):
        profile = profiles.get_profile("xiaomi")
        self.assertIsNotNone(profile)
        self.assertIn("com.miui.systemAdSolution", profile.suspend_packages)

    def test_generic_profile_does_not_touch_system(self):
        profile = profiles.get_profile("generic")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.suspend_packages, ())

    def test_default_profile_is_generic(self):
        self.assertEqual(profiles.DEFAULT_PROFILE.key, "generic")


if __name__ == "__main__":
    unittest.main()
