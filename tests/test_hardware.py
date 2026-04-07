from pyats.aetest import Testcase, test, setup, cleanup


class TestHardware(Testcase):

    @setup
    def connect(self, testbed, device_name):
        self.device = testbed.devices[device_name]
        self.device.connect(via='netconf')

    @test
    def verify_platform_state(self):
        output = self.device.parse('show platform')
        failed = [
            card for card, data in output.get('slot', {}).items()
            if data.get('state') not in ['IOS XR RUN', 'OK']
        ]
        assert not failed, f"Platform cards not healthy: {failed}"

    @test
    def verify_cpu_utilization(self):
        output = self.device.parse('show processes cpu')
        cpu = output.get('one_min_cpu', 100)
        assert cpu < 80, f"CPU utilization too high: {cpu}%"

    @test
    def verify_memory_utilization(self):
        output = self.device.parse('show memory summary')
        for node, data in output.get('nodes', {}).items():
            free = data.get('free_application_memory', 0)
            assert free > 100000, f"Low free memory on {node}: {free}KB"

    @cleanup
    def disconnect(self):
        self.device.disconnect()
