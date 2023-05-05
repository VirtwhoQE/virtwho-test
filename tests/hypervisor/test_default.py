"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
"""
import pytest

from virtwho import REGISTER
from virtwho import HYPERVISOR

from virtwho.base import hostname_get
from virtwho.configure import hypervisor_create


@pytest.mark.usefixtures('function_virtwho_d_conf_clean')
@pytest.mark.usefixtures('class_debug_true')
@pytest.mark.usefixtures('class_globalconf_clean')
class TestHypervisorPositive:
    @pytest.mark.tier1
    def test_guest_attr_by_curl(self, virtwho, function_hypervisor, hypervisor_data, register_data,
                                rhsm, satellite, ssh_host, function_guest_register):
        """
        :title: virt-who: hypervisor : check the guest address by curl
        :id: d9dd2559-4650-4ae0-8ebb-f8e296d3920a
            1. Config the virt-who config file, run virt-who service
            2. check guest attributes by curl

        :expectedresults:
            1. Succeed to run the virt-who service, no error messages in the rhsm.log file
            2. Succeed to find the guest uuid in from the output of the curl command
        """
        host_name = hypervisor_data['hypervisor_hostname']
        guest_uuid = hypervisor_data['guest_uuid']
        guest_hostname = hypervisor_data['guest_hostname']
        result = virtwho.run_service()
        assert (result['error'] == 0
                and result['send'] == 1
                and result['thread'] == 1)

        if REGISTER == 'rhsm':
            registered_id = rhsm.uuid(host_name)
            cmd = f"curl -s -k -u " \
                f"{register_data['username']}:{register_data['password']} " \
                f"https://{register_data['server']}/subscription/" \
                f"consumers/{registered_id}/guestids/{guest_uuid}"
            ret, output = ssh_host.runcmd(cmd)
            assert (guest_uuid in output
                    and "guestId" in output
                    and "attributes" in output)
        else:
            guest_registered_id = satellite.host_id(guest_hostname)
            cmd = f"curl -X GET -s -k -u " \
                f"{register_data['username']}:{register_data['password']} " \
                f"https://{register_data['server']}/api/v2/hosts/{guest_registered_id}"
            ret, output = ssh_host.runcmd(cmd)
            attr1 = f'"id":{guest_registered_id}'
            assert (attr1 in output
                    and guest_hostname in output)

    @pytest.mark.tier1
    def test_associated_info_by_rhsmlog_and_webui(
            self, virtwho, function_hypervisor, hypervisor_data, rhsm, satellite):
        """
        :title: virt-who: hypervisor: check associated info by rhsm.log and webui
        :id: cc0fd665-7154-4efa-ad71-b509b4224e22
            1. Config the virt-who config file, run virt-who service
            2. check host-to-guest association in rhsm.log/Web UI

        :expectedresults:
            1. Succeed to run the virt-who service, no error messages in the rhsm.log file
            2. Succeed to find the host-to-guest association in rhsm.log/Web UI
        """
        host_name = hypervisor_data['hypervisor_hostname']
        guest_uuid = hypervisor_data['guest_uuid']
        guest_hostname = hypervisor_data['guest_hostname']

        result = virtwho.run_service()
        assert (result['error'] == 0
                and result['send'] == 1
                and result['thread'] == 1)

        # check host-to-guest association in rhsm.log
        assert guest_uuid in result['log']

        # check host-to-guest association in webui
        if REGISTER == 'rhsm':
            assert rhsm.associate(host_name, guest_uuid)
        else:
            assert satellite.associate_on_webui(host_name, guest_hostname)

    @pytest.mark.tier1
    def test_mapping_info(
            self, virtwho, function_hypervisor, hypervisor_data, rhsm, satellite, register_data):
        """
        :title: virt-who: hypervisor: test the mapping info
        :id: 745cae04-c558-4ecf-8226-54c826d97eea
            1. Run the virt-who service by cli
            2. Check the mapping info from the rhsm.log
            3. Run the virt-who service by by starting service
            4. Check the mapping info from the rhsm.log
            5. Check the hypervisor facts from the rhsm.log

        :expectedresults:
            2. The hypervisor is associated with guest in the result and for the
            specified owner
            4. The hypervisor is associated with guest in the result and for the
            specified owner
            5. The facts should have the info about type,version and socket
        """
        host_name = hypervisor_data['hypervisor_hostname']
        guest_uuid = hypervisor_data['guest_uuid']

        # check fetch and send function by virt-who cli
        result = virtwho.run_cli(debug=True, oneshot=False)
        assert (result['error'] == 0
                and result['send'] == 1
                and result['thread'] == 1
                and virtwho.associate_in_mapping(
                    result, register_data['default_org'], host_name, guest_uuid))

        # check fetch and send function by virt-who service
        result = virtwho.run_service()
        assert (result['error'] == 0
                and result['send'] == 1
                and result['thread'] == 1
                and virtwho.associate_in_mapping(
                    result, register_data['default_org'], host_name, guest_uuid))

        # check hypervisor's facts
        facts = result['mappings'][register_data['default_org']][host_name]
        assert "hypervisors_async" in result['log']
        assert ('type' in facts.keys()
                and 'version' in facts.keys()
                and 'socket' in facts.keys())

    @pytest.mark.tier1
    def test_guest_facts(
            self, virtwho, function_hypervisor, hypervisor_data, rhsm, satellite, register_data, ssh_guest):
        """
        :title: virt-who: default: test the mapping info
        :id: 09e1754d-5f3a-49c5-aebc-91d4f4a8471e
        """
        guest_uuid = hypervisor_data['guest_uuid']
        virt_type = {
            'local': 'kvm',
            'libvirt': 'kvm',
            'rhevm': 'kvm',
            'esx': 'vmware',
            'hyperv': 'hyperv',
            'xen': 'xen',
            'kubevirt': 'kvm',
            'ahv': 'nutanix_ahv'
        }
        # check virt.uuid fact by subscription-manager in guest")
        cmd = "subscription-manager facts --list | grep virt.uuid"
        _, output = ssh_guest.runcmd(cmd)
        virt_uuid = output.split(':')[1].strip()
        assert virt_uuid.lower() == guest_uuid.lower()

        # check virt.host_type fact by subscription-manager in guest
        _, virtwhat_output = ssh_guest.runcmd("virt-what")
        _, facts_output = ssh_guest.runcmd(
            "subscription-manager facts --list | grep virt.host_type")
        assert (virt_type[HYPERVISOR] in virtwhat_output
                and virt_type[HYPERVISOR] in facts_output)

        # check virt.is_guest fact by subscription-manager in guest
        cmd = "subscription-manager facts --list | grep virt.is_guest"
        _, output = ssh_guest.runcmd(cmd)
        virt_is_guest = output.split(':')[1].strip()
        assert virt_is_guest == "True"

    @pytest.mark.tier2
    def test_delete_host_hypervisor(
            self, virtwho, hypervisor_data, rhsm, satellite, register_data,
            ssh_host, sm_host, function_host_register):
        """
        :title: virt-who: default: test the mapping info after deleting the host and hypervisor
        :id: 19b84057-69a3-43bc-9b24-f39bc31ed3a8
        :caseimportance: High
        :tags: tier2
        :customerscenario: false
        :upstream: no
        :steps:

            1. Run the virt-who service to send the mapping info
            2. Delete the virt-who host from webui
            3. Run the virt-who service again to check the rhsm.log
            3. Re-register the virt-who host and re-run the virt-who service
            4. Delete the hypervisor from web UI,re-run the virt-who service
        :expectedresults:

            1. Virt-who works fine, no error messages in the rhsm.log
            3. Virt-who works fine, can send the the mappping info
            4. Virt-who Works fine, no error messages in the rhsm.log
        """
        host_name = hypervisor_data['hypervisor_hostname']
        virtwho_hostname = hostname_get(ssh_host)

        # run virt-who to send mappings
        hypervisor_create(rhsm=False)
        result = virtwho.run_service()
        assert (result['error'] == 0
                and result['send'] == 1
                and result['thread'] == 1)

        # delete virt-who host from webui
        if REGISTER == 'rhsm':
            rhsm.host_delete(virtwho_hostname)
        else:
            satellite.host_delete(virtwho_hostname)

        result = virtwho.run_service()
        error_msg = "Communication with subscription manager failed: consumer no longer exists"
        assert (result['error'] is not 0
                and result['send'] == 0
                and result['thread'] == 1
                and error_msg in result['error_msg'])

        # re-register host and run virt-who
        sm_host.unregister()
        sm_host.register()
        result = virtwho.run_service()
        assert (result['error'] == 0
                and result['send'] == 1
                and result['thread'] == 1)

        # delete hypervisor from webui
        if HYPERVISOR is not 'local':
            if REGISTER == 'rhsm':
                rhsm.host_delete(host_name)
            else:
                satellite.host_delete(host_name)
            result = virtwho.run_service()
            assert (result['error'] == 0
                    and result['send'] == 1
                    and result['thread'] == 1)
