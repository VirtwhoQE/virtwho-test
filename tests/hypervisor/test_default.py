"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
:subsystemteam: sst_subscription_virtwho
:caselevel: Component
"""

import pytest

from virtwho import REGISTER
from virtwho import HYPERVISOR
from virtwho import logger

from virtwho.base import hostname_get
from virtwho.configure import hypervisor_create


@pytest.mark.usefixtures("function_host_register_for_local_mode")
@pytest.mark.usefixtures("function_virtwho_d_conf_clean")
@pytest.mark.usefixtures("function_debug_true")
@pytest.mark.usefixtures("class_globalconf_clean")
class TestHypervisorPositive:
    @pytest.mark.tier1
    def test_guest_attr_by_curl(
        self,
        virtwho,
        function_hypervisor,
        hypervisor_data,
        register_data,
        rhsm,
        satellite,
        ssh_host,
        function_guest_register,
    ):
        """
        :title: virt-who: hypervisor : check the guest address by curl
        :id: d9dd2559-4650-4ae0-8ebb-f8e296d3920a
        :caseimportance: High
        :tags: hypervisor,default,tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. Config the virt-who config file, run virt-who service
            2. check guest attributes by curl

        :expectedresults:
            1. Succeed to run the virt-who service, no error messages in the rhsm.log file
            2. Succeed to find the guest uuid in from the output of the curl command
        """
        host_name = hypervisor_data["hypervisor_hostname"]
        guest_uuid = hypervisor_data["guest_uuid"]
        guest_hostname = hypervisor_data["guest_hostname"]
        result = virtwho.run_service()
        assert result["error"] == 0 and result["send"] == 1 and result["thread"] == 1

        if REGISTER == "rhsm":
            registered_id = rhsm.uuid(host_name)
            cmd = (
                f"curl -s -k -u "
                f"{register_data['username']}:{register_data['password']} "
                f"https://{register_data['server']}/subscription/"
                f"consumers/{registered_id}/guestids/{guest_uuid}"
            )
            ret, output = ssh_host.runcmd(cmd)
            assert (
                guest_uuid in output and "guestId" in output and "attributes" in output
            )
        else:
            guest_registered_id = satellite.host_id(guest_hostname)
            cmd = (
                f"curl -X GET -s -k -u "
                f"{register_data['username']}:{register_data['password']} "
                f"https://{register_data['server']}/api/v2/hosts/{guest_registered_id}"
            )
            ret, output = ssh_host.runcmd(cmd)
            attr1 = f'"id":{guest_registered_id}'
            assert attr1 in output and guest_hostname in output

    @pytest.mark.tier1
    @pytest.mark.satelliteSmoke
    @pytest.mark.fedoraSmoke
    @pytest.mark.fipsEnable
    @pytest.mark.gating
    def test_associated_info_by_rhsmlog_and_webui(
        self,
        virtwho,
        function_hypervisor,
        hypervisor_data,
        rhsm,
        satellite,
        register_data,
        function_guest_register,
    ):
        """
        :title: virt-who: hypervisor: check associated info by rhsm.log and webui
        :id: cc0fd665-7154-4efa-ad71-b509b4224e22
        :caseimportance: High
        :tags: hypervisor,default,tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. Config the virt-who config file, run virt-who service
            2. check host-to-guest association in rhsm.log/Web UI

        :expectedresults:
            1. Succeed to run the virt-who service, no error messages in the rhsm.log file
            2. Succeed to find the host-to-guest association in rhsm.log/Web UI
        """
        host_name = hypervisor_data["hypervisor_hostname"]
        guest_uuid = hypervisor_data["guest_uuid"]
        guest_hostname = hypervisor_data["guest_hostname"]
        default_org = register_data["default_org"]

        result = virtwho.run_service()
        assert result["error"] == 0 and result["send"] == 1 and result["thread"] == 1

        # check host-to-guest association in rhsm.log
        if HYPERVISOR != "local":
            mappings = result["mappings"]
            associated_hypervisor_in_mapping = mappings[default_org][guest_uuid][
                "guest_hypervisor"
            ]
            assert associated_hypervisor_in_mapping == host_name

        # check host-to-guest association in webui
        if REGISTER == "rhsm":
            assert rhsm.associate(host_name, guest_uuid)
        else:
            assert satellite.associate_on_webui(host_name, guest_hostname)

    @pytest.mark.tier1
    @pytest.mark.notLocal
    def test_mapping_info(
        self,
        virtwho,
        function_hypervisor,
        hypervisor_data,
        rhsm,
        satellite,
        register_data,
    ):
        """
        :title: virt-who: hypervisor: test the mapping info
        :id: 745cae04-c558-4ecf-8226-54c826d97eea
        :caseimportance: High
        :tags: hypervisor,default,tier1
        :customerscenario: false
        :upstream: no
        :steps:
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
        host_name = hypervisor_data["hypervisor_hostname"]
        guest_uuid = hypervisor_data["guest_uuid"]

        # check fetch and send function by virt-who cli
        result = virtwho.run_cli(debug=True, oneshot=False)
        assert (
            result["error"] == 0
            and result["send"] == 1
            and result["thread"] == 1
            and virtwho.associate_in_mapping(
                result, register_data["default_org"], host_name, guest_uuid
            )
        )

        # check fetch and send function by virt-who service
        result = virtwho.run_service()
        assert (
            result["error"] == 0
            and result["send"] == 1
            and result["thread"] == 1
            and virtwho.associate_in_mapping(
                result, register_data["default_org"], host_name, guest_uuid
            )
        )

        # check hypervisor's facts
        facts = result["mappings"][register_data["default_org"]][host_name]
        assert "hypervisors_async" in result["log"]
        assert (
            "type" in facts.keys()
            and "version" in facts.keys()
            and "socket" in facts.keys()
        )

    @pytest.mark.tier1
    def test_guest_facts(
        self,
        virtwho,
        function_hypervisor,
        hypervisor_data,
        rhsm,
        satellite,
        register_data,
        ssh_guest,
    ):
        """
        :title: virt-who: hypervisor: test the guest facts
        :id: 09e1754d-5f3a-49c5-aebc-91d4f4a8471e
        :caseimportance: High
        :tags: hypervisor,default,tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. Check virt.uuid fact by subscription-manager in guest
            2. Check virt.host_type fact by subscription-manager in guest
            3. Check virt.is_guest fact by subscription-manager in guest
            4. Run the virt-who service by cli -s -j with bad configuration

        :expectedresults:
            1. Succeed to check virt.uuid fact
            2. Succeed to check virt.host_type fact
            3. Succeed to check virt.is_guest fact
        """
        guest_uuid = hypervisor_data["guest_uuid"]
        virt_type = {
            "local": "kvm",
            "libvirt": "kvm",
            "rhevm": "kvm",
            "esx": "vmware",
            "hyperv": "hyperv",
            "xen": "xen",
            "kubevirt": "kvm",
            "ahv": "nutanix_ahv",
        }
        # check virt.uuid fact by subscription-manager in guest
        cmd = "subscription-manager facts --list | grep virt.uuid"
        _, output = ssh_guest.runcmd(cmd)
        virt_uuid = output.split(":")[1].strip()
        assert virt_uuid.lower() == guest_uuid.lower()

        # check virt.host_type fact by subscription-manager in guest
        _, virtwhat_output = ssh_guest.runcmd("virt-what")
        _, facts_output = ssh_guest.runcmd(
            "subscription-manager facts --list | grep virt.host_type"
        )
        assert (
            virt_type[HYPERVISOR] in virtwhat_output
            and virt_type[HYPERVISOR] in facts_output
        )

        # check virt.is_guest fact by subscription-manager in guest
        cmd = "subscription-manager facts --list | grep virt.is_guest"
        _, output = ssh_guest.runcmd(cmd)
        virt_is_guest = output.split(":")[1].strip()
        assert virt_is_guest == "True"

    @pytest.mark.tier1
    @pytest.mark.release(rhel8=False, rhel9=True, rhel10=True)
    @pytest.mark.notLocal
    def test_virtwho_status(
        self,
        virtwho,
        function_hypervisor,
        hypervisor_data,
        register_data,
        function_debug_false,
    ):
        """
        :title: virt-who: hypervisor: test the virtwho status
        :id: 1608c965-c7f5-427b-b45e-c767600cdbf4
        :caseimportance: High
        :tags: hypervisor,default,tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. Run the virt-who service by cli -do to report the mapping
            2. Run the virt-who service by cli -s with good configuration
            3. Run the virt-who service by cli -s -j with good configuration
            4. Run the virt-who service by cli -s -j with bad configuration

        :expectedresults:
            1. Succeed to send the mapping
            2. Succeed to find the success status
            3. Succeed to print the json status info
            4. Succeed to find the failure status
        """
        # Run virt-who to report the mapping
        result = virtwho.run_cli()
        assert result["error"] == 0 and result["send"] == 1 and result["thread"] == 0

        # Check '#virt-who --status' with good configuration
        result = virtwho.run_cli(oneshot=False, debug=False, status=True)
        assert (
            "success" in result[function_hypervisor.section]["source_status"]
            and "success" in result[function_hypervisor.section]["destination_status"]
        )

        # Check #virt-who --status --json
        result = virtwho.run_cli(oneshot=False, debug=False, status=True, jsn=True)
        if "libvirt" in HYPERVISOR:
            source_connection = f"qemu+ssh://root@{hypervisor_data['hypervisor_server']}/system?no_tty=1"
        elif "esx" in HYPERVISOR:
            source_connection = f"https://{hypervisor_data['hypervisor_server']}"
        elif "rhevm" in HYPERVISOR:
            source_connection = (
                hypervisor_data["hypervisor_server"].split("ovirt-engine")[0].strip()
            )
        else:
            source_connection = hypervisor_data["hypervisor_server"]
        source = result[function_hypervisor.section]["source"]
        destination = result[function_hypervisor.section]["destination"]
        assert (
            source["connection"] == source_connection
            and source["status"] == "success"
            and source["last_successful_retrieve"].split(" ")[2] == "UTC"
            and source["hypervisors"] >= 1
            and source["guests"] >= 1
            and destination["connection"] == register_data["server"]
            and destination["status"] == "success"
            and destination["last_successful_send"].split(" ")[2] == "UTC"
            and destination["last_successful_send_job_status"] == "FINISHED"
        )

        # Check '#virt-who --status --json' with bad configuration
        option = "password"
        if "kubevirt" in HYPERVISOR:
            option = "kubeconfig"
        if "libvirt" in HYPERVISOR:
            option = "server"
        function_hypervisor.update(option, "xxx")
        function_hypervisor.update("owner", "xxx")
        result = virtwho.run_cli(oneshot=False, debug=False, status=True, jsn=True)
        if HYPERVISOR == "ahv":
            logger.info("=== AHV: failed with bz2177721 ===")
        assert (
            result[function_hypervisor.section]["source"]["status"] == "failure"
            and result[function_hypervisor.section]["destination"]["status"]
            == "failure"
        )

    @pytest.mark.tier2
    def test_delete_host_hypervisor(
        self,
        virtwho,
        hypervisor_data,
        rhsm,
        satellite,
        register_data,
        ssh_host,
        sm_host,
        function_host_register,
    ):
        """
        :title: virt-who: hypervisor: test the mapping info after deleting the host and hypervisor
        :id: 19b84057-69a3-43bc-9b24-f39bc31ed3a8
        :caseimportance: High
        :tags: hypervisor,default,tier2
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
        host_name = hypervisor_data["hypervisor_hostname"]
        virtwho_hostname = hostname_get(ssh_host)

        # run virt-who to send mappings
        hypervisor_create(rhsm=False)
        result = virtwho.run_service()
        assert result["error"] == 0 and result["send"] == 1 and result["thread"] == 1

        # delete virt-who host from webui
        if REGISTER == "rhsm":
            rhsm.host_delete(virtwho_hostname)
        else:
            satellite.host_delete(virtwho_hostname)

        result = virtwho.run_service()
        error_msg = (
            "Communication with subscription manager failed: consumer no longer exists"
        )
        assert (
            result["error"] is not 0
            and result["send"] == 0
            and result["thread"] == 1
            and error_msg in result["log"]
        )

        # re-register host and run virt-who
        sm_host.unregister()
        sm_host.register()
        result = virtwho.run_service()
        assert result["error"] == 0 and result["send"] == 1 and result["thread"] == 1

        # delete hypervisor from webui
        if HYPERVISOR != "local":
            if REGISTER == "rhsm":
                rhsm.host_delete(host_name)
            else:
                satellite.host_delete(host_name)
            result = virtwho.run_service()
            assert (
                result["error"] == 0 and result["send"] == 1 and result["thread"] == 1
            )
