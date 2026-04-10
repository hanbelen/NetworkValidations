"""
Unit tests for validations/checks/
Tests all check modules with mocked NETCONF responses.
"""

import unittest
from unittest.mock import patch


class TestIsisChecks(unittest.TestCase):

    @patch("validations.checks.isis.get_isis_adjacencies")
    def test_all_adjacencies_up(self, mock_get):
        """isis checks pass when all adjacencies are UP."""
        mock_get.return_value = [
            {"neighbor_id": "0100.0000.0002", "interface": "Gi0/0/0/0",
             "state": "UP", "level": "L2"},
            {"neighbor_id": "0100.0000.0003", "interface": "Gi0/0/0/1",
             "state": "UP", "level": "L2"},
        ]
        from validations.checks.isis import run
        results = run(device="172.16.100.10", role="p")
        passed = [r for r in results if r.passed]
        self.assertEqual(len(passed), len(results))

    @patch("validations.checks.isis.get_isis_adjacencies")
    def test_no_adjacencies_fails(self, mock_get):
        """isis adjacencies_up check fails when no adjacencies are UP."""
        mock_get.return_value = []
        from validations.checks.isis import run
        results = run(device="172.16.100.10", role="p")
        adj_check = next(r for r in results if r.check == "isis.adjacencies_up")
        self.assertFalse(adj_check.passed)

    @patch("validations.checks.isis.get_isis_adjacencies")
    def test_level1_adjacency_fails(self, mock_get):
        """isis level2_only check fails when L1 adjacency is found."""
        mock_get.return_value = [
            {"neighbor_id": "0100.0000.0002", "interface": "Gi0/0/0/0",
             "state": "UP", "level": "L1"},
        ]
        from validations.checks.isis import run
        results = run(device="172.16.100.10", role="p")
        l2_check = next(r for r in results if r.check == "isis.level2_only")
        self.assertFalse(l2_check.passed)

    @patch("validations.checks.isis.get_isis_adjacencies")
    def test_netconf_failure_returns_single_fail(self, mock_get):
        """isis run() returns single FAIL result when NETCONF is unreachable."""
        mock_get.side_effect = Exception("Connection refused")
        from validations.checks.isis import run
        results = run(device="172.16.100.10", role="p")
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].passed)


class TestLdpChecks(unittest.TestCase):

    @patch("validations.checks.ldp.get_ldp_sessions")
    def test_all_sessions_operational(self, mock_get):
        """ldp checks pass when all sessions are OPERATIONAL."""
        mock_get.return_value = [
            {"peer": "10.0.0.2", "state": "OPERATIONAL"},
            {"peer": "10.0.0.3", "state": "OPERATIONAL"},
        ]
        from validations.checks.ldp import run
        results = run(device="172.16.100.10", role="p")
        self.assertTrue(all(r.passed for r in results))

    @patch("validations.checks.ldp.get_ldp_sessions")
    def test_non_operational_session_fails(self, mock_get):
        """ldp no_stuck_sessions check fails when a session is not operational."""
        mock_get.return_value = [
            {"peer": "10.0.0.2", "state": "OPERATIONAL"},
            {"peer": "10.0.0.3", "state": "INITIALIZED"},
        ]
        from validations.checks.ldp import run
        results = run(device="172.16.100.10", role="p")
        stuck_check = next(r for r in results if r.check == "ldp.no_stuck_sessions")
        self.assertFalse(stuck_check.passed)


class TestRsvpChecks(unittest.TestCase):

    @patch("validations.checks.rsvp.get_rsvp_tunnels")
    def test_all_tunnels_up(self, mock_get):
        """rsvp checks pass when all tunnels are UP."""
        mock_get.return_value = [
            {"name": "tunnel-te1", "destination": "10.0.0.4",
             "state": "UP", "bandwidth": "0"},
            {"name": "tunnel-te2", "destination": "10.0.0.5",
             "state": "UP", "bandwidth": "0"},
        ]
        from validations.checks.rsvp import run
        results = run(device="172.16.100.10", role="p")
        self.assertTrue(all(r.passed for r in results))

    @patch("validations.checks.rsvp.get_rsvp_tunnels")
    def test_no_tunnels_fails(self, mock_get):
        """rsvp tunnels_exist check fails when no tunnels are found."""
        mock_get.return_value = []
        from validations.checks.rsvp import run
        results = run(device="172.16.100.10", role="p")
        exist_check = next(r for r in results if r.check == "rsvp.tunnels_exist")
        self.assertFalse(exist_check.passed)

    @patch("validations.checks.rsvp.get_rsvp_tunnels")
    def test_down_tunnel_fails(self, mock_get):
        """rsvp all_tunnels_up check fails when a tunnel is DOWN."""
        mock_get.return_value = [
            {"name": "tunnel-te1", "destination": "10.0.0.4",
             "state": "UP", "bandwidth": "0"},
            {"name": "tunnel-te2", "destination": "10.0.0.5",
             "state": "DOWN", "bandwidth": "0"},
        ]
        from validations.checks.rsvp import run
        results = run(device="172.16.100.10", role="pe")
        up_check = next(r for r in results if r.check == "rsvp.all_tunnels_up")
        self.assertFalse(up_check.passed)


class TestBgpChecks(unittest.TestCase):

    @patch("validations.checks.bgp.get_bgp_neighbors")
    def test_all_neighbors_established(self, mock_get):
        """bgp checks pass when all neighbors are ESTABLISHED."""
        mock_get.return_value = [
            {"peer": "10.0.0.5", "as": "65000",
             "state": "ESTABLISHED", "family": "l2vpn-evpn"},
            {"peer": "10.0.0.6", "as": "65000",
             "state": "ESTABLISHED", "family": "l2vpn-evpn"},
        ]
        from validations.checks.bgp import run
        results = run(device="172.16.100.20", role="pe")
        self.assertTrue(all(r.passed for r in results))

    @patch("validations.checks.bgp.get_bgp_neighbors")
    def test_no_neighbors_fails(self, mock_get):
        """bgp neighbors_established check fails when no neighbors established."""
        mock_get.return_value = []
        from validations.checks.bgp import run
        results = run(device="172.16.100.20", role="pe")
        est_check = next(r for r in results if r.check == "bgp.neighbors_established")
        self.assertFalse(est_check.passed)

    @patch("validations.checks.bgp.get_bgp_neighbors")
    def test_wrong_address_family_fails(self, mock_get):
        """bgp expected_address_family check fails when AF is missing."""
        mock_get.return_value = [
            {"peer": "10.0.0.5", "as": "65000",
             "state": "ESTABLISHED", "family": "ipv4-unicast"},
        ]
        from validations.checks.bgp import run
        results = run(device="172.16.100.20", role="pe")
        af_check = next(r for r in results if r.check == "bgp.expected_address_family")
        self.assertFalse(af_check.passed)


class TestL2vpnChecks(unittest.TestCase):

    @patch("validations.checks.l2vpn.get_l2vpn_xconnects")
    def test_all_xconnects_up(self, mock_get):
        """l2vpn checks pass when all xconnects are UP."""
        mock_get.return_value = [
            {"group": "CUST-A", "name": "syd-mel-pe1", "state": "UP"},
            {"group": "CUST-B", "name": "syd-mel-pe2", "state": "UP"},
        ]
        from validations.checks.l2vpn import run
        results = run(device="172.16.100.20", role="pe")
        self.assertTrue(all(r.passed for r in results))

    @patch("validations.checks.l2vpn.get_l2vpn_xconnects")
    def test_no_xconnects_fails(self, mock_get):
        """l2vpn xconnects_exist check fails when no xconnects found."""
        mock_get.return_value = []
        from validations.checks.l2vpn import run
        results = run(device="172.16.100.20", role="pe")
        exist_check = next(r for r in results if r.check == "l2vpn.xconnects_exist")
        self.assertFalse(exist_check.passed)

    @patch("validations.checks.l2vpn.get_l2vpn_xconnects")
    def test_down_xconnect_fails(self, mock_get):
        """l2vpn all_xconnects_up check fails when an xconnect is DOWN."""
        mock_get.return_value = [
            {"group": "CUST-A", "name": "syd-mel-pe1", "state": "UP"},
            {"group": "CUST-B", "name": "syd-mel-pe2", "state": "DOWN"},
        ]
        from validations.checks.l2vpn import run
        results = run(device="172.16.100.20", role="pe")
        up_check = next(r for r in results if r.check == "l2vpn.all_xconnects_up")
        self.assertFalse(up_check.passed)


class TestCheckResult(unittest.TestCase):

    def test_status_pass(self):
        """CheckResult.status returns PASS when passed=True."""
        from validations.checks.base import CheckResult
        r = CheckResult(device="syd-p1", check="isis.adjacencies_up", passed=True)
        self.assertEqual(r.status, "PASS")

    def test_status_fail(self):
        """CheckResult.status returns FAIL when passed=False."""
        from validations.checks.base import CheckResult
        r = CheckResult(device="syd-p1", check="isis.adjacencies_up", passed=False)
        self.assertEqual(r.status, "FAIL")

    def test_to_dict(self):
        """CheckResult.to_dict() returns expected keys."""
        from validations.checks.base import CheckResult
        r = CheckResult(device="syd-p1", check="isis.adjacencies_up",
                        passed=True, reason="3/3 UP")
        d = r.to_dict()
        self.assertIn("device", d)
        self.assertIn("check", d)
        self.assertIn("status", d)
        self.assertIn("reason", d)
        self.assertIn("detail", d)


if __name__ == "__main__":
    unittest.main()
