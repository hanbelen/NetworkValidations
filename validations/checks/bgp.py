"""
BGP EVPN validation checks.
Applies to: PE, RR, TR
"""


import logging

from lib.netconf import get_bgp_neighbors
from validations.checks.base import CheckResult

log = logging.getLogger(__name__)

# Expected BGP address families per role
EXPECTED_FAMILIES = {
    "pe": "l2vpn-evpn",
    "rr": "l2vpn-evpn",
    "tr": "ipv4-unicast",
}


def run(device: str, role: str) -> list[CheckResult]:
    """Run all BGP checks for a device."""
    results = []

    try:
        neighbors = get_bgp_neighbors(device)
    except Exception as exc:
        return [CheckResult(device=device, check="bgp.reachable",
                            passed=False, reason=str(exc))]

    # Check 1 — at least one BGP neighbor is established
    established = [n for n in neighbors if n["state"].upper() == "ESTABLISHED"]
    results.append(CheckResult(
        device  = device,
        check   = "bgp.neighbors_established",
        passed  = len(established) > 0,
        reason  = f"{len(established)}/{len(neighbors)} neighbors established",
        detail  = {"neighbors": neighbors},
    ))

    # Check 2 — expected address family is present
    expected_af = EXPECTED_FAMILIES.get(role)
    if expected_af:
        has_af = any(
            expected_af in n.get("family", "").lower()
            for n in established
        )
        results.append(CheckResult(
            device  = device,
            check   = "bgp.expected_address_family",
            passed  = has_af,
            reason  = f"expected {expected_af} in established neighbors",
        ))

    # Check 3 — no neighbors stuck in non-established state
    non_est = [n for n in neighbors if n["state"].upper() != "ESTABLISHED"]
    results.append(CheckResult(
        device  = device,
        check   = "bgp.no_stuck_neighbors",
        passed  = len(non_est) == 0,
        reason  = f"{len(non_est)} non-established neighbors",
        detail  = {"non_established": non_est},
    ))

    return results
