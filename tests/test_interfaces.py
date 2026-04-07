from pyats.aetest import Testcase, test, setup, cleanup


class TestInterfaces(Testcase):

    @setup
    def connect(self, testbed, device_name):
        self.device = testbed.devices[device_name]
        self.device.connect(via='netconf')

    @test
    def verify_interfaces_up(self):
        output = self.device.parse('show interfaces')
        failed = []
        for intf, data in output.items():
            if intf.startswith('MgmtEth') or intf.startswith('Loopback'):
                continue
            if data.get('oper_status') != 'up':
                failed.append(intf)
        assert not failed, f"Interfaces down: {failed}"

    @test
    def verify_no_input_errors(self):
        output = self.device.parse('show interfaces')
        failed = []
        for intf, data in output.items():
            errors = data.get('counters', {}).get('in_errors', 0)
            if errors > 0:
                failed.append(f"{intf}: {errors} input errors")
        assert not failed, f"Input errors found: {failed}"

    @test
    def verify_no_output_errors(self):
        output = self.device.parse('show interfaces')
        failed = []
        for intf, data in output.items():
            errors = data.get('counters', {}).get('out_errors', 0)
            if errors > 0:
                failed.append(f"{intf}: {errors} output errors")
        assert not failed, f"Output errors found: {failed}"

    @cleanup
    def disconnect(self):
        self.device.disconnect()
