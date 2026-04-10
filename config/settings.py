"""
Central configuration.
Sensitive values can be overridden via environment variables.
"""

import os

NETBOX_URL   = os.environ.get("NETBOX_URL",   "http://localhost:8000")
NETBOX_TOKEN = os.environ.get("NETBOX_TOKEN", "SoKwHMv7xcimCoCHCoy2UXEEEpcByDoye0msAWKt")

MGMT_SUBNET     = "172.16.100"
MGMT_SCAN_START = 1
MGMT_SCAN_END   = 252

SWITCH_IP   = "172.16.100.253"
SWITCH_USER = os.environ.get("SWITCH_USER", "cisco")
SWITCH_PASS = os.environ.get("SWITCH_PASS", "cisco")

DEVICE_USER = os.environ.get("DEVICE_USER", "cisco")
DEVICE_PASS = os.environ.get("DEVICE_PASS", "cisco")

# IOS XR exposes NETCONF on port 22 (SSH subsystem), not the standard port 830
NETCONF_PORT    = 22
NETCONF_TIMEOUT = 30

# Maps IOSvL2 switch port → device role. Same for all sites.
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

ROLE_COLORS = {
    "p":  "aa1409",
    "pe": "f44336",
    "rr": "e91e63",
    "tr": "9c27b0",
}