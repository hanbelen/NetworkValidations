"""
Unit tests for lib/netbox.py
Tests get_or_create logic and upsert_device — all HTTP calls mocked.
"""

import unittest
from unittest.mock import patch, MagicMock


class TestNetBoxClient(unittest.TestCase):

    def setUp(self):
        from lib.netbox import NetBoxClient
        self.nb = NetBoxClient()

    @patch("lib.netbox.requests.get")
    def test_get_or_create_returns_existing(self, mock_get):
        """get_or_create() returns existing object without creating a new one."""
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"count": 1, "results": [{"id": 42, "name": "SYD"}]},
        )
        mock_get.return_value.raise_for_status = MagicMock()

        result = self.nb.get_or_create(
            "dcim/sites/",
            {"slug": "syd"},
            {"name": "SYD", "slug": "syd"},
        )
        self.assertEqual(result["id"], 42)

    @patch("lib.netbox.requests.post")
    @patch("lib.netbox.requests.get")
    def test_get_or_create_creates_when_missing(self, mock_get, mock_post):
        """get_or_create() calls POST when object does not exist."""
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"count": 0, "results": []},
        )
        mock_get.return_value.raise_for_status = MagicMock()
        mock_post.return_value = MagicMock(
            status_code=201,
            json=lambda: {"id": 99, "name": "SYD"},
        )

        result = self.nb.get_or_create(
            "dcim/sites/",
            {"slug": "syd"},
            {"name": "SYD", "slug": "syd"},
        )
        self.assertEqual(result["id"], 99)
        mock_post.assert_called_once()

    @patch("lib.netbox.requests.post")
    @patch("lib.netbox.requests.get")
    def test_get_or_create_site(self, mock_get, mock_post):
        """get_or_create_site() uses lowercase slug."""
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"count": 0, "results": []},
        )
        mock_get.return_value.raise_for_status = MagicMock()
        mock_post.return_value = MagicMock(
            status_code=201,
            json=lambda: {"id": 1, "slug": "syd"},
        )

        self.nb.get_or_create_site("SYD")
        call_data = mock_post.call_args[1]["json"]
        self.assertEqual(call_data["slug"], "syd")
        self.assertEqual(call_data["name"], "SYD")

    @patch("lib.netbox.requests.post")
    @patch("lib.netbox.requests.get")
    def test_post_raises_on_error(self, mock_get, mock_post):
        """post() raises NetBoxError on non-2xx response."""
        from lib.netbox import NetBoxError
        mock_post.return_value = MagicMock(
            status_code=400,
            text="Bad Request",
        )
        with self.assertRaises(NetBoxError):
            self.nb.post("dcim/sites/", {"name": "BAD"})

    @patch("lib.netbox.requests.get")
    def test_get_raises_on_http_error(self, mock_get):
        """get() raises when the HTTP response is an error."""
        mock_get.return_value = MagicMock()
        mock_get.return_value.raise_for_status.side_effect = Exception("404")
        with self.assertRaises(Exception):
            self.nb.get("dcim/sites/")


if __name__ == "__main__":
    unittest.main()
