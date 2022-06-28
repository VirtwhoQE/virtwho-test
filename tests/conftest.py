import pytest

from virtwho.settings import config
from virtwho.runner import VirtwhoRunner
from virtwho.configure import VirtwhoHypervisorConfig
from virtwho.configure import VirtwhoGlobalConfig
from virtwho.configure import get_hypervisor_handler, virtwho_ssh_connect
from virtwho.configure import get_register_handler
from virtwho.ssh import SSHConnect
from virtwho.register import SubscriptionManager, Satellite, RHSM
from virtwho import HYPERVISOR, REGISTER, logger
from virtwho.base import hostname_get

hypervisor_handler = get_hypervisor_handler(HYPERVISOR)
register_handler = get_register_handler(REGISTER)


@pytest.fixture(name='hypervisor', scope='session')
def virtwho_hypervisor_config():
    return VirtwhoHypervisorConfig(HYPERVISOR, REGISTER)


@pytest.fixture(name='hypervisor_create', scope='class')
def virtwho_hypervisor_config_file_create_with_rhsm_options(hypervisor):
    hypervisor.create()


@pytest.fixture(name='globalconf', scope='session')
def virtwho_global_config():
    return VirtwhoGlobalConfig(HYPERVISOR)


@pytest.fixture(name='globalconf_clean', scope='function')
def virtwho_global_config_clean(globalconf):
    globalconf.clean()


@pytest.fixture(name='debug_true', scope='function')
def virtwho_global_config_debug_true(globalconf):
    globalconf.update('global', 'debug', 'true')


@pytest.fixture(name='virtwho', scope='class')
def virtwho_runner():
    return VirtwhoRunner(HYPERVISOR, REGISTER)


@pytest.fixture(name='ssh_host', scope='session')
def virtwho_host_ssh_connect():
    return virtwho_ssh_connect(HYPERVISOR)


@pytest.fixture(name='ssh_guest', scope='session')
def guest_ssh_connect():
    port = 22
    if HYPERVISOR == 'kubevirt':
        port = hypervisor_handler.guest_port
    return SSHConnect(host=hypervisor_handler.guest_ip,
                      user=hypervisor_handler.guest_username,
                      pwd=hypervisor_handler.guest_password,
                      port=port)


@pytest.fixture(name='sm_host', scope='session')
def subscription_manager_virtwho_host_with_default_org():
    vw_server = config.virtwho.server
    vw_username = config.virtwho.username
    vw_password = config.virtwho.password
    vw_port = config.virtwho.port or 22
    if HYPERVISOR == 'local':
        vw_server = config.local.server
        vw_username = config.local.username
        vw_password = config.local.password
        vw_port = config.local.port or 22
    return SubscriptionManager(host=vw_server,
                               username=vw_username,
                               password=vw_password,
                               port=vw_port,
                               register_type=REGISTER,
                               org=register_handler.default_org)


@pytest.fixture(name='sm_guest', scope='session')
def subscription_manager_guest_host_with_default_org():
    return SubscriptionManager(host=hypervisor_handler.guest_ip,
                               username=hypervisor_handler.guest_username,
                               password=hypervisor_handler.guest_password,
                               port=22,
                               register_type=REGISTER,
                               org=register_handler.default_org)


@pytest.fixture(name='hypervisor_data', scope='session')
def hypervisor_common_data_get_from_virtwho_ini(ssh_guest):
    data = dict()
    data['guest_name'] = hypervisor_handler.guest_name
    data['guest_ip'] = hypervisor_handler.guest_ip
    data['guest_uuid'] = hypervisor_handler.guest_uuid
    data['guest_hostname'] = hostname_get(ssh_guest)
    data['hypervisor_uuid'] = ''
    data['hypervisor_hostname'] = ''
    data['hypervisor_hwuuid'] = ''
    if HYPERVISOR == 'esx':
        data['hypervisor_uuid'] = hypervisor_handler.esx_uuid
        data['hypervisor_hostname'] = hypervisor_handler.esx_hostname
        data['hypervisor_hwuuid'] = hypervisor_handler.esx_hwuuid
    elif HYPERVISOR == 'rhevm':
        data['hypervisor_uuid'] = hypervisor_handler.vdsm_uuid
        data['hypervisor_hostname'] = hypervisor_handler.vdsm_hostname
        data['hypervisor_hwuuid'] = hypervisor_handler.vdsm_hwuuid
    else:
        data['hypervisor_uuid'] = hypervisor_handler.uuid
        data['hypervisor_hostname'] = hypervisor_handler.hostname
    return data


@pytest.fixture(name='register_data', scope='session')
def register_server_common_data_get_from_virtwho_ini():
    data = dict()
    data['server'] = register_handler.server
    data['prefix'] = register_handler.prefix
    data['port'] = register_handler.port
    data['default_org'] = register_handler.default_org
    data['activation_key'] = register_handler.activation_key
    data['secondary_org'] = ''
    if REGISTER == 'satellite':
        data['secondary_org'] = register_handler.secondary_org
    return data


@pytest.fixture(name='satellite', scope='session')
def satellite_default_org():
    return Satellite(
        server=config.satellite.server,
        org=config.satellite.default_org,
        activation_key=config.satellite.activation_key
    )


@pytest.fixture(name='rhsm', scope='session')
def rhsm():
    return RHSM()


@pytest.fixture(name='data', scope='session')
def test_data():
    data = dict()

    proxy = dict()
    proxy_server = config.virtwho.proxy_server
    proxy_port = config.virtwho.proxy_port
    bad_proxy_server = 'bad.proxy.redhat.com'
    bad_proxy_port = '9999'
    good_proxy = f'{proxy_server}:{proxy_port}'
    bad_proxy = f'{bad_proxy_server}:{bad_proxy_port}'
    proxy['server'] = proxy_server
    proxy['port'] = proxy_port
    proxy['bad_server'] = bad_proxy_server
    proxy['bad_port'] = bad_proxy_port
    proxy['http_proxy'] = f'http://{good_proxy}'
    proxy['https_proxy'] = f'https://{good_proxy}'
    proxy['bad_http_proxy'] = f'http://{bad_proxy}'
    proxy['bad_https_proxy'] = f'https://{bad_proxy}'
    proxy['connection_log'] = f'Connection built: ' \
                              f'http_proxy={good_proxy}'
    proxy['proxy_log'] = f'Using proxy: {good_proxy}'
    proxy['error'] = ['Connection refused',
                      'Cannot connect to proxy',
                      'Connection timed out',
                      'Unable to connect']

    data['proxy'] = proxy
    return data

