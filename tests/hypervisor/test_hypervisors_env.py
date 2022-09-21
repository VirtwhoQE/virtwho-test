"""Test cases Global fields

:casecomponent: virt-who
:testtype: nonfunctional
:caseautomation: Automated
"""
from virtwho.settings import config


class TestHypervisorsEnvironment:
    def test_esx(self):
        """
        """
        assert config.hypervisors_state.esx == 'GOOD'

    def test_hyperv(self):
        """
        """
        assert config.hypervisors_state.hyperv == 'GOOD'

    def test_kubevirt(self):
        """
        """
        assert config.hypervisors_state.kubevirt == 'GOOD'

    def test_ahv(self):
        """
        """
        assert config.hypervisors_state.ahv == 'GOOD'

    def test_libvirt(self):
        """
        """
        assert config.hypervisors_state.libvirt == 'GOOD'

    def test_rhevm(self):
        """
        """
        assert config.hypervisors_state.rhevm == 'GOOD'

    def test_xen(self):
        """
        """
        assert config.hypervisors_state.xen == 'GOOD'
