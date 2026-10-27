import unittest
from unittest.mock import patch
from collections import namedtuple
from ci_disk_preflight import check

Usage = namedtuple('Usage', 'total used free')


class DiskPreflightTests(unittest.TestCase):
    @patch('ci_disk_preflight.shutil.disk_usage', return_value=Usage(200, 100, 100))
    def test_exact_budget_passes(self, _):
        self.assertTrue(check('.', 100)['passed'])

    @patch('ci_disk_preflight.shutil.disk_usage', return_value=Usage(200, 101, 99))
    def test_shortfall_fails_without_skip(self, _):
        with self.assertRaisesRegex(ValueError, 'no validation was skipped'):
            check('.', 100)
