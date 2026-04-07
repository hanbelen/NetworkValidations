#!/usr/bin/env python3
"""
day1.py — Post-deployment stage checks
Called after each pipeline stage with --tests flag.
"""

import argparse
import sys
from pyats.topology import loader
from tests.test_interfaces import TestInterfaces
from tests.test_hardware import TestHardware
from tests.test_routing import TestRouting
from tests.test_mpls import TestMpls
from tests.test_reachability import TestReachability


TEST_MAP = {
    'interfaces':  (TestInterfaces,   ['verify_interfaces_up',
                                       'verify_no_input_errors',
                                       'verify_no_output_errors']),
    'hardware':    (TestHardware,     ['verify_platform_state',
                                       'verify_cpu_utilization',
                                       'verify_memory_utilization']),
    'isis':        (TestRouting,      ['verify_isis_adjacencies',
                                       'verify_isis_level2_only',
                                       'verify_loopbacks_in_rib']),
    'ldp':         (TestMpls,         ['verify_ldp_sessions']),
    'rsvp':        (TestMpls,         ['verify_rsvp_sessions']),
    'te_tunnels':  (TestMpls,         ['verify_te_tunnels_up']),
    'bgp':         (TestRouting,      ['verify_loopbacks_in_rib']),
    'evpn':        (TestMpls,         ['verify_ldp_sessions']),
    'l2vpn':       (TestMpls,         ['verify_l2vpn_xconnects']),
    'reachability':(TestReachability, ['verify_loopback_reachability']),
}


def parse_args():
    parser = argparse.ArgumentParser(description='Day 1 post-stage checks')
    parser.add_argument('--site',    required=True, help='Site name e.g. SYD or MEL')
    parser.add_argument('--testbed', required=True, help='Path to testbed YAML')
    parser.add_argument('--tests',   required=True, help='Comma-separated test names')
    return parser.parse_args()


def get_site_devices(testbed, site):
    return [
        name for name, device in testbed.devices.items()
        if name.upper().startswith(site.upper())
    ]


def run_tests(device_name, testbed, test_names):
    results = []
    for test_name in test_names:
        if test_name not in TEST_MAP:
            print(f"  WARN  Unknown test: {test_name} — skipping")
            continue
        test_class, methods = TEST_MAP[test_name]
        tc = test_class()
        try:
            tc.connect(testbed=testbed, device_name=device_name)
            for method in methods:
                getattr(tc, method)()
                print(f"  PASS  {device_name} — {test_name}.{method}")
        except AssertionError as e:
            print(f"  FAIL  {device_name} — {test_name}: {e}")
            results.append(False)
        except Exception as e:
            print(f"  ERROR {device_name} — {test_name}: {e}")
            results.append(False)
        finally:
            tc.disconnect()
    return all(results) if results else True


def main():
    args = parse_args()
    testbed = loader.load(args.testbed)
    devices = get_site_devices(testbed, args.site)
    test_names = [t.strip() for t in args.tests.split(',')]

    if not devices:
        print(f"ERROR: No devices found for site {args.site}")
        sys.exit(1)

    print(f"\nDay 1 checks — site: {args.site} — tests: {test_names}")
    print(f"Devices: {devices}\n")

    failed = [d for d in devices if not run_tests(d, testbed, test_names)]

    if failed:
        print(f"\nFAILED: {failed}")
        sys.exit(1)

    print(f"\nAll checks passed for site {args.site}")
    sys.exit(0)


if __name__ == '__main__':
    main()
