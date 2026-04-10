"""
Unit tests for lib/scanner.py
Tests the fping scan output parsing and IP filtering.
"""

import unittest
from unittest.mock import patch, MagicMock


class TestScan(unittest.TestCase):

    @patch("lib.scanner.subprocess.run")
    def test_returns_live_ips(self, mock_run):
        """scan() returns IPs found by fping."""
        mock_run.return_value = MagicMock(
            stdout="172.16.100.10\n172.16.100.11\n172.16.100.12\n"
        )
        from lib.scanner import scan
        result = scan()
        self.assertEqual(result, ["172.16.100.10", "172.16.100.11", "172.16.100.12"])

    @patch("lib.scanner.subprocess.run")
    def test_switch_ip_always_excluded(self, mock_run):
        """scan() never returns the switch IP even if fping finds it."""
        mock_run.return_value = MagicMock(
            stdout="172.16.100.10\n172.16.100.253\n"
        )
        from lib.scanner import scan
        result = scan()
        self.assertNotIn("172.16.100.253", result)

    @patch("lib.scanner.subprocess.run")
    def test_custom_exclusions(self, mock_run):
        """scan() excludes additional IPs passed in the exclude list."""
        mock_run.return_value = MagicMock(
            stdout="172.16.100.10\n172.16.100.11\n172.16.100.12\n"
        )
        from lib.scanner import scan
        result = scan(exclude=["172.16.100.11"])
        self.assertNotIn("172.16.100.11", result)
        self.assertIn("172.16.100.10", result)

    @patch("lib.scanner.subprocess.run")
    def test_returns_sorted_list(self, mock_run):
        """scan() returns IPs in sorted order."""
        mock_run.return_value = MagicMock(
            stdout="172.16.100.12\n172.16.100.10\n172.16.100.11\n"
        )
        from lib.scanner import scan
        result = scan()
        self.assertEqual(result, sorted(result))

    @patch("lib.scanner.subprocess.run")
    def test_empty_subnet(self, mock_run):
        """scan() returns empty list when no hosts are alive."""
        mock_run.return_value = MagicMock(stdout="")
        from lib.scanner import scan
        result = scan()
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
