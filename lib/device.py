"""
NETCONF client
Collects management MAC address, serial number, and model from each device.
"""


import logging
import re
from dataclasses import dataclass, field

from ncclient import manager
from ncclient.xml_ import to_ele

from config.settings import DEVICE_USER, DEVICE_PASS, NETCONF_PORT, NETCONF_TIMEOUT

log = logging.getLogger(__name__)


@dataclass
class DeviceInfo:
    ip:           str
    mac:          str | None = None
    serial:       str | None = None
    model:        str | None = None
    manufacturer: str        = field(default="Cisco")

    @property
    def mac_dot(self) -> str | None:
        """Normalise MAC to Cisco dot notation: 52:54:00:03:a7:d5 → 5254.0003.a7d5"""
        if not self.mac:
            return None
        clean = self.mac.replace(":", "").replace("-", "").replace(".", "")
        return ".".join(clean[i:i+4] for i in range(0, 12, 4))


class DeviceClient:

    def __init__(self, host: str):
        self.host = host

    def _connect(self) -> manager.Manager:
        return manager.connect(
            host=self.host,
            port=NETCONF_PORT,
            username=DEVICE_USER,
            password=DEVICE_PASS,
            hostkey_verify=False,
            device_params={"name": "iosxr"},
            timeout=NETCONF_TIMEOUT,
            look_for_keys=False,
            allow_agent=False,
        )

    def get_mgmt_mac(self) -> str | None:
        """Get MAC address of MgmtEth0/RP0/CPU0/0."""
        rpc = to_ele("""
            <rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
              <get>
                <filter>
                  <interfaces xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-pfi-im-cmd-oper">
                    <interface-xr>
                      <interface>
                        <interface-name>MgmtEth0/RP0/CPU0/0</interface-name>
                        <mac-address/>
                      </interface>
                    </interface-xr>
                  </interfaces>
                </filter>
              </get>
            </rpc>
        """)
        try:
            with self._connect() as m:
                xml = str(m.dispatch(rpc))

            match = re.search(
                r"<address>([0-9a-f]{2}(?::[0-9a-f]{2}){5})</address>",
                xml, re.IGNORECASE,
            ) or re.search(r"<mac-address>([^<]+)</mac-address>", xml)

            return match.group(1).strip().lower() if match else None

        except Exception as exc:
            log.error("MAC error on %s: %s", self.host, exc)
            return None

    def get_inventory(self) -> tuple[str | None, str | None]:
        """
        Return (serial, model).
        Uses the RP serial (R-IOSXRV9000-RP-C) — most stable identifier.
        """
        rpc = to_ele("""
            <rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="2">
              <get>
                <filter>
                  <inventory xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-invmgr-oper">
                    <racks><rack><slots><slot><cards><card>
                      <basic-info/>
                    </card></cards></slot></slots></rack></racks>
                  </inventory>
                </filter>
              </get>
            </rpc>
        """)
        try:
            with self._connect() as m:
                xml = str(m.dispatch(rpc))

            rp = re.search(
                r"R-IOSXRV9000-RP-C.*?<serial-number>([^<]+)</serial-number>",
                xml, re.DOTALL,
            )
            sn = rp or re.search(r"<serial-number>([^<]+)</serial-number>", xml)
            mn = re.search(r"<model-name>([^<]+)</model-name>", xml)

            return (
                sn.group(1).strip() if sn else None,
                mn.group(1).strip() if mn else None,
            )

        except Exception as exc:
            log.error("Inventory error on %s: %s", self.host, exc)
            return None, None

    def collect(self) -> DeviceInfo:
        """Collect all device attributes and return as a DeviceInfo."""
        log.info("Collecting from %s", self.host)
        mac           = self.get_mgmt_mac()
        serial, model = self.get_inventory()
        return DeviceInfo(ip=self.host, mac=mac, serial=serial, model=model)