#!/usr/bin/env python3
"""
pre_day1.py — Pre-Day1 bootstrap script
1. fping scan 172.16.100.0/24 for live devices
2. SSH to IOSvL2 switch — get MAC table (port -> MAC -> role)
3. SSH to each device via NETCONF — get serial, model, manufacturer
4. Create/update NetBox entries
Usage:
    python3 pre_day1.py --site SYD
"""

import argparse
import subprocess
import sys
import re
import requests
import paramiko
import time
from ncclient import manager
from ncclient.xml_ import to_ele

# ── Config ────────────────────────────────────────────────────────────────────

NETBOX_URL   = "http://localhost:8000"
NETBOX_TOKEN = "SoKwHMv7xcimCoCHCoy2UXEEEpcByDoye0msAWKt"
MGMT_SUBNET  = "172.16.100"
SWITCH_USER  = "cisco"
SWITCH_IP    = "172.16.100.253"
SWITCH_PASS  = "cisco"
DEVICE_USER  = "cisco"
DEVICE_PASS  = "cisco"

HEADERS = {
    "Authorization": f"Token {NETBOX_TOKEN}",
    "Content-Type":  "application/json",
    "Accept":        "application/json",
}

# Port -> role mapping (universal across all sites)
PORT_ROLE_MAP = {
    "Gi0/0": "p1",
    "Gi0/1": "p2",
    "Gi0/2": "rr1",
    "Gi0/3": "rr2",
    "Gi1/0": "tr1",
    "Gi1/1": "tr2",
    "Gi1/2": "pe1",
    "Gi1/3": "pe2",
}

# ── NetBox helpers ─────────────────────────────────────────────────────────────

def nb_get(endpoint, params=None):
    r = requests.get(f"{NETBOX_URL}/api/{endpoint}", headers=HEADERS, params=params)
    r.raise_for_status()
    return r.json()

def nb_post(endpoint, data):
    r = requests.post(f"{NETBOX_URL}/api/{endpoint}", headers=HEADERS, json=data)
    if r.status_code not in (200, 201):
        print(f"  ERROR POST {endpoint}: {r.status_code} — {r.text[:200]}")
        return None
    return r.json()

def nb_patch(endpoint, obj_id, data):
    r = requests.patch(
        f"{NETBOX_URL}/api/{endpoint}{obj_id}/",
        headers=HEADERS,
        json=data
    )
    if r.status_code != 200:
        print(f"  ERROR PATCH {endpoint}{obj_id}: {r.status_code} — {r.text[:200]}")
        return None
    return r.json()

def nb_get_or_create(endpoint, lookup, create_data):
    r = nb_get(endpoint, params=lookup)
    if r["count"] > 0:
        return r["results"][0]
    return nb_post(endpoint, create_data)

# ── Step 1 — fping scan ───────────────────────────────────────────────────────

def fping_scan(subnet, switch_ip):
    print(f"\n[1] Scanning {subnet}.0/24 with fping...")
    result = subprocess.run(
        ["fping", "-a", "-g", f"{subnet}.1", f"{subnet}.252"],
        capture_output=True, text=True
    )
    live_ips = [
        ip.strip() for ip in result.stdout.splitlines()
        if ip.strip() and ip.strip() != switch_ip
    ]
    print(f"  Found {len(live_ips)} live hosts: {live_ips}")
    return live_ips

# ── Step 2 — SSH to switch, get MAC table ─────────────────────────────────────

def get_switch_mac_table(switch_ip):
    print(f"\n[2] Getting MAC table from switch {switch_ip}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=switch_ip,
        username=SWITCH_USER,
        password=SWITCH_PASS,
        timeout=10,
        look_for_keys=False,
        allow_agent=False,
        disabled_algorithms={"pubkeys": ["rsa-sha2-256", "rsa-sha2-512"]}
    )
    channel = client.invoke_shell()
    time.sleep(1)
    channel.send("terminal length 0\n")
    time.sleep(0.5)
    channel.send("show mac address-table\n")
    time.sleep(2)
    output = ""
    while channel.recv_ready():
        output += channel.recv(4096).decode()
    client.close()

    # Parse MAC table
    # Format: Vlan  Mac Address      Type    Ports
    # Example: 1    5254.0003.a7d5   DYNAMIC Gi0/2
    mac_port_map = {}
    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 4 and re.match(
            r'[0-9a-f]{4}\.[0-9a-f]{4}\.[0-9a-f]{4}', parts[1], re.I
        ):
            mac  = parts[1].lower()
            port = parts[3]
            mac_port_map[mac] = port
            print(f"  MAC {mac} → port {port}")
    return mac_port_map

# ── Step 3 — NETCONF to each device ──────────────────────────────────────────

def get_device_info_netconf(ip):
    """Get serial, model, MAC via NETCONF"""
    try:
        with manager.connect(
            host=ip,
            port=830,
            username=DEVICE_USER,
            password=DEVICE_PASS,
            hostkey_verify=False,
            device_params={"name": "iosxr"},
            timeout=30,
        ) as m:
            rpc = to_ele("""
                <rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
                  <get>
                    <filter>
                      <inventory xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-invmgr-oper">
                        <racks>
                          <rack>
                            <slots>
                              <slot>
                                <cards>
                                  <card>
                                    <basic-info/>
                                  </card>
                                </cards>
                              </slot>
                            </slots>
                          </rack>
                        </racks>
                      </inventory>
                    </filter>
                  </get>
                </rpc>
            """)
            response  = m.dispatch(rpc)
            xml_str   = str(response)
            serial    = None
            model     = None

            serial_match = re.search(
                r'<serial-number>([^<]+)</serial-number>', xml_str
            )
            if serial_match:
                serial = serial_match.group(1).strip()

            model_match = re.search(
                r'<model-name>([^<]+)</model-name>', xml_str
            )
            if model_match:
                model = model_match.group(1).strip()

            return {"serial": serial, "model": model, "manufacturer": "Cisco"}

    except Exception as e:
        print(f"  NETCONF INFO ERROR {ip}: {e}")
        return None

def get_mgmt_mac_netconf(ip):
    """Get MAC address of MgmtEth0/RP0/CPU0/0 via NETCONF"""
    try:
        with manager.connect(
            host=ip,
            port=830,
            username=DEVICE_USER,
            password=DEVICE_PASS,
            hostkey_verify=False,
            device_params={"name": "iosxr"},
            timeout=30,
        ) as m:
            rpc = to_ele("""
                <rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="2">
                  <get>
                    <filter>
                      <interfaces xmlns="http://openconfig.net/yang/interfaces">
                        <interface>
                          <name>MgmtEth0/RP0/CPU0/0</name>
                          <state/>
                        </interface>
                      </interfaces>
                    </filter>
                  </get>
                </rpc>
            """)
            response  = m.dispatch(rpc)
            xml_str   = str(response)
            mac_match = re.search(
                r'<mac-address>([^<]+)</mac-address>', xml_str
            )
            if mac_match:
                return mac_match.group(1).strip().lower()
    except Exception as e:
        print(f"  NETCONF MAC ERROR {ip}: {e}")
    return None

# ── Step 4 — NetBox updates ───────────────────────────────────────────────────

def get_or_create_site(site_name):
    return nb_get_or_create(
        "dcim/sites/",
        {"slug": site_name.lower()},
        {"name": site_name, "slug": site_name.lower()}
    )

def get_or_create_manufacturer(name):
    slug = name.lower().replace(" ", "-")
    return nb_get_or_create(
        "dcim/manufacturers/",
        {"slug": slug},
        {"name": name, "slug": slug}
    )

def get_or_create_device_type(model, manufacturer_id):
    slug = re.sub(r'[^a-z0-9-]', '-', model.lower()).strip('-')
    return nb_get_or_create(
        "dcim/device-types/",
        {"slug": slug},
        {"model": model, "slug": slug, "manufacturer": manufacturer_id}
    )

def get_or_create_device_role(role_type):
    role_colors = {
        "p":  "aa1409",
        "pe": "f44336",
        "rr": "e91e63",
        "tr": "9c27b0",
    }
    color = role_colors.get(role_type, "607d8b")
    return nb_get_or_create(
        "dcim/device-roles/",
        {"slug": role_type},
        {"name": role_type.upper(), "slug": role_type, "color": color}
    )

def create_or_update_device(
    hostname, site_id, role_id, device_type_id, serial, mac, ip
):
    existing = nb_get("dcim/devices/", params={"name": hostname})
    device_data = {
        "name":        hostname,
        "site":        site_id,
        "role":        role_id,
        "device_type": device_type_id,
        "status":      "planned",
        "serial":      serial or "",
        "custom_fields": {
            "serial_number": serial,
        }
    }
    if existing["count"] > 0:
        dev = nb_patch("dcim/devices/", existing["results"][0]["id"], device_data)
        print(f"  UPDATED device {hostname}")
    else:
        dev = nb_post("dcim/devices/", device_data)
        print(f"  CREATED device {hostname}")

    if not dev:
        return None

    dev_id = dev["id"]

    # MgmtEth interface + MAC
    if mac:
        nb_get_or_create(
            "dcim/interfaces/",
            {"device_id": dev_id, "name": "MgmtEth0/RP0/CPU0/0"},
            {
                "device":      dev_id,
                "name":        "MgmtEth0/RP0/CPU0/0",
                "type":        "1000base-t",
                "mac_address": mac.upper(),
                "mgmt_only":   True,
                "enabled":     True,
            }
        )
        print(f"  MAC {mac} assigned to MgmtEth0/RP0/CPU0/0")

    # DHCP IP
    nb_get_or_create(
        "ipam/ip-addresses/",
        {"address": f"{ip}/24"},
        {"address": f"{ip}/24", "status": "active"}
    )
    print(f"  IP {ip}/24 created")
    return dev

# ── Main ───────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="Pre-Day1 bootstrap")
    parser.add_argument("--site",      required=True, help="Site name e.g. SYD or MEL")

    return parser.parse_args()

def main():
    args      = parse_args()
    site_name = args.site.upper()
    switch_ip = SWITCH_IP

    print(f"\n{'='*60}")
    print(f"Pre-Day1 Bootstrap — Site: {site_name}")
    print(f"{'='*60}")

    # Step 1 — fping scan
    live_ips = fping_scan(MGMT_SUBNET, switch_ip)
    if not live_ips:
        print("No live devices found. Exiting.")
        sys.exit(1)

    # Step 2 — switch MAC table
    mac_port_map = get_switch_mac_table(switch_ip)

    # Step 3 — device info via NETCONF
    print(f"\n[3] Getting device info via NETCONF...")
    device_info = {}

    for ip in live_ips:
        print(f"\n  Connecting to {ip}...")
        mgmt_mac = get_mgmt_mac_netconf(ip)
        info     = get_device_info_netconf(ip)

        if not mgmt_mac:
            print(f"  {ip} — could not get MAC, skipping")
            continue

        # Normalize MAC to dot notation for matching
        mac_clean = mgmt_mac.replace(":", "").replace("-", "").replace(".", "")
        mac_dot   = ".".join([mac_clean[i:i+4] for i in range(0, 12, 4)])

        port      = mac_port_map.get(mac_dot)
        role_name = PORT_ROLE_MAP.get(port) if port else None
        hostname  = f"{site_name.lower()}-{role_name}" if role_name else f"unknown-{ip}"

        device_info[ip] = {
            "mac":          mgmt_mac,
            "mac_dot":      mac_dot,
            "port":         port,
            "role":         role_name,
            "hostname":     hostname,
            "serial":       info.get("serial") if info else None,
            "model":        info.get("model")  if info else "IOS XRv 9000",
            "manufacturer": info.get("manufacturer") if info else "Cisco",
        }
        print(
            f"  {ip} → port:{port} role:{role_name} "
            f"hostname:{hostname} serial:{device_info[ip]['serial']}"
        )

    # Step 4 — NetBox
    print(f"\n[4] Updating NetBox...")
    site    = get_or_create_site(site_name)
    site_id = site["id"]

    for ip, info in device_info.items():
        if not info["role"]:
            print(f"  SKIP {ip} — no role identified")
            continue

        manufacturer  = get_or_create_manufacturer(info["manufacturer"])
        device_type   = get_or_create_device_type(
            info["model"], manufacturer["id"]
        )
        role_type     = re.sub(r'\d+', '', info["role"])
        role          = get_or_create_device_role(role_type)

        create_or_update_device(
            hostname       = info["hostname"],
            site_id        = site_id,
            role_id        = role["id"],
            device_type_id = device_type["id"],
            serial         = info["serial"],
            mac            = info["mac"],
            ip             = ip,
        )

    print(f"\n✅ Pre-Day1 bootstrap complete for site {site_name}!")
    print(f"   Devices discovered: {len(device_info)}")

if __name__ == "__main__":
    main()
