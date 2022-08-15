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
        assert config.hypervisors_status.esx == 'GOOD'

    def test_hyperv(self):
        """
        """
        assert config.hypervisors_status.hyperv == 'GOOD'

    def test_kubevirt(self):
        """
        """
        assert config.hypervisors_status.kubevirt == 'GOOD'

    def test_ahv(self):
        """
        """
        assert config.hypervisors_status.ahv == 'GOOD'

    def test_libvirt(self):
        """
        """
        assert config.hypervisors_status.libvirt == 'GOOD'

    def test_rhevm(self):
        """
        """
        assert config.hypervisors_status.rhevm == 'GOOD'

    def test_xen(self):
        """
        """
        assert config.hypervisors_status.xen == 'GOOD'
