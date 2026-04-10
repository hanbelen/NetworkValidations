#!/usr/bin/env python3
"""
bootstrap/pre_day1.py — Pre-Day1 device discovery and NetBox population.

Pipeline:
    1. fping sweep 172.16.100.0/24 — discover live devices
    2. SSH → IOSvL2 switch — read MAC address table (port → MAC)
    3. NETCONF → each device (parallel) — collect MAC, serial, model
    4. Cross-reference device MAC against switch table → derive role/hostname
    5. Upsert site, manufacturer, device type, role, device, interface, IP in NetBox

Usage:
    python3 -m bootstrap.pre_day1 --site SYD
    python3 -m bootstrap.pre_day1 --site MEL --dry-run
    python3 -m bootstrap.pre_day1 --site SYD --debug

Environment overrides (see config/settings.py for defaults):
    NETBOX_URL  NETBOX_TOKEN  DEVICE_USER  DEVICE_PASS  SWITCH_USER  SWITCH_PASS
"""

import argparse
import logging
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from config.settings import PORT_ROLE_MAP, SWITCH_IP
from lib.device import DeviceClient, DeviceInfo
from lib.netbox import NetBoxClient, NetBoxError
from lib.scanner import scan
from lib.switch import SwitchClient

log = logging.getLogger(__name__)

_MAX_WORKERS = 4


# ── Pure helpers ──────────────────────────────────────────────────────────────

def _derive_hostname(site: str, role_name: str | None, ip: str) -> str:
    """syd + pe1 → syd-pe1.  No role match → unknown-<ip>."""
    return f"{site.lower()}-{role_name}" if role_name else f"unknown-{ip}"


def _role_type(role_name: str) -> str:
    """pe1 → pe,  rr2 → rr,  p1 → p."""
    return re.sub(r"\d+$", "", role_name)


def _collect_one(ip: str) -> DeviceInfo:
    """Thread worker — collect all info from a single device."""
    return DeviceClient(ip).collect()


# ── Pipeline stages ───────────────────────────────────────────────────────────

def _stage_scan() -> list[str]:
    log.info("Stage 1 — network scan")
    live = scan()
    if not live:
        log.error("No live devices found — is the lab running?")
        sys.exit(1)
    return live


def _stage_mac_table() -> dict[str, str]:
    log.info("Stage 2 — switch MAC table  [%s]", SWITCH_IP)
    return SwitchClient(SWITCH_IP).get_mac_table()


def _stage_collect(live_ips: list[str]) -> list[DeviceInfo]:
    log.info("Stage 3 — NETCONF collection  [%d devices, %d workers]",
             len(live_ips), _MAX_WORKERS)
    results: list[DeviceInfo] = []

    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
        futures = {pool.submit(_collect_one, ip): ip for ip in live_ips}
        for future in as_completed(futures):
            ip = futures[future]
            try:
                info = future.result()
                results.append(info)
                log.info(
                    "  %-18s  mac=%-17s  serial=%-14s  model=%s",
                    ip,
                    info.mac    or "—",
                    info.serial or "—",
                    info.model  or "—",
                )
            except Exception as exc:
                log.error("  %-18s  collection failed: %s", ip, exc)

    return results


def _stage_netbox(
    site_name: str,
    devices: list[DeviceInfo],
    mac_port_map: dict[str, str],
) -> None:
    log.info("Stage 4 — NetBox population  [site=%s]", site_name)
    nb      = NetBoxClient()
    site_id = nb.get_or_create_site(site_name)["id"]

    for info in devices:
        if not info.mac:
            log.warning("SKIP  %-18s  no MAC address", info.ip)
            continue

        port      = mac_port_map.get(info.mac_dot)
        role_name = PORT_ROLE_MAP.get(port) if port else None
        hostname  = _derive_hostname(site_name, role_name, info.ip)

        log.info(
            "%-18s  port=%-6s  role=%-5s  → %s",
            info.ip, port or "?", role_name or "?", hostname,
        )

        if not role_name:
            log.warning(
                "SKIP  %-18s  MAC %s not in switch table",
                info.ip, info.mac_dot,
            )
            continue

        try:
            mfr  = nb.get_or_create_manufacturer(info.manufacturer)
            dt   = nb.get_or_create_device_type(
                info.model or "IOS XRv 9000", mfr["id"]
            )
            role = nb.get_or_create_device_role(_role_type(role_name))

            nb.upsert_device(
                hostname       = hostname,
                site_id        = site_id,
                role_id        = role["id"],
                device_type_id = dt["id"],
                serial         = info.serial,
                mac            = info.mac,
                dhcp_ip        = info.ip,
            )
        except NetBoxError as exc:
            log.error("NetBox error  %s: %s", hostname, exc)


def _dry_run_report(
    site_name: str,
    devices: list[DeviceInfo],
    mac_port_map: dict[str, str],
) -> None:
    log.info("Dry run — NetBox writes suppressed")
    for info in devices:
        port      = mac_port_map.get(info.mac_dot) if info.mac_dot else None
        role_name = PORT_ROLE_MAP.get(port) if port else None
        hostname  = _derive_hostname(site_name, role_name, info.ip)
        log.info(
            "  WOULD UPSERT  hostname=%-22s  serial=%-14s  mac=%s",
            hostname, info.serial or "—", info.mac or "—",
        )


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Pre-Day1 device discovery and NetBox population",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--site",    required=True, metavar="SITE",
                   help="Site code (e.g. SYD, MEL)")
    p.add_argument("--dry-run", action="store_true",
                   help="Discover devices but skip all NetBox writes")
    p.add_argument("--debug",   action="store_true",
                   help="Enable DEBUG logging")
    return p.parse_args()


def main() -> None:
    args      = _parse_args()
    site_name = args.site.upper()

    logging.basicConfig(
        level   = logging.DEBUG if args.debug else logging.INFO,
        format  = "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt = "%H:%M:%S",
    )

    log.info("pre_day1  site=%s%s", site_name, "  [DRY RUN]" if args.dry_run else "")

    live_ips     = _stage_scan()
    mac_port_map = _stage_mac_table()
    devices      = _stage_collect(live_ips)

    if args.dry_run:
        _dry_run_report(site_name, devices, mac_port_map)
        return

    _stage_netbox(site_name, devices, mac_port_map)

    identified = sum(
        1 for d in devices
        if d.mac and PORT_ROLE_MAP.get(mac_port_map.get(d.mac_dot))
    )
    log.info(
        "complete  identified=%d  total=%d%s",
        identified, len(devices),
        f"  WARNING: {len(devices)-identified} device(s) unidentified"
        if identified < len(devices) else "",
    )


if __name__ == "__main__":
    main()