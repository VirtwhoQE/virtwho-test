from virtwho.settings import config
from virtwho.runner import VirtwhoRunner
from virtwho.configure import VirtwhoHypervisorConfig
from virtwho.configure import VirtwhoGlobalConfig
from virtwho.configure import get_hypervisor_handler, virtwho_ssh_connect
from virtwho.configure import get_register_handler
from virtwho.register import SubscriptionManager
from virtwho import HYPERVISOR, REGISTER
import pytest


@pytest.fixture(name='hypervisor_handler', scope='session')
def virtwho_hypervisor_handler():
    return get_hypervisor_handler(HYPERVISOR)


@pytest.fixture(name='hypervisor', scope='session')
def virtwho_hypervisor_config():
    return VirtwhoHypervisorConfig(HYPERVISOR, REGISTER)


@pytest.fixture(name='hypervisor_create', scope='class')
def virtwho_hypervisor_config_file_create(hypervisor):
    hypervisor.create()


@pytest.fixture(name='register_handler', scope='session')
def virtwho_register_handler():
    return get_register_handler(REGISTER)


@pytest.fixture(name='globalconf', scope='session')
def virtwho_global_config():
    return VirtwhoGlobalConfig(HYPERVISOR)


@pytest.fixture(name='globalconf_clean', scope='function')
def virtwho_global_config_clean(globalconf):
    globalconf.clean()


@pytest.fixture(name='global_debug_true', scope='function')
def virtwho_global_config_debug_true(globalconf):
    globalconf.update('global', 'debug', 'true')


@pytest.fixture(name='virtwho', scope='class')
def virtwho_runner():
    return VirtwhoRunner(HYPERVISOR, REGISTER)


@pytest.fixture(name='ssh_host', scope='session')
def virtwho_host_ssh_connect():
    return virtwho_ssh_connect(HYPERVISOR)


@pytest.fixture(name='sm_host', scope='session')
def subscription_manager_virtwho_host_with_default_org(register_handler):
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
def subscription_manager_guest_host_with_default_org(hypervisor_handler, register_handler):
    return SubscriptionManager(host=hypervisor_handler.guest_ip,
                               username=hypervisor_handler.guest_username,
                               password=hypervisor_handler.guest_password,
                               port=22,
                               register_type=REGISTER,
                               org=register_handler.default_org)


@pytest.fixture(name='hypervisor_data', scope='session')
def hypervisor_common_data_get_from_virtwho_ini(hypervisor_handler):
    data = dict()
    data['guest_uuid'] = hypervisor_handler.guest_uuid
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
