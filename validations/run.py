#!/usr/bin/env python3
"""
validations/run.py — Day 1 validation orchestrator.

Pulls devices from NetBox, runs the appropriate checks per device role,
and reports results to console and JSON.

Usage:
    python3 -m validations.run --site SYD --step day1 --stage isis
    python3 -m validations.run --site SYD --step day1 --stage bgp
    python3 -m validations.run --site SYD --step day1 --stage l2vpn

Exit codes:
    0 — all checks passed
    1 — one or more checks failed
"""


import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from lib.netbox import NetBoxClient
from validations.checks.base import CheckResult

# Import check modules
from validations.checks import isis, ldp, rsvp, bgp, l2vpn

log = logging.getLogger(__name__)

# Which checks run per role per stage
ROLE_STAGE_MAP: dict[str, dict[str, bool]] = {
    "p":  {"isis": True,  "ldp": True,  "rsvp": True,  "bgp": False, "l2vpn": False},
    "pe": {"isis": True,  "ldp": True,  "rsvp": True,  "bgp": True,  "l2vpn": True },
    "rr": {"isis": True,  "ldp": True,  "rsvp": False, "bgp": True,  "l2vpn": False},
    "tr": {"isis": True,  "ldp": True,  "rsvp": False, "bgp": True,  "l2vpn": False},
}

# Map stage name → check module
STAGE_CHECKS = {
    "isis":  isis,
    "ldp":   ldp,
    "rsvp":  rsvp,
    "bgp":   bgp,
    "l2vpn": l2vpn,
}


# ── NetBox helpers ─────────────────────────────────────────────────────────────

def get_devices_from_netbox(site: str) -> list[dict]:
    """
    Pull all devices for a site from NetBox.
    Returns list of {hostname, ip, role} dicts.
    """
    nb      = NetBoxClient()
    result  = nb.get("dcim/devices/", params={"site": site.lower(), "limit": 100})
    devices = []

    for dev in result.get("results", []):
        # Get primary IP
        ip_data = dev.get("primary_ip") or {}
        ip      = ip_data.get("address", "").split("/")[0] if ip_data else None

        # Get role slug (p, pe, rr, tr)
        role_data = dev.get("role") or {}
        role      = role_data.get("slug", "")

        if not ip:
            log.warning("SKIP %s — no primary IP in NetBox", dev["name"])
            continue

        devices.append({
            "hostname": dev["name"],
            "ip":       ip,
            "role":     role,
        })

    log.info("Found %d devices in NetBox for site %s", len(devices), site)
    return devices


# ── Result reporting ───────────────────────────────────────────────────────────

def print_results(results: list[CheckResult]) -> None:
    """Print a formatted pass/fail table to console."""
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)

    log.info("─" * 60)
    for r in results:
        icon = "✅" if r.passed else "❌"
        log.info("%s  %-25s  %-35s  %s", icon, r.device, r.check, r.reason)
    log.info("─" * 60)
    log.info("Total: %d passed  %d failed", passed, failed)


def save_results(
    results: list[CheckResult],
    site: str,
    stage: str,
    step: str,
) -> Path:
    """Save results to a JSON file for Jenkins and audit trail."""
    Path("results").mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filepath  = Path(f"results/{site}_{step}_{stage}_{timestamp}.json")

    payload = {
        "site":      site,
        "step":      step,
        "stage":     stage,
        "timestamp": timestamp,
        "summary": {
            "total":  len(results),
            "passed": sum(1 for r in results if r.passed),
            "failed": sum(1 for r in results if not r.passed),
        },
        "results": [r.to_dict() for r in results],
    }

    filepath.write_text(json.dumps(payload, indent=2))
    log.info("Results saved → %s", filepath)
    return filepath


# ── Pipeline ───────────────────────────────────────────────────────────────────

def run_stage(
    devices: list[dict],
    stage: str,
) -> list[CheckResult]:
    """
    Run a single validation stage across all eligible devices.
    Skips devices where the stage doesn't apply to their role.
    """
    check_module = STAGE_CHECKS[stage]
    all_results: list[CheckResult] = []

    for dev in devices:
        role      = dev["role"]
        role_map  = ROLE_STAGE_MAP.get(role, {})

        if not role_map.get(stage, False):
            log.debug("SKIP  %-20s  stage=%s not applicable for role=%s",
                      dev["hostname"], stage, role)
            continue

        log.info("CHECK %-20s  stage=%s  role=%s", dev["hostname"], stage, role)
        results = check_module.run(device=dev["ip"], role=role)

        for r in results:
            # Replace IP with hostname in results for readability
            r.device = dev["hostname"]
            all_results.append(r)

    return all_results


# ── Entry point ────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run network validations for a site and stage"
    )
    p.add_argument("--site",  required=True,
                   help="Site code e.g. SYD, MEL")
    p.add_argument("--step",  required=True,
                   choices=["day1", "day2", "pre_change", "post_change"],
                   help="Pipeline step")
    p.add_argument("--stage", required=True,
                   choices=list(STAGE_CHECKS.keys()),
                   help="Validation stage to run")
    p.add_argument("--debug", action="store_true",
                   help="Enable debug logging")
    return p.parse_args()


def main() -> None:
    args      = _parse_args()
    site_name = args.site.upper()

    logging.basicConfig(
        level   = logging.DEBUG if args.debug else logging.INFO,
        format  = "%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt = "%H:%M:%S",
    )

    log.info("Validation  site=%s  step=%s  stage=%s",
             site_name, args.step, args.stage)

    devices = get_devices_from_netbox(site_name)
    if not devices:
        log.error("No devices found in NetBox for site %s", site_name)
        sys.exit(1)

    results = run_stage(devices, args.stage)

    print_results(results)
    save_results(results, site_name, args.stage, args.step)

    # Exit 1 if any check failed — Jenkins will catch this
    if any(not r.passed for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()