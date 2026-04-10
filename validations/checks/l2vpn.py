"""
EVPN VPWS xconnect validation checks.
Applies to: PE only
"""


import logging

from lib.netconf import get_l2vpn_xconnects
from validations.checks.base import CheckResult

log = logging.getLogger(__name__)


def run(device: str, role: str) -> list[CheckResult]:
    """Run all L2VPN checks for a device."""
    results = []

    try:
        xconnects = get_l2vpn_xconnects(device)
    except Exception as exc:
        return [CheckResult(device=device, check="l2vpn.reachable",
                            passed=False, reason=str(exc))]

    # Check 1 — at least one xconnect exists
    results.append(CheckResult(
        device  = device,
        check   = "l2vpn.xconnects_exist",
        passed  = len(xconnects) > 0,
        reason  = f"{len(xconnects)} xconnects found",
        detail  = {"xconnects": xconnects},
    ))

    if not xconnects:
        return results

    # Check 2 — all xconnects are UP
    down = [x for x in xconnects if x["state"].upper() != "UP"]
    results.append(CheckResult(
        device  = device,
        check   = "l2vpn.all_xconnects_up",
        passed  = len(down) == 0,
        reason  = f"{len(down)}/{len(xconnects)} xconnects down",
        detail  = {"down_xconnects": down},
    ))

    return results
