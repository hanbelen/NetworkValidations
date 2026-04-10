"""
Shared NETCONF query functions.
Each function connects to a device, runs a YANG query, and returns parsed data.
Keeping queries here means check files stay clean and vendor-specific
YANG paths are in one place — easy to swap for Juniper/Arista later.
"""


import logging
import re

from ncclient import manager
from ncclient.xml_ import to_ele

from config.settings import DEVICE_USER, DEVICE_PASS, NETCONF_PORT, NETCONF_TIMEOUT

log = logging.getLogger(__name__)


def _connect(host: str) -> manager.Manager:
    return manager.connect(
        host=host,
        port=NETCONF_PORT,
        username=DEVICE_USER,
        password=DEVICE_PASS,
        hostkey_verify=False,
        device_params={"name": "iosxr"},
        timeout=NETCONF_TIMEOUT,
        look_for_keys=False,
        allow_agent=False,
    )


def _dispatch(host: str, rpc_xml: str) -> str:
    """Open a NETCONF session, dispatch an RPC, return raw XML string."""
    try:
        with _connect(host) as m:
            return str(m.dispatch(to_ele(rpc_xml)))
    except Exception as exc:
        log.error("NETCONF error on %s: %s", host, exc)
        raise


# ── IS-IS ─────────────────────────────────────────────────────────────────────

def get_isis_adjacencies(host: str) -> list[dict]:
    """
    Return list of IS-IS adjacencies.
    Each entry: {neighbor_id, interface, state, level}
    """
    xml = _dispatch(host, """
        <rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
          <get>
            <filter>
              <isis xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-clns-isis-oper">
                <instances>
                  <instance>
                    <neighbors/>
                  </instance>
                </instances>
              </isis>
            </filter>
          </get>
        </rpc>
    """)

    adjacencies = []
    for block in re.findall(r"<neighbor>(.*?)</neighbor>", xml, re.DOTALL):
        def _find(tag: str) -> str:
            m = re.search(rf"<{tag}>([^<]+)</{tag}>", block)
            return m.group(1).strip() if m else ""
        adjacencies.append({
            "neighbor_id": _find("neighbor-id"),
            "interface":   _find("interface-name"),
            "state":       _find("adjacency-state"),
            "level":       _find("local-isisid"),
        })

    return adjacencies


# ── LDP ───────────────────────────────────────────────────────────────────────

def get_ldp_sessions(host: str) -> list[dict]:
    """
    Return list of LDP sessions.
    Each entry: {peer, state}
    """
    xml = _dispatch(host, """
        <rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="2">
          <get>
            <filter>
              <mpls-ldp xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-mpls-ldp-oper">
                <global>
                  <active>
                    <default-vrf>
                      <neighbors/>
                    </default-vrf>
                  </active>
                </global>
              </mpls-ldp>
            </filter>
          </get>
        </rpc>
    """)

    sessions = []
    for block in re.findall(r"<neighbor>(.*?)</neighbor>", xml, re.DOTALL):
        def _find(tag: str) -> str:
            m = re.search(rf"<{tag}>([^<]+)</{tag}>", block)
            return m.group(1).strip() if m else ""
        sessions.append({
            "peer":  _find("lsr-id"),
            "state": _find("session-state"),
        })

    return sessions


# ── RSVP-TE ───────────────────────────────────────────────────────────────────

def get_rsvp_tunnels(host: str) -> list[dict]:
    """
    Return list of RSVP-TE tunnels.
    Each entry: {name, destination, state, bandwidth}
    """
    xml = _dispatch(host, """
        <rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="3">
          <get>
            <filter>
              <mpls-te xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-mpls-te-oper">
                <tunnels>
                  <summary/>
                </tunnels>
              </mpls-te>
            </filter>
          </get>
        </rpc>
    """)

    tunnels = []
    for block in re.findall(r"<tunnel-info>(.*?)</tunnel-info>", xml, re.DOTALL):
        def _find(tag: str) -> str:
            m = re.search(rf"<{tag}>([^<]+)</{tag}>", block)
            return m.group(1).strip() if m else ""
        tunnels.append({
            "name":        _find("tunnel-name"),
            "destination": _find("destination-address"),
            "state":       _find("tunnel-state"),
            "bandwidth":   _find("bandwidth"),
        })

    return tunnels


# ── BGP ───────────────────────────────────────────────────────────────────────

def get_bgp_neighbors(host: str) -> list[dict]:
    """
    Return list of BGP neighbors.
    Each entry: {peer, as, state, family}
    """
    xml = _dispatch(host, """
        <rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="4">
          <get>
            <filter>
              <bgp xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ipv4-bgp-oper">
                <instances>
                  <instance>
                    <instance-active>
                      <default-vrf>
                        <neighbors/>
                      </default-vrf>
                    </instance-active>
                  </instance>
                </instances>
              </bgp>
            </filter>
          </get>
        </rpc>
    """)

    neighbors = []
    for block in re.findall(r"<neighbor>(.*?)</neighbor>", xml, re.DOTALL):
        def _find(tag: str) -> str:
            m = re.search(rf"<{tag}>([^<]+)</{tag}>", block)
            return m.group(1).strip() if m else ""
        neighbors.append({
            "peer":   _find("neighbor-address"),
            "as":     _find("remote-as"),
            "state":  _find("connection-state"),
            "family": _find("af-name"),
        })

    return neighbors


# ── L2VPN ─────────────────────────────────────────────────────────────────────

def get_l2vpn_xconnects(host: str) -> list[dict]:
    """
    Return list of EVPN VPWS xconnects.
    Each entry: {group, name, state}
    """
    xml = _dispatch(host, """
        <rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="5">
          <get>
            <filter>
              <l2vpn-forwarding xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-l2vpn-oper">
                <nodes>
                  <node>
                    <l2fib-xcon-details/>
                  </node>
                </nodes>
              </l2vpn-forwarding>
            </filter>
          </get>
        </rpc>
    """)

    xconnects = []
    for block in re.findall(r"<l2fib-xcon-detail>(.*?)</l2fib-xcon-detail>",
                            xml, re.DOTALL):
        def _find(tag: str) -> str:
            m = re.search(rf"<{tag}>([^<]+)</{tag}>", block)
            return m.group(1).strip() if m else ""
        xconnects.append({
            "group": _find("group-name"),
            "name":  _find("xcon-name"),
            "state": _find("state"),
        })

    return xconnects
