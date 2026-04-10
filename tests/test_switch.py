"""
Unit tests for lib/switch.py
Tests MAC address table parsing — no SSH connection needed.
"""

import unittest


class TestParseMacTable(unittest.TestCase):
    """Test the static _parse() method directly — no SSH needed."""

    def setUp(self):
        from lib.switch import SwitchClient
        self.switch = SwitchClient("172.16.100.253")

    def test_parses_valid_mac_table(self):
        """_parse() correctly extracts MAC and port from standard output."""
        output = """
          Mac Address Table
        -------------------------------------------
        Vlan    Mac Address       Type        Ports
        ----    -----------       --------    -----
           1    5254.0003.a7d5    DYNAMIC     Gi0/2
           1    5254.0025.21b4    DYNAMIC     Gi1/3
           1    5254.004e.c101    DYNAMIC     Gi1/2
        """
        result = self.switch._parse(output)
        self.assertEqual(result["5254.0003.a7d5"], "Gi0/2")
        self.assertEqual(result["5254.0025.21b4"], "Gi1/3")
        self.assertEqual(result["5254.004e.c101"], "Gi1/2")

    def test_returns_lowercase_mac(self):
        """_parse() normalises MAC addresses to lowercase."""
        output = "   1    5254.00AB.CD12    DYNAMIC     Gi0/0\n"
        result = self.switch._parse(output)
        self.assertIn("5254.00ab.cd12", result)

    def test_skips_header_lines(self):
        """_parse() ignores non-MAC lines like headers and separators."""
        output = """
        Vlan    Mac Address       Type        Ports
        ----    -----------       --------    -----
        Total Mac Addresses for this criterion: 1
        """
        result = self.switch._parse(output)
        self.assertEqual(result, {})

    def test_empty_output(self):
        """_parse() returns empty dict when output has no MAC entries."""
        result = self.switch._parse("")
        self.assertEqual(result, {})

    def test_multiple_vlans(self):
        """_parse() handles MAC entries across different VLANs."""
        output = """
           1    5254.0003.a7d5    DYNAMIC     Gi0/0
          10    5254.0025.21b4    DYNAMIC     Gi0/1
         100    5254.004e.c101    DYNAMIC     Gi0/2
        """
        result = self.switch._parse(output)
        self.assertEqual(len(result), 3)


if __name__ == "__main__":
    unittest.main()
