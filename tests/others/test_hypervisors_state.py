"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
:subsystemteam: rhel-sst-csi-client-tools
:caselevel: Component
"""

# All the test cases have been uploaded to Polarion with Inactive status
# because the cases are just used to test the test environments.

import pytest

from virtwho.provision.virtwho_hypervisor import hyperv_monitor
from virtwho.provision.virtwho_hypervisor import esx_monitor
from virtwho.provision.virtwho_hypervisor import kubevirt_monitor
from virtwho.provision.virtwho_hypervisor import libvirt_monitor
from virtwho.provision.virtwho_hypervisor import ahv_monitor
from virtwho.provision.virtwho_hypervisor import rhevm_monitor


class TestHypervisorsState:
    """The test cases for hypervisor-monitor"""

    def test_state_esx(self):
        """Test the ESX hypervisor environment state

        :title: virt-who: hypervisor-monitor: verify ESX hypervisor state
        :id: 620648be-ca19-4709-9989-ecb45fcdcb0d
        :caseimportance: High
        :tags: others,hypervisor-monitor,tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. Verify the vCenter server is reachable
            2. Verify the ESXi host is reachable
            3. Verify the Windows PowerCLI client is reachable
            4. Query the hypervisor for guest VM data (UUID, hostname, etc.)
            5. Verify the RHEL guest VM is running and SSH-accessible
            6. Update virtwho.ini with discovered environment data
        :expectedresults:
            1. vCenter server responds to ping
            2. ESXi host responds to ping
            3. Windows client responds to ping
            4. Guest VM data is retrieved successfully
            5. Guest VM is in a running state and reachable via SSH
            6. Configuration is updated; overall state is GOOD
        """
        assert esx_monitor() == "GOOD"

    def test_state_hyperv(self):
        """Test the Hyper-V hypervisor environment state

        :title: virt-who: hypervisor-monitor: verify Hyper-V hypervisor state
        :id: fa3bc4f0-4a01-4b20-9e54-dd8a5e73d323
        :caseimportance: High
        :tags: others,hypervisor-monitor,tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. Verify the Hyper-V server is reachable
            2. Query the hypervisor for guest VM data (UUID, hostname, etc.)
            3. Verify the RHEL guest VM is running and SSH-accessible
            4. Update virtwho.ini with discovered environment data
        :expectedresults:
            1. Hyper-V server responds to ping
            2. Guest VM data is retrieved successfully
            3. Guest VM is in a running state and reachable via SSH
            4. Configuration is updated; overall state is GOOD
        """
        assert hyperv_monitor() == "GOOD"

    def test_state_kubevirt(self):
        """Test the KubeVirt hypervisor environment state

        :title: virt-who: hypervisor-monitor: verify KubeVirt hypervisor state
        :id: 6e9e6b3a-cc77-4c6f-82c5-ff0130560487
        :caseimportance: High
        :tags: others,hypervisor-monitor,tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. Verify the KubeVirt API endpoint host is reachable
            2. Query the KubeVirt API for guest VM data (UUID, hostname, etc.)
            3. Verify the RHEL guest VM is SSH-accessible
            4. Update virtwho.ini with discovered environment data
        :expectedresults:
            1. KubeVirt API host responds to ping
            2. Guest VM data is retrieved via API
            3. Guest VM is reachable via SSH
            4. Configuration is updated; overall state is GOOD
        """
        assert kubevirt_monitor() == "GOOD"

    def test_state_ahv(self):
        """Test the AHV (Nutanix) hypervisor environment state

        :title: virt-who: hypervisor-monitor: verify AHV hypervisor state
        :id: fc9173c0-e709-4a02-b4e3-d6a2033c75af
        :caseimportance: High
        :tags: others,hypervisor-monitor,tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. Verify the Nutanix/AHV server is reachable
            2. Query the AHV API for guest VM data (UUID, hostname, cluster, etc.)
            3. Verify the RHEL guest VM is running and SSH-accessible
            4. Update virtwho.ini with discovered environment data
        :expectedresults:
            1. Nutanix server responds to ping
            2. Guest VM data is retrieved via API
            3. Guest VM is reachable via SSH
            4. Configuration is updated; overall state is GOOD
        """
        assert ahv_monitor() == "GOOD"

    def test_state_libvirt(self):
        """Test the libvirt hypervisor environment state

        :title: virt-who: hypervisor-monitor: verify libvirt hypervisor state
        :id: 59759aa7-1663-4229-ac9b-3604d15d9c34
        :caseimportance: High
        :tags: others,hypervisor-monitor,tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. Verify the libvirt host is reachable
            2. Query the hypervisor for guest VM data (UUID, hostname, etc.)
            3. Verify the RHEL guest VM exists and is SSH-accessible
            4. Update virtwho.ini with discovered environment data
        :expectedresults:
            1. Libvirt host responds to ping
            2. Guest VM data is retrieved successfully
            3. Guest VM is reachable via SSH
            4. Configuration is updated; overall state is GOOD
        """
        assert libvirt_monitor() == "GOOD"

    @pytest.mark.skip(
        reason="RHEVM monitor not implemented — rhevm_monitor() returns SKIP"
    )
    def test_state_rhevm(self):
        """Test the RHEVM hypervisor environment state

        :title: virt-who: hypervisor-monitor: verify RHEVM hypervisor state
        :id: 9d5c4db0-01fa-465a-a477-0026c6212660
        :caseimportance: High
        :tags: others,hypervisor-monitor,tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. Verify the RHEVM server is reachable
            2. Query the hypervisor for guest VM data
            3. Verify the RHEL guest VM is running and SSH-accessible
            4. Update virtwho.ini with discovered environment data
        :expectedresults:
            1. RHEVM server responds to ping
            2. Guest VM data is retrieved successfully
            3. Guest VM is reachable via SSH
            4. Configuration is updated; overall state is GOOD
        """
        assert rhevm_monitor() == "GOOD"
