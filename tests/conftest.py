from virtwho.settings import config
from virtwho.runner import VirtwhoRunner
from virtwho.configure import VirtwhoHypervisorConfig
from virtwho.configure import VirtwhoGlobalConfig
from virtwho.configure import get_hypervisor_handler
from virtwho.configure import get_register_handler
from virtwho.register import SubscriptionManager
import pytest


mode = config.job.mode
register_type = config.job.register

if mode == 'local':
    vw_server = config.local.server
    vw_username = config.local.username
    vw_password = config.local.password
    vw_port = config.local.port or 22
else:
    vw_server = config.virtwho.server
    vw_username = config.virtwho.username
    vw_password = config.virtwho.password
    vw_port = config.virtwho.port or 22

hypervisor = get_hypervisor_handler(mode)
guest_server = hypervisor.guest_ip
guest_username = hypervisor.guest_username
guest_password = hypervisor.guest_password

register = get_register_handler(register_type)
org = register.default_org
if 'satellite' in register_type:
    secondary_org = register.secondary_org
activation_key = register.activation_key


@pytest.fixture(scope='class')
def hypervisor():
    return VirtwhoHypervisorConfig(mode, register_type)


@pytest.fixture(scope='session')
def virtwhoconf():
    return VirtwhoGlobalConfig(mode)


@pytest.fixture(scope='class')
def virtwho():
    return VirtwhoRunner(mode, register_type)


@pytest.fixture(name='sm_virtwho', scope='session')
def subscription_manager_virtwho_host_with_default_org():
    return SubscriptionManager(host=vw_server,
                               username=vw_username,
                               password=vw_password,
                               port=vw_port,
                               register_type=register_type, org=org)


@pytest.fixture(name='sm_virtwho_org', scope='session')
def subscription_manager_virtwho_host_with_second_org():
    return SubscriptionManager(host=vw_server,
                               username=vw_username,
                               password=vw_password,
                               port=vw_port,
                               register_type=register_type,
                               org=secondary_org)


@pytest.fixture(name='sm_virtwho_ak', scope='session')
def subscription_manager_virtwho_host_with_activation_key():
    return SubscriptionManager(host=vw_server,
                               username=vw_username,
                               password=vw_password,
                               port=vw_port,
                               register_type=register_type,
                               org=org,
                               activation_key=activation_key)


@pytest.fixture(name='sm_guest', scope='session')
def subscription_manager_guest_host_with_default_org():
    return SubscriptionManager(host=guest_server,
                               username=guest_username,
                               password=guest_password,
                               port=22,
                               register_type=register_type, org=org)


@pytest.fixture(name='sm_guest_org', scope='session')
def subscription_manager_guest_host_with_second_org():
    return SubscriptionManager(host=guest_server,
                               username=guest_username,
                               password=guest_password,
                               port=22,
                               register_type=register_type,
                               org=secondary_org)


@pytest.fixture(name='sm_guest_ak', scope='session')
def subscription_manager_guest_host_with_activation_key():
    return SubscriptionManager(host=guest_server,
                               username=guest_username,
                               password=guest_password,
                               port=22,
                               register_type=register_type,
                               org=org,
                               activation_key=activation_key)


@pytest.fixture(name='global_conf_clean', scope='class')
def virtwho_conf_file_clean(virtwhoconf):
    virtwhoconf.clean()
