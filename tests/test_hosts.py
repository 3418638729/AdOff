"""hosts 解析与生成的单元测试。"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from adoff import hosts  # noqa: E402


class ParseDomainsTest(unittest.TestCase):
    def test_keeps_valid_domains_in_order(self):
        text = "ad.example.com\ncdn.example.net\ntracker.example.org\n"
        self.assertEqual(
            hosts.parse_domains(text),
            ["ad.example.com", "cdn.example.net", "tracker.example.org"],
        )

    def test_skips_comments_and_blank_lines(self):
        text = "# comment\n\n! adblock style\n[Adblock Plus]\nreal.example.com\n"
        self.assertEqual(hosts.parse_domains(text), ["real.example.com"])

    def test_removes_duplicates(self):
        text = "dup.example.com\ndup.example.com\nother.example.com\n"
        self.assertEqual(hosts.parse_domains(text), ["dup.example.com", "other.example.com"])

    def test_rejects_invalid_entries(self):
        text = "not-a-domain\n1234\nfoo\nvalid.example.com\n"
        self.assertEqual(hosts.parse_domains(text), ["valid.example.com"])

    def test_domain_requires_a_dot_and_tld(self):
        text = "localhost\nvalid.example.com\n"
        self.assertEqual(hosts.parse_domains(text), ["valid.example.com"])


class ExtraDomainsTest(unittest.TestCase):
    def test_project_list_contains_core_sdks(self):
        domains = hosts.read_extra_domains()
        self.assertIn("ad.oceanengine.com", domains)
        self.assertIn("pgdt.gtimg.cn", domains)
        self.assertIn("alimama.com", domains)

    def test_no_duplicates_in_project_list(self):
        domains = hosts.read_extra_domains()
        self.assertEqual(len(domains), len(set(domains)))


if __name__ == "__main__":
    unittest.main()
