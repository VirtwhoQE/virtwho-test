from virtwho.settings import config
from virtwho.runner import VirtwhoRunner
from virtwho.configure import VirtwhoHypervisorConfig
from virtwho.configure import VirtwhoGlobalConfig
from virtwho.configure import get_hypervisor_handler
from virtwho.configure import get_register_handler
from virtwho.register import SubscriptionManager
from virtwho.register import RHSM
from virtwho.register import Satellite
import pytest


mode = config.job.mode
register_type = config.job.register


@pytest.fixture(name='hypervisor_handler', scope='session')
def virtwho_hypervisor_handler():
    return get_hypervisor_handler(mode)


@pytest.fixture(name='register_handler', scope='session')
def virtwho_register_handler():
    return get_register_handler(register_type)


@pytest.fixture(name='hypervisor', scope='session')
def virtwho_hypervisor_config():
    return VirtwhoHypervisorConfig(mode, register_type)


@pytest.fixture(name='hypervisor_create', scope='class')
def virtwho_hypervisor_config_file_create(hypervisor):
    hypervisor.create()


@pytest.fixture(name='globalconf', scope='session')
def virtwho_global_config():
    return VirtwhoGlobalConfig(mode)


@pytest.fixture(name='globalconf_clean', scope='class')
def virtwho_global_config_clean(globalconf):
    globalconf.clean()


@pytest.fixture(name='virtwho', scope='class')
def virtwho_runner():
    return VirtwhoRunner(mode, register_type)


@pytest.fixture(name='sm_host', scope='session')
def subscription_manager_virtwho_host_with_default_org(register_handler):
    vw_server = config.virtwho.server
    vw_username = config.virtwho.username
    vw_password = config.virtwho.password
    vw_port = config.virtwho.port or 22
    if mode == 'local':
        vw_server = config.local.server
        vw_username = config.local.username
        vw_password = config.local.password
        vw_port = config.local.port or 22
    return SubscriptionManager(host=vw_server,
                               username=vw_username,
                               password=vw_password,
                               port=vw_port,
                               register_type=register_type,
                               org=register_handler.default_org)


@pytest.fixture(name='sm_guest', scope='session')
def subscription_manager_guest_host_with_default_org(hypervisor_handler, register_handler):
    return SubscriptionManager(host=hypervisor_handler.guest_ip,
                               username=hypervisor_handler.guest_username,
                               password=hypervisor_handler.guest_password,
                               port=22,
                               register_type=register_type,
                               org=register_handler.default_org)


@pytest.fixture(name='rhsm', scope='session')
def rhsm():
    return RHSM()


@pytest.fixture(name='satellite', scope='session')
def satellite_with_default_org():
    return Satellite(org=config.satellite.default_org)
