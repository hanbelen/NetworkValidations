"""
IS-IS validation checks.
Applies to: P, PE, RR, TR
"""


import logging

from lib.netconf import get_isis_adjacencies
from validations.checks.base import CheckResult

log = logging.getLogger(__name__)

# Minimum number of IS-IS adjacencies expected per role
MIN_ADJACENCIES = {
    "p":  2,   # at least 2 neighbors (connected to other P/PE nodes)
    "pe": 1,   # at least 1 neighbor (connected to P)
    "rr": 1,   # at least 1 neighbor
    "tr": 1,   # at least 1 neighbor
}


def run(device: str, role: str) -> list[CheckResult]:
    """Run all IS-IS checks for a device."""
    results = []

    try:
        adjacencies = get_isis_adjacencies(device)
    except Exception as exc:
        return [CheckResult(device=device, check="isis.reachable",
                            passed=False, reason=str(exc))]

    # Check 1 — at least one adjacency is UP
    up = [a for a in adjacencies if a["state"].upper() == "UP"]
    results.append(CheckResult(
        device  = device,
        check   = "isis.adjacencies_up",
        passed  = len(up) > 0,
        reason  = f"{len(up)}/{len(adjacencies)} adjacencies UP",
        detail  = {"adjacencies": adjacencies},
    ))

    # Check 2 — minimum adjacency count for role
    min_count = MIN_ADJACENCIES.get(role, 1)
    results.append(CheckResult(
        device  = device,
        check   = "isis.min_adjacency_count",
        passed  = len(up) >= min_count,
        reason  = f"expected >={min_count}, got {len(up)}",
    ))

    # Check 3 — no Level-1 adjacencies (Level-2 only network)
    l1 = [a for a in adjacencies if "L1" in a.get("level", "")]
    results.append(CheckResult(
        device  = device,
        check   = "isis.level2_only",
        passed  = len(l1) == 0,
        reason  = f"{len(l1)} Level-1 adjacencies found (expected 0)",
    ))

    return results
