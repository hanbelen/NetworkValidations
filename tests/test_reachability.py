from pyats.aetest import Testcase, test, setup, cleanup


LOOPBACKS = {
    'SYD-P1':  '10.0.0.1',
    'SYD-P2':  '10.0.0.2',
    'SYD-PE1': '10.0.0.3',
    'SYD-PE2': '10.0.0.4',
    'SYD-RR1': '10.0.0.5',
    'SYD-RR2': '10.0.0.6',
    'SYD-TR1': '10.0.0.7',
    'SYD-TR2': '10.0.0.8',
    'MEL-PE1': '10.0.0.11',
    'MEL-PE2': '10.0.0.12',
    'MEL-TR1': '10.0.0.13',
    'MEL-TR2': '10.0.0.14',
}


class TestReachability(Testcase):

    @setup
    def connect(self, testbed, device_name):
        self.device = testbed.devices[device_name]
        self.device.connect(via='netconf')

    @test
    def verify_loopback_reachability(self):
        failed = []
        for target_device, target_ip in LOOPBACKS.items():
            if target_device == self.device.name:
                continue
            result = self.device.execute(
                f'ping {target_ip} source Loopback0 count 5'
            )
            if '!!!!!'.count('!') < 3:
                failed.append(f"{self.device.name} -> {target_device} ({target_ip})")
        assert not failed, f"Reachability failures: {failed}"

    @cleanup
    def disconnect(self):
        self.device.disconnect()
