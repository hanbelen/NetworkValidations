"""
RSVP-TE validation checks.
Applies to: P, PE only
"""


import logging

from lib.netconf import get_rsvp_tunnels
from validations.checks.base import CheckResult

log = logging.getLogger(__name__)


def run(device: str, role: str) -> list[CheckResult]:
    """Run all RSVP-TE checks for a device."""
    results = []

    try:
        tunnels = get_rsvp_tunnels(device)
    except Exception as exc:
        return [CheckResult(device=device, check="rsvp.reachable",
                            passed=False, reason=str(exc))]

    # Check 1 — at least one tunnel exists
    results.append(CheckResult(
        device  = device,
        check   = "rsvp.tunnels_exist",
        passed  = len(tunnels) > 0,
        reason  = f"{len(tunnels)} tunnels found",
        detail  = {"tunnels": tunnels},
    ))

    if not tunnels:
        return results

    # Check 2 — all tunnels are UP
    down = [t for t in tunnels if t["state"].upper() != "UP"]
    results.append(CheckResult(
        device  = device,
        check   = "rsvp.all_tunnels_up",
        passed  = len(down) == 0,
        reason  = f"{len(down)}/{len(tunnels)} tunnels down",
        detail  = {"down_tunnels": down},
    ))

    return results
