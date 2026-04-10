"""
Unit tests for lib/device.py
Tests MAC normalisation and NETCONF response parsing.
"""

import unittest
from unittest.mock import patch, MagicMock


class TestDeviceInfo(unittest.TestCase):
    """Test the DeviceInfo dataclass."""

    def setUp(self):
        from lib.device import DeviceInfo
        self.DeviceInfo = DeviceInfo

    def test_mac_dot_colon_format(self):
        """mac_dot converts colon-separated MAC to Cisco dot notation."""
        info = self.DeviceInfo(ip="172.16.100.10", mac="52:54:00:03:a7:d5")
        self.assertEqual(info.mac_dot, "5254.0003.a7d5")

    def test_mac_dot_already_dot_format(self):
        """mac_dot handles MAC already in dot notation."""
        info = self.DeviceInfo(ip="172.16.100.10", mac="5254.0003.a7d5")
        self.assertEqual(info.mac_dot, "5254.0003.a7d5")

    def test_mac_dot_none_when_no_mac(self):
        """mac_dot returns None when no MAC is set."""
        info = self.DeviceInfo(ip="172.16.100.10", mac=None)
        self.assertIsNone(info.mac_dot)

    def test_default_manufacturer(self):
        """DeviceInfo defaults manufacturer to Cisco."""
        info = self.DeviceInfo(ip="172.16.100.10")
        self.assertEqual(info.manufacturer, "Cisco")


class TestDeviceClient(unittest.TestCase):
    """Test DeviceClient NETCONF response parsing."""

    def setUp(self):
        from lib.device import DeviceClient
        self.client = DeviceClient("172.16.100.10")

    @patch("lib.device.manager.connect")
    def test_get_mgmt_mac_colon_format(self, mock_connect):
        """get_mgmt_mac() extracts MAC in colon format from XML response."""
        xml = "<address>52:54:00:03:a7:d5</address>"
        mock_m = MagicMock()
        mock_m.__enter__ = MagicMock(return_value=mock_m)
        mock_m.__exit__ = MagicMock(return_value=False)
        mock_m.dispatch.return_value = xml
        mock_connect.return_value = mock_m

        result = self.client.get_mgmt_mac()
        self.assertEqual(result, "52:54:00:03:a7:d5")

    @patch("lib.device.manager.connect")
    def test_get_mgmt_mac_returns_none_on_error(self, mock_connect):
        """get_mgmt_mac() returns None when NETCONF connection fails."""
        mock_connect.side_effect = Exception("Connection refused")
        result = self.client.get_mgmt_mac()
        self.assertIsNone(result)

    @patch("lib.device.manager.connect")
    def test_get_inventory_prefers_rp_serial(self, mock_connect):
        """get_inventory() returns RP serial over other serials."""
        xml = """
            <serial-number>LC123456</serial-number>
            R-IOSXRV9000-RP-C
            <serial-number>RP789012</serial-number>
            <model-name>IOS XRv 9000</model-name>
        """
        mock_m = MagicMock()
        mock_m.__enter__ = MagicMock(return_value=mock_m)
        mock_m.__exit__ = MagicMock(return_value=False)
        mock_m.dispatch.return_value = xml
        mock_connect.return_value = mock_m

        serial, model = self.client.get_inventory()
        self.assertEqual(serial, "RP789012")
        self.assertEqual(model, "IOS XRv 9000")

    @patch("lib.device.manager.connect")
    def test_get_inventory_returns_none_on_error(self, mock_connect):
        """get_inventory() returns (None, None) when NETCONF fails."""
        mock_connect.side_effect = Exception("Timeout")
        serial, model = self.client.get_inventory()
        self.assertIsNone(serial)
        self.assertIsNone(model)


if __name__ == "__main__":
    unittest.main()
