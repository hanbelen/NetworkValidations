# NetworkValidations

pyATS validation scripts for CML lab — pre and post deployment checks via NETCONF.

## Structure
- `tests/` — Reusable test modules (interfaces, hardware, routing, MPLS, reachability)
- `day0.py` — Pre-deployment checks (interfaces up, no hardware errors, base config only)
- `day1.py` — Post Day 1 stage checks (ISIS, LDP, RSVP-TE, L2VPN)
- `day2.py` — Pre/post Day 2 delta change checks
- `testbed/` — pyATS testbed config (testbed.yml is gitignored — contains credentials)

## Usage
```bash
# Day 0 pre-checks
python3 day0.py --testbed testbed/testbed.yml

# Day 1 post-checks (specific stage)
python3 day1.py --testbed testbed/testbed.yml --tests isis,ldp

# Day 2 checks
python3 day2.py --testbed testbed/testbed.yml
```
