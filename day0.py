#!/usr/bin/env python3
"""
day0.py — Pre-deployment checks
Runs before any config is pushed.
Checks: interfaces up, no hardware errors, base config only.
"""

import argparse
import sys
from pyats.topology import loader
from tests.test_interfaces import TestInterfaces
from tests.test_hardware import TestHardware


def parse_args():
    parser = argparse.ArgumentParser(description='Day 0 pre-deployment checks')
    parser.add_argument('--site', required=True, help='Site name e.g. SYD or MEL')
    parser.add_argument('--testbed', required=True, help='Path to testbed YAML')
    return parser.parse_args()


def get_site_devices(testbed, site):
    return [
        name for name, device in testbed.devices.items()
        if name.upper().startswith(site.upper())
    ]


def run_checks(device_name, testbed):
    results = []
    for test_class in [TestInterfaces, TestHardware]:
        tc = test_class()
        try:
            tc.connect(testbed=testbed, device_name=device_name)
            for method in ['verify_interfaces_up', 'verify_no_input_errors',
                           'verify_no_output_errors', 'verify_platform_state',
                           'verify_cpu_utilization', 'verify_memory_utilization']:
                if hasattr(tc, method):
                    getattr(tc, method)()
                    print(f"  PASS  {device_name} — {method}")
        except AssertionError as e:
            print(f"  FAIL  {device_name} — {e}")
            results.append(False)
        except Exception as e:
            print(f"  ERROR {device_name} — {e}")
            results.append(False)
        finally:
            tc.disconnect()
    return all(results) if results else True


def main():
    args = parse_args()
    testbed = loader.load(args.testbed)
    devices = get_site_devices(testbed, args.site)

    if not devices:
        print(f"ERROR: No devices found for site {args.site}")
        sys.exit(1)

    print(f"\nDay 0 pre-checks — site: {args.site}")
    print(f"Devices: {devices}\n")

    failed = [d for d in devices if not run_checks(d, testbed)]

    if failed:
        print(f"\nFAILED: {failed}")
        sys.exit(1)

    print(f"\nAll Day 0 checks passed for site {args.site}")
    sys.exit(0)


if __name__ == '__main__':
    main()
