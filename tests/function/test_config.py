"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
"""
import pytest

from virtwho import HYPERVISOR
from virtwho import HYPERVISOR_FILE
from virtwho import REGISTER

from virtwho.base import hostname_get


@pytest.mark.usefixtures('globalconf_clean')
@pytest.mark.usefixtures('hypervisor')
class TestConfiguration:
    @pytest.mark.tier1
    def test_debug_in_virtwho_conf(self, virtwho, globalconf):
        """Test the debug option in /etc/virtwho.conf

        :title: virt-who: config: test debug option
        :id: 6f238133-43db-4a52-b01c-441faba0cf74
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. Run virt-who with "debug=True" in [global] section in /etc/virt-who.conf file
            2. Run virt-who with "debug=False" in [global] section in /etc/virt-who.conf file

        :expectedresults:

            1. no [DEBUG] log printed
            2. [DEBUG] logs are printed with the configuration
        """
        globalconf.update('global', 'debug', 'True')
        result = virtwho.run_service()
        assert (result['send'] == 1
                and result['error'] == 0
                and result['debug'] is True)

        globalconf.update('global', 'debug', 'False')
        result = virtwho.run_service()
        assert (result['send'] == 1
                and result['error'] == 0
                and result['debug'] is False)

    @pytest.mark.tier1
    def test_interval_in_virtwho_conf(self, virtwho, globalconf):
        """Test the interval option in /etc/virtwho.conf

        :title: virt-who: config: test interval option
        :id: f1d39429-62c0-44f0-a6d3-4ffc8dc704b1
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. Enable interval and set to 10 in /etc/virt-who.conf
            2. Enable interval and set to 60 in /etc/virt-who.conf
            3. Enable interval and set to 120 in /etc/virt-who.conf
        :expectedresults:

            1. Default value of 3600 seconds will be used when configure lower than 60 seconds
            2. Configure successfully, and virt-who starting infinite loop with 60 seconds interval
            3. Configure successfully, and virt-who starting infinite loop with 120 seconds interval
        """
        globalconf.update('global', 'debug', 'True')
        globalconf.update('global', 'interval', '10')
        result = virtwho.run_service()
        assert (result['send'] == 1
                and result['error'] == 0
                and result['interval'] == 3600)

        globalconf.update('global', 'interval', '60')
        result = virtwho.run_service(wait=60)
        assert (result['send'] == 1
                and result['error'] == 0
                and result['loop'] == 60)

    @pytest.mark.tier1
    def test_oneshot_in_virtwho_conf(self, virtwho, globalconf):
        """Test the oneshot option in /etc/virtwho.conf

        :title: virt-who: config: test oneshot option
        :id: 9e39f91f-80b5-4773-bef0-7facf8cb85e2
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. Run virt-who with "oneshot=True" in /etc/virt-who.conf
            2. Run virt-who with "oneshot=False" in /etc/virt-who.conf file

        :expectedresults:

            1. Can see 'Thread X stopped after running once' log in rhsm.log
            2. Cannot see 'Thread X stopped after running once' log in rhsm.log
        """
        globalconf.update('global', 'debug', 'True')
        globalconf.update('global', 'oneshot', 'True')
        result = virtwho.run_service()
        assert (result['send'] == 1
                and result['error'] == 0
                and result['terminate'] == 1
                and result['oneshot'] is True)

        globalconf.update('global', 'oneshot', 'False')
        result = virtwho.run_service()
        assert (result['send'] == 1
                and result['error'] == 0
                and result['terminate'] == 0
                and result['oneshot'] is False)

    @pytest.mark.tier1
    def test_print_in_virtwho_conf(self, virtwho, globalconf, hypervisor_data):
        """Test the print_ option in /etc/virtwho.conf

        :title: virt-who: config: test print_ option
        :id: 25de8130-677f-43ca-b07d-a15f49e91205
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. Run virt-who with "print_=True" in /etc/virt-who.conf
            2. Run virt-who with "print_=False" in /etc/virt-who.conf

        :expectedresults:

            1. the mappings send number and alive thread number of the virt-who is 0
            2. the mappings send number and alive thread number of the virt-who is 1
        """
        globalconf.update('global', 'print_', 'False')
        result = virtwho.run_service()
        assert (result['error'] == 0
                and result['send'] == 1
                and result['thread'] == 1)

        guest_id = hypervisor_data['guest_uuid']
        globalconf.update('global', 'print_', 'True')
        globalconf.update('global', 'debug', 'True')
        result = virtwho.run_service()
        assert (result['error'] == 0
                and result['send'] == 0
                and result['thread'] == 0
                and result['debug'] is True
                and guest_id in result['log'])

        globalconf.update('global', 'print_', 'True')
        globalconf.update('global', 'debug', 'False')
        result = virtwho.run_service()
        assert (result['error'] == 0
                and result['send'] == 0
                and result['thread'] == 0
                and result['debug'] is False
                and guest_id not in result['log'])

    @pytest.mark.tier1
    def test_reporter_id_in_virtwho_conf(self, virtwho, globalconf, ssh_host, hypervisor_data):
        """Test the reporter_id option in /etc/virtwho.conf

        :title: virt-who: config: test reporter_id option
        :id: 83df76e6-27c6-4429-b32b-fbc2be0564a4
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. run virt-who to with default configured
            2. update the reporter_id in /etc/virtwho.conf file and run virt-who

        :expectedresults:

            1. the hostname of the virt-who host shout be included in default reporter_id
            2. the reporter_id should be updated to the setting reporter_id
        """
        virtwho_hostname = hostname_get(ssh_host)
        globalconf.update('global', 'debug', 'True')
        result = virtwho.run_service()
        assert (result['error'] == 0
                and result['send'] == 1
                and result['thread'] == 1
                and virtwho_hostname in result['reporter_id'])
        reporter_id = "virtwho_reporter_id"
        globalconf.update('global', 'reporter_id', reporter_id)
        result = virtwho.run_service()
        assert (result['error'] == 0
                and result['send'] == 1
                and result['thread'] == 1
                and result['reporter_id'] == reporter_id)

    @pytest.mark.tier1
    def test_log_per_config_in_virtwho_conf(self, virtwho, globalconf, hypervisor_data, ssh_host):
        """Test the log_per_config option in /etc/virtwho.conf

        :title: virt-who: config: test log_per_config option
        :id: 85accd49-54dc-4899-a9cf-c6fb07b2fe3c
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. Run virt-who with log-per-config=False in /etc/virt-who.conf
            2. Run virt-who with log-per-config=True in /etc/virt-who.conf

        :expectedresults:

            1. unexpected /var/log/rhsm/virtwho* files not exist
            2. Succeeded to find virtwho.destination_-*.log, virtwho.main.log, virtwho.main.log and
            virtwho.rhsm_log.log file in /var/log/rhsm/
        """
        guest_uuid = hypervisor_data['guest_uuid']
        globalconf.update('global', 'debug', 'True')

        globalconf.update('global', 'log_per_config', 'False')
        result = virtwho.run_service()
        assert (result['error'] == 0
                and result['send'] == 1
                and result['thread'] == 1)
        ret, _ = ssh_host.runcmd('ls /var/log/rhsm/virtwho*')
        assert ret is not 0

        globalconf.update('global', 'log_per_config', 'True')
        result = virtwho.run_service()
        assert (result['error'] == 0
                and result['send'] == 1
                and result['thread'] == 1)
        ret, files = ssh_host.runcmd('ls /var/log/rhsm/virtwho*')
        assert (ret == 0
                and 'virtwho.destination' in files
                and 'virtwho.main.log' in files
                and 'virtwho.rhsm_log.log' in files
                and 'virtwho.virt.log' in files)

        # assert the contents for the log files
        for filename in files.strip().split('\n'):
            _, file_content = ssh_host.runcmd(f"cat {filename.strip()}")
            if 'virtwho.destination' in filename:
                assert ('ERROR' not in file_content
                        and guest_uuid in file_content
                        and 'virtwho.destination' in file_content
                        and 'virtwho.rhsm_log' not in file_content
                        and 'virtwho.main' not in file_content)
            if 'virtwho.main.log' in filename:
                assert ('ERROR' not in file_content
                        and 'Report for config' in file_content
                        and 'virtwho.main' in file_content
                        and 'virtwho.destination' not in file_content
                        and 'virtwho.rhsm_log' not in file_content)
            if 'virtwho.rhsm_log.log' in filename:
                assert ('ERROR' not in file_content
                        and "Using reporter_id=" in file_content
                        and 'virtwho.rhsm_log' in file_content
                        and 'virtwho.destination' not in file_content
                        and 'virtwho.main' not in file_content)

    @pytest.mark.tier1
    def test_log_dir_and_log_file_in_virtwho_conf(self, virtwho, globalconf, hypervisor_data, ssh_host):
        """Test the log_dir and log_file option in /etc/virtwho.conf

        :title: virt-who: config: test log_dir and log_file option
        :id: b20c8bf6-25f1-485a-a659-2f4194ee7fcc
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. Run virt-who with log_dir setting in /etc/virt-who.conf
            2. Run virt-who with log_dir and log_file setting in /etc/virt-who.conf

        :expectedresults:

            1. Succeeded to find the default rhsm.log file in specific log dir
            2. Succeeded to find the specific log file in specific log dir
        """
        log_dir = '/var/log/rhsm/virtwho/'
        default_log_file = '/var/log/rhsm/virtwho/rhsm.log'
        specific_log_file = '/var/log/rhsm/virtwho/virtwho.log'
        guest_uuid = hypervisor_data['guest_uuid']
        globalconf.update('global', 'debug', 'True')

        globalconf.update('global', 'log_dir', log_dir)
        result = virtwho.run_service()
        assert (result['error'] == 0
                and result['send'] == 1
                and result['thread'] == 1)
        result, _ = ssh_host.runcmd(f'ls {default_log_file}')
        assert result == 0
        _, content = ssh_host.runcmd(f'cat {default_log_file}')
        assert (guest_uuid in content
                and 'ERROR' not in content)

        globalconf.update('global', 'log_file', specific_log_file)
        result = virtwho.run_service()
        assert (result['error'] == 0
                and result['send'] == 1
                and result['thread'] == 1)
        result, _ = ssh_host.runcmd(f'ls {specific_log_file}')
        assert result == 0
        result, contents = ssh_host.runcmd(f'cat {specific_log_file}')
        assert (guest_uuid in contents
                and 'ERROR' not in contents)

    @pytest.mark.tier1
    def test_configs_in_virtwho_conf(self, virtwho, globalconf, hypervisor_data, ssh_host):
        """Test the configs option in /etc/virtwho.conf

        :title: virt-who: config: test configs option
        :id: 03db48c3-4a98-4956-bd6f-a8ac4da7da8e
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. Run virt-who configs setting in /etc/virt-who.conf

        :expectedresults:

            1. Succeeded to run the virt-who and ignore the configurations files in
            /etc/virt-who.d/ dir
        """
        config_file = '/tmp/test_config_configs.conf'
        guest_uuid = hypervisor_data['guest_uuid']
        globalconf.update('global', 'debug', 'True')
        ssh_host.runcmd(f'\\cp -f {HYPERVISOR_FILE} {config_file}')

        globalconf.update('global', 'configs', config_file)
        result = virtwho.run_service()
        msg = "ignoring configuration files in '/etc/virt-who.d/'"
        assert (result['error'] == 0
                and result['send'] == 1
                and result['thread'] == 1
                and guest_uuid in result['log']
                and msg in result['log'])

    @pytest.mark.tier1
    def test_owner_in_virtwho_conf(self, virtwho, globalconf, hypervisor, hypervisor_data,
                                   owner_data, debug_true):
        """Test the owner option in /etc/virtwho.conf

        :title: virt-who: config: test owner option
        :id: ce219d82-cf66-4019-af17-3197c53c72a0
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. Run virt-who with incorrect owner setting in [defaults] section
            in /etc/virt-who.conf
            2. Run virt-who with the correct owner setting in [defaults] section
            in /etc/virt-who.conf

        :expectedresults:

            1. Virt-who runs failed with the incorrect owner setting
            2. Succeeded to run the virt-who with correct owner setting
        """
        guest_uuid = hypervisor_data['guest_uuid']
        globalconf.update('global', 'debug', 'True')
        hypervisor.delete('owner')

        globalconf.update('defaults', 'owner', owner_data['bad_owner'])
        result = virtwho.run_service()
        assert (result['error'] is not 0
                and result['send'] == 0
                and result['thread'] == 1
                and any(error in result['error_msg'] for error in owner_data['error']))

        globalconf.update('defaults', 'owner', owner_data['owner'])
        result = virtwho.run_service()
        assert (result['error'] == 0
                and result['send'] == 1
                and result['thread'] == 1
                and guest_uuid in result['log'])

    @pytest.mark.tier1
    def test_hypervisor_id_in_virtwho_conf(self, virtwho, globalconf, hypervisor, hypervisor_data,
                                           register_data, rhsm, satellite):
        """Test the hypervisor_id option in /etc/virtwho.conf

        :title: virt-who: config: test hypervisor_id option
        :id: fed463a6-9538-4242-9990-2e4995d1f473
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. Run virt-who with hypervisor_id=hostname in /etc/virt-who.conf
            2. Run virt-who with hypervisor_id=uuid in /etc/virt-who.conf
            3. Run virt-who with hypervisor_id=hwuuid in /etc/virt-who.conf

        :expectedresults:

            1. Succeeded to run the virt-who, the hypervisor_id in mapping info should be hostname
            2. Succeeded to run the virt-who, the hypervisor_id in mapping info should be uuid
            3. Succeeded to run the virt-who, the hypervisor_id in mapping info should be hwuuid
        """
        globalconf.update('global', 'debug', 'True')
        # we default have the hypervisor_id section in the config file in /etc/virt-who.d/
        hypervisor.delete('hypervisor_id')

        hypervisor_ids = ['hostname', 'uuid']
        # only esx and rhevm modes support hwuuid
        if HYPERVISOR in ['esx', 'rhevm']:
            hypervisor_ids.append('hwuuid')
        for hypervisor_id in hypervisor_ids:
            globalconf.update('defaults', 'hypervisor_id', hypervisor_id)
            result = virtwho.run_service()
            assert (result['error'] == 0
                    and result['send'] == 1
                    and result['thread'] == 1
                    and result['hypervisor_id'] == hypervisor_data[f'hypervisor_{hypervisor_id}'])
            if REGISTER == 'rhsm':
                assert rhsm.consumers(hypervisor_data['hypervisor_hostname'])
                rhsm.delete(hypervisor_data['hypervisor_hostname'])
            else:
                if hypervisor_id == 'hostname':
                    assert satellite.host_id(hypervisor_data['hypervisor_hostname'])
                    assert not satellite.host_id(hypervisor_data['hypervisor_uuid'])
                    if hypervisor_id in ['esx', 'rhevm']:
                        assert not satellite.host_id(hypervisor_data['hypervisor_hwuuid'])
                elif hypervisor_id == 'uuid':
                    assert satellite.host_id(hypervisor_data['hypervisor_uuid'])
                    assert not satellite.host_id(hypervisor_data['hypervisor_hostname'])
                    if hypervisor_id in ['esx', 'rhevm']:
                        assert not satellite.host_id(hypervisor_data['hypervisor_hwuuid'])
                else:
                    assert satellite.host_id(hypervisor_data['hypervisor_hwuuid'])
                    assert not satellite.host_id(hypervisor_data['hypervisor_hostname'])
                    assert not satellite.host_id(hypervisor_data['hypervisor_uuid'])

    @pytest.mark.tier1
    def test_http_proxy_in_virtwho_conf(self, virtwho, globalconf, proxy_data):
        """Test the http_proxy, https_proxy and no_proxy options in /etc/virtwho.conf

        :title: virt-who: config: test http_proxy, https_proxy and no_proxy options
        :id: f7d2d5fc-2446-46ae-8fd4-eda0109f75a5
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. Run virt-who with http_proxy setting in /etc/virt-who.conf
            2. Run virt-who with unreachable http_proxy setting in /etc/virt-who.conf
            3. Run virt-who with unreachable http_proxy and no_proxy setting in /etc/virt-who.conf
            4. Run virt-who with https_proxy setting in /etc/virt-who.conf
            5. Run virt-who with unreachable https_proxy setting in /etc/virt-who.conf
            6. Run virt-who with unreachable https_proxy and no_proxy setting in /etc/virt-who.conf

        :expectedresults:

            1. Succeeded to run virt-who, succeeded to find expected proxy log in rhsm log
            2. Virt-who runs error, succeeded to find expected proxy log in rhsm log
            3. Succeeded to run virt-who
            4. Succeeded to run virt-who, succeeded to find expected proxy log in rhsm log
            5. Virt-who runs error, succeeded to find expected proxy log in rhsm log
            6. Succeeded to run virt-who
        """
        globalconf.update('global', 'debug', 'True')

        for proxy in ['http_proxy', 'https_proxy']:
            # run virt-who with http_proxy/https_proxy setting
            globalconf.update('system_environment', proxy, proxy_data[proxy])
            connection_msg = proxy_data['connection_log']
            proxy_msg = proxy_data['proxy_log']
            result = virtwho.run_service()
            assert (result['error'] == 0
                    and result['send'] == 1
                    and result['thread'] == 1
                    and connection_msg in result['log']
                    and proxy_msg in result['log'])

            # run virt-who with unreachable http_proxy/https_proxy setting
            globalconf.update('system_environment', proxy, proxy_data[f'bad_{proxy}'])
            result = virtwho.run_service()
            assert (result['error'] == 1 or 2)
            assert (any(error_msg in result['error_msg'] for error_msg in proxy_data['error']))

            # run virt-who with unreachable http_proxy/https and no_proxy setting
            globalconf.update('system_environment', 'no_proxy', '*')
            result = virtwho.run_service()
            assert (result['error'] == 0
                    and result['send'] == 1
                    and result['thread'] == 1)

            globalconf.delete('system_environment')


@pytest.mark.usefixtures('globalconf_clean')
@pytest.mark.usefixtures('hypervisor')
@pytest.mark.rhel8
class TestSysConfiguration:
    @pytest.mark.tier1
    def test_debug_in_virtwho_sysconfig(self, virtwho, sysconfig):
        """Test the VIRTWHO_DEBUG option in /etc/sysconfig/virt-who

        :title: virt-who: config: test VIRTWHO_DEBUG option
        :id: 0b60fbdb-4554-4f92-bbc9-fdd43ff71adb
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. Run virt-who with "VIRTWHO_DEBUG=1" in /etc/sysconfig/virt-who file
            2. Run virt-who with "VIRTWHO_DEBUG=0" in /etc/sysconfig/virt-who file

        :expectedresults:

            1. no [DEBUG] log printed
            2. [DEBUG] logs are printed with the configuration
        """
        sysconfig.update(**{'VIRTWHO_DEBUG': '1'})
        result = virtwho.run_service()
        assert (result['send'] == 1
                and result['error'] == 0
                and result['debug'] is True)

        sysconfig.update(**{'VIRTWHO_DEBUG': '0'})
        result = virtwho.run_service()
        assert (result['send'] == 1
                and result['error'] == 0
                and result['debug'] is False)

        sysconfig.clean()

    @pytest.mark.tier1
    def test_oneshot_in_virtwho_sysocnfig(self, virtwho, sysconfig):
        """Test the VIRTWHO_ONE_SHOT option in /etc/sysconfig/virt-who

        :title: virt-who: config: test VIRTWHO_ONE_SHOT option
        :id: 8f8204c7-6c6d-4189-8947-774ed5018835
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. Run virt-who with "VIRTWHO_ONE_SHOT=1" in /etc/sysconfig/virt-who
            2. Run virt-who with "VIRTWHO_ONE_SHOT=0" in /etc/sysconfig/virt-who

        :expectedresults:

            1. Can see 'Thread X stopped after running once' log in rhsm.log
            2. Cannot see 'Thread X stopped after running once' log in rhsm.log
        """
        sysconfg_options = {'VIRTWHO_DEBUG': '1',
                            'VIRTWHO_ONE_SHOT': '1'}
        sysconfig.update(**sysconfg_options)
        result = virtwho.run_service()
        assert (result['send'] == 1
                and result['error'] == 0
                and result['terminate'] == 1
                and result['oneshot'] is True)

        sysconfg_options['VIRTWHO_ONE_SHOT'] = 0
        sysconfig.update(**sysconfg_options)
        result = virtwho.run_service()
        assert (result['send'] == 1
                and result['error'] == 0
                and result['terminate'] == 0
                and result['oneshot'] is False)

        sysconfig.clean()

    @pytest.mark.tier1
    def test_interval_in_virtwho_sysocnfig(self, virtwho, sysconfig):
        """Test the VIRTWHO_INTERVAL option in /etc/sysconfig/virt-who

        :title: virt-who: config: test VIRTWHO_INTERVAL option
        :id: e46ceb4c-e4ed-47c2-9d3e-2a15a0c34d83
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. Enable interval and set to 10 in /etc/sysconfig/virt-who
            2. Enable interval and set to 60 in /etc/sysconfig/virt-who
        :expectedresults:

            1. Default value of 3600 seconds will be used when configure lower than 60 seconds
            2. Configure successfully, and virt-who starting infinite loop with 60 seconds interval
        """
        sysconfg_options = {'VIRTWHO_DEBUG': '1',
                            'VIRTWHO_INTERVAL': '10'}
        sysconfig.update(**sysconfg_options)
        result = virtwho.run_service()
        assert (result['send'] == 1
                and result['error'] == 0
                and result['interval'] == 3600)

        sysconfg_options['VIRTWHO_INTERVAL'] = 60
        sysconfig.update(**sysconfg_options)
        result = virtwho.run_service(wait=60)
        assert (result['send'] == 1
                and result['error'] == 0
                and result['loop'] == 60)

        sysconfig.clean()
