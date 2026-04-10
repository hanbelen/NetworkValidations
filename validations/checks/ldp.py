"""
LDP validation checks.
Applies to: P, PE, RR, TR
"""


import logging

from lib.netconf import get_ldp_sessions
from validations.checks.base import CheckResult

log = logging.getLogger(__name__)


def run(device: str, role: str) -> list[CheckResult]:
    """Run all LDP checks for a device."""
    results = []

    try:
        sessions = get_ldp_sessions(device)
    except Exception as exc:
        return [CheckResult(device=device, check="ldp.reachable",
                            passed=False, reason=str(exc))]

    # Check 1 — at least one LDP session is operational
    operational = [s for s in sessions if s["state"].upper() == "OPERATIONAL"]
    results.append(CheckResult(
        device  = device,
        check   = "ldp.sessions_operational",
        passed  = len(operational) > 0,
        reason  = f"{len(operational)}/{len(sessions)} sessions operational",
        detail  = {"sessions": sessions},
    ))

    # Check 2 — no sessions stuck in non-operational state
    non_op = [s for s in sessions if s["state"].upper() != "OPERATIONAL"]
    results.append(CheckResult(
        device  = device,
        check   = "ldp.no_stuck_sessions",
        passed  = len(non_op) == 0,
        reason  = f"{len(non_op)} non-operational sessions found",
        detail  = {"non_operational": non_op},
    ))

    return results
