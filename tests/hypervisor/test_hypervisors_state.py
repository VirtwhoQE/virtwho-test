"""Test cases Global fields

:casecomponent: virt-who
:testtype: nonfunctional
:caseautomation: Automated
:subsystemteam: sst_subscription_virtwho
:caselevel: Component
"""

from virtwho.provision.virtwho_hypervisor import hyperv_monitor
from virtwho.provision.virtwho_hypervisor import esx_monitor
from virtwho.provision.virtwho_hypervisor import kubevirt_monitor
from virtwho.provision.virtwho_hypervisor import libvirt_monitor
from virtwho.provision.virtwho_hypervisor import ahv_monitor
from virtwho.provision.virtwho_hypervisor import rhevm_monitor
from virtwho.provision.virtwho_hypervisor import xen_monitor


class TestHypervisorsState:
    """The test cases for hypervisor-monitor"""

    def test_state_esx(self):
        """Test the esx state"""
        assert esx_monitor() == "GOOD"

    def test_state_hyperv(self):
        """Test the hyperv state"""
        assert hyperv_monitor() == "GOOD"

    def test_state_kubevirt(self):
        """Test the kubevirt state"""
        assert kubevirt_monitor() == "GOOD"

    def test_state_ahv(self):
        """Test the ahv state"""
        assert ahv_monitor() == "GOOD"

    def test_state_libvirt(self):
        """Test the libvirt state"""
        assert libvirt_monitor() == "GOOD"

    def test_state_rhevm(self):
        """Test the rhevm state"""
        assert rhevm_monitor() == "GOOD"

    def test_state_xen(self):
        """Test the xen state"""
        assert xen_monitor() == "GOOD"
