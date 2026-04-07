from pyats.aetest import Testcase, test, setup, cleanup


class TestMpls(Testcase):

    @setup
    def connect(self, testbed, device_name):
        self.device = testbed.devices[device_name]
        self.device.connect(via='netconf')

    @test
    def verify_ldp_sessions(self):
        output = self.device.parse('show mpls ldp neighbor')
        neighbors = output.get('vrf', {}).get('default', {}).get('neighbors', {})
        assert neighbors, f"No LDP neighbors on {self.device.name}"
        failed = [
            nbr for nbr, data in neighbors.items()
            if data.get('state') != 'Oper'
        ]
        assert not failed, f"LDP sessions not operational: {failed}"

    @test
    def verify_rsvp_sessions(self):
        if self.device.name.startswith(('RR', 'TR')):
            self.skipped('RSVP-TE not applicable for RR/TR routers')
        output = self.device.parse('show rsvp session')
        sessions = output.get('rsvp', {}).get('sessions', {})
        assert sessions, f"No RSVP sessions on {self.device.name}"

    @test
    def verify_te_tunnels_up(self):
        if 'PE' not in self.device.name:
            self.skipped('TE tunnels only on PE routers')
        output = self.device.parse('show mpls traffic-eng tunnels')
        tunnels = output.get('tunnel', {})
        failed = [
            t for t, data in tunnels.items()
            if data.get('lsp_state') != 'established'
        ]
        assert not failed, f"TE tunnels not established: {failed}"

    @test
    def verify_l2vpn_xconnects(self):
        if 'PE' not in self.device.name:
            self.skipped('L2VPN xconnects only on PE routers')
        output = self.device.parse('show l2vpn xconnect')
        xconnects = output.get('groups', {})
        failed = [
            xc for grp in xconnects.values()
            for xc, data in grp.items()
            if data.get('state') != 'UP'
        ]
        assert not failed, f"L2VPN xconnects not UP: {failed}"

    @cleanup
    def disconnect(self):
        self.device.disconnect()
