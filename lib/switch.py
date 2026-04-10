"""
IOSvL2 management switch client.
Retrieves the MAC address table via SSH CLI.
"""


import logging
import re
import time

import paramiko

from config.settings import SWITCH_USER, SWITCH_PASS

log = logging.getLogger(__name__)


class SwitchClient:

    def __init__(self, host: str):
        self.host = host

    def get_mac_table(self) -> dict[str, str]:
        """
        SSH into the switch and return the MAC address table.

        Returns:
            {mac_in_dot_notation: switch_port}
            e.g. {"5254.0003.a7d5": "Gi0/2"}
        """
        log.info("Fetching MAC table from %s", self.host)
        output = self._run("show mac address-table")
        return self._parse(output)

    def _run(self, command: str) -> str:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=self.host,
            username=SWITCH_USER,
            password=SWITCH_PASS,
            timeout=10,
            look_for_keys=False,
            allow_agent=False,
            disabled_algorithms={"pubkeys": ["rsa-sha2-256", "rsa-sha2-512"]},
        )
        try:
            ch = client.invoke_shell()
            time.sleep(1)
            ch.send("terminal length 0\n")
            time.sleep(0.5)
            ch.send(f"{command}\n")
            time.sleep(2)
            output = ""
            while ch.recv_ready():
                output += ch.recv(4096).decode()
        finally:
            client.close()
        return output

    @staticmethod
    def _parse(output: str) -> dict[str, str]:
        """
        Parse lines like:
            1    5254.0003.a7d5    DYNAMIC    Gi0/2
        """
        result  = {}
        pattern = re.compile(
            r"^\s*\d+\s+([0-9a-f]{4}\.[0-9a-f]{4}\.[0-9a-f]{4})\s+\S+\s+(\S+)",
            re.IGNORECASE,
        )
        for line in output.splitlines():
            m = pattern.match(line)
            if m:
                result[m.group(1).lower()] = m.group(2)

        log.info("Parsed %d MAC entries", len(result))
        return result