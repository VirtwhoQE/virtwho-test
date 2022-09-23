"""Test cases Global fields

:casecomponent: virt-who
:testtype: nonfunctional
:caseautomation: Automated
"""

from virtwho.settings import config
from virtwho.provision.virtwho_hypervisor import hypervisor_state


class TestHypervisorsState:
    def test_state_esx(self):
        """Test the esx state"""
        hypervisor_state(mode='esx')
        assert config.esx.state == 'GOOD'

    def test_state_hyperv(self):
        """Test the hyperv state"""
        hypervisor_state(mode='hyperv')
        assert config.hyperv.state == 'GOOD'

    def test_state_kubevirt(self):
        """Test the kubevirt state"""
        assert config.kubevirt.state == 'GOOD'

    def test_state_ahv(self):
        """Test the ahv state"""
        assert config.ahv.state == 'GOOD'

    def test_state_libvirt(self):
        """Test the libvirt state"""
        hypervisor_state(mode='libvirt')
        assert config.libvirt.state == 'GOOD'

    def test_state_rhevm(self):
        """Test the rhevm state"""
        assert config.rhevm.state == 'GOOD'

    def test_state_xen(self):
        """Test the xen state"""
        assert config.xen.state == 'GOOD'
