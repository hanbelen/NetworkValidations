"""
Ping sweep the management subnet using fping.
"""


import logging
import subprocess

from config.settings import MGMT_SUBNET, MGMT_SCAN_START, MGMT_SCAN_END, SWITCH_IP

log = logging.getLogger(__name__)


def scan(exclude: list[str] | None = None) -> list[str]:
    """
    Return sorted list of live IPs on the management subnet.
    The switch IP is always excluded from results.
    """
    excluded = set(exclude or [])
    excluded.add(SWITCH_IP)

    result = subprocess.run(
        ["fping", "-a", "-g",
         f"{MGMT_SUBNET}.{MGMT_SCAN_START}",
         f"{MGMT_SUBNET}.{MGMT_SCAN_END}"],
        capture_output=True,
        text=True,
    )

    live = sorted(
        ip.strip()
        for ip in result.stdout.splitlines()
        if ip.strip() and ip.strip() not in excluded
    )

    log.info("Scan complete — %d live hosts found", len(live))
    return live