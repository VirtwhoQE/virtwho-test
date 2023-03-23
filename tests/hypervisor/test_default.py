"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
"""
import pytest

from virtwho import REGISTER


@pytest.mark.usefixtures('function_virtwho_d_conf_clean')
@pytest.mark.usefixtures('debug_true')
@pytest.mark.usefixtures('globalconf_clean')
class TestLibvrtPositive:
    @pytest.mark.tier1
    def test_guest_attr_by_curl(self, virtwho, function_hypervisor, hypervisor_data,
                                      register_data, rhsm, satellite, register_guest, ssh_host):
        """
        :title: virt-who: all_hypervisors : check the guest attress by curl
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
        :title: virt-who: libvirt: check associated info by rhsm.log and webui
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
