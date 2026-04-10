"""
NetBox REST API client with idempotent get_or_create helpers.
"""


import logging
import re

import requests

from config.settings import NETBOX_URL, NETBOX_TOKEN, ROLE_COLORS

log = logging.getLogger(__name__)

_HEADERS = {
    "Authorization": f"Token {NETBOX_TOKEN}",
    "Content-Type":  "application/json",
    "Accept":        "application/json",
}


class NetBoxError(Exception):
    pass


class NetBoxClient:

    # ── HTTP primitives ────────────────────────────────────────────────────────

    def get(self, endpoint: str, params: dict | None = None) -> dict:
        r = requests.get(f"{NETBOX_URL}/api/{endpoint}", headers=_HEADERS,
                         params=params, timeout=10)
        r.raise_for_status()
        return r.json()

    def post(self, endpoint: str, data: dict) -> dict:
        r = requests.post(f"{NETBOX_URL}/api/{endpoint}", headers=_HEADERS,
                          json=data, timeout=10)
        if r.status_code not in (200, 201):
            raise NetBoxError(f"POST {endpoint} → {r.status_code}: {r.text[:200]}")
        return r.json()

    def patch(self, endpoint: str, obj_id: int, data: dict) -> dict:
        r = requests.patch(f"{NETBOX_URL}/api/{endpoint}{obj_id}/",
                           headers=_HEADERS, json=data, timeout=10)
        if r.status_code != 200:
            raise NetBoxError(f"PATCH {endpoint}{obj_id} → {r.status_code}: {r.text[:200]}")
        return r.json()

    def get_or_create(self, endpoint: str, lookup: dict, data: dict) -> dict:
        """Return existing object matching lookup, or create it."""
        result = self.get(endpoint, params=lookup)
        if result["count"] > 0:
            return result["results"][0]
        return self.post(endpoint, data)

    # ── Domain helpers ─────────────────────────────────────────────────────────

    def get_or_create_site(self, name: str) -> dict:
        slug = name.lower()
        return self.get_or_create("dcim/sites/", {"slug": slug},
                                  {"name": name, "slug": slug})

    def get_or_create_manufacturer(self, name: str) -> dict:
        slug = name.lower().replace(" ", "-")
        return self.get_or_create("dcim/manufacturers/", {"slug": slug},
                                  {"name": name, "slug": slug})

    def get_or_create_device_type(self, model: str, manufacturer_id: int) -> dict:
        slug = re.sub(r"[^a-z0-9-]", "-", model.lower()).strip("-")
        return self.get_or_create("dcim/device-types/", {"slug": slug},
                                  {"model": model, "slug": slug,
                                   "manufacturer": manufacturer_id})

    def get_or_create_device_role(self, role_type: str) -> dict:
        color = ROLE_COLORS.get(role_type, "607d8b")
        return self.get_or_create("dcim/device-roles/", {"slug": role_type},
                                  {"name": role_type.upper(), "slug": role_type,
                                   "color": color})

    def upsert_device(
        self,
        hostname: str,
        site_id: int,
        role_id: int,
        device_type_id: int,
        serial: str | None,
        mac: str | None,
        dhcp_ip: str,
    ) -> dict | None:
        """Create or update a device record, interface, and IP in NetBox."""
        payload = {
            "name": hostname, "site": site_id, "role": role_id,
            "device_type": device_type_id, "status": "planned",
            "serial": serial or "",
            "custom_fields": {"serial_number": serial},
        }

        existing = self.get("dcim/devices/", params={"name": hostname})
        if existing["count"] > 0:
            dev = self.patch("dcim/devices/", existing["results"][0]["id"], payload)
            log.info("UPDATED  %s", hostname)
        else:
            dev = self.post("dcim/devices/", payload)
            log.info("CREATED  %s", hostname)

        if not dev:
            return None

        if mac:
            self.get_or_create(
                "dcim/interfaces/",
                {"device_id": dev["id"], "name": "MgmtEth0/RP0/CPU0/0"},
                {"device": dev["id"], "name": "MgmtEth0/RP0/CPU0/0",
                 "type": "1000base-t", "mac_address": mac.upper(),
                 "mgmt_only": True, "enabled": True},
            )

        self.get_or_create(
            "ipam/ip-addresses/",
            {"address": f"{dhcp_ip}/24"},
            {"address": f"{dhcp_ip}/24", "status": "active"},
        )

        return dev