from pyats.aetest import Testcase, test, setup, cleanup


class TestRouting(Testcase):

    @setup
    def connect(self, testbed, device_name):
        self.device = testbed.devices[device_name]
        self.device.connect(via='netconf')

    @test
    def verify_isis_adjacencies(self):
        output = self.device.parse('show isis neighbors')
        neighbors = output.get('isis', {}).get('CORE', {}).get('neighbors', {})
        assert neighbors, f"No IS-IS adjacencies found on {self.device.name}"
        failed = [
            nbr for nbr, data in neighbors.items()
            if data.get('state') != 'Up'
        ]
        assert not failed, f"IS-IS neighbors not Up: {failed}"

    @test
    def verify_isis_level2_only(self):
        output = self.device.parse('show isis neighbors')
        neighbors = output.get('isis', {}).get('CORE', {}).get('neighbors', {})
        failed = [
            nbr for nbr, data in neighbors.items()
            if data.get('circuit_type') != 'L2'
        ]
        assert not failed, f"Non-L2 IS-IS adjacencies found: {failed}"

    @test
    def verify_loopbacks_in_rib(self):
        output = self.device.parse('show route ipv4')
        routes = output.get('vrf', {}).get('default', {}).get('address_family', {}) \
                       .get('ipv4', {}).get('routes', {})
        expected_loopbacks = [
            '10.0.0.1/32', '10.0.0.2/32', '10.0.0.3/32', '10.0.0.4/32',
            '10.0.0.5/32', '10.0.0.6/32', '10.0.0.7/32', '10.0.0.8/32',
            '10.0.0.11/32', '10.0.0.12/32', '10.0.0.13/32', '10.0.0.14/32'
        ]
        missing = [r for r in expected_loopbacks if r not in routes]
        assert not missing, f"Missing loopbacks in RIB: {missing}"

    @cleanup
    def disconnect(self):
        self.device.disconnect()
