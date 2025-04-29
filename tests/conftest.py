import pytest

from virtwho.settings import config
from virtwho.runner import VirtwhoRunner
from virtwho.configure import VirtwhoSysConfig
from virtwho.configure import VirtwhoGlobalConfig
from virtwho.configure import RHSMConf
from virtwho.configure import get_hypervisor_handler, virtwho_ssh_connect
from virtwho.configure import get_register_handler
from virtwho.configure import hypervisor_create

from virtwho.ssh import SSHConnect
from virtwho.register import SubscriptionManager, Satellite, RHSM
from virtwho import HYPERVISOR, REGISTER, RHEL_COMPOSE, logger
from virtwho.base import hostname_get

hypervisor_handler = get_hypervisor_handler(HYPERVISOR)
register_handler = get_register_handler(REGISTER)


def pytest_runtest_logstart(nodeid):
    logger.info(f"Started Test: {nodeid}")


def pytest_runtest_logfinish(nodeid):
    logger.info(f"Finished Test: {nodeid}")


def pytest_addoption(parser):
    parser.addoption(
        "--rhelver",
        action="store",
        metavar="NAME",
        help="Only run tests for this RHEL version: rhel8, rhel9, rhel10",
    )


def pytest_collection_modifyitems(session, config, items):
    logger.info(f"collection modifyitems is run, {session}, {config}, {items}")
    rhelver = config.getoption("--rhelver")
    if not rhelver:
        return
    deselected_items = []
    selected_items = []
    for item in items:
        release = item.get_closest_marker("release")
        if not release:
            return
        release_conf = release.kwargs
        if rhelver not in release_conf:
            return
        if not release_conf[rhelver]:
            deselected_items += [item]
            item.add_marker(
                pytest.mark.skip(
                    reason=f"skipped due to required rhel (should be {rhelver})"
                )
            )
        else:
            selected_items += [item]

    logger.info("pytest_collection_modifyitems was run")
    if deselected_items:
        logger.info(f"a few items to deselect: {deselected_items}")
        logger.info(f"remaining tests to run {selected_items}")
        config.hook.pytest_deselected(deselected_items)
        items[:] = selected_items


@pytest.fixture(scope="class")
def class_hypervisor():
    """Instantication of class VirtwhoHypervisorConfig()"""
    return hypervisor_create(HYPERVISOR, REGISTER)


@pytest.fixture(scope="function")
def function_hypervisor():
    """Create virt-who hypervisor test file with all rhsm options"""
    return hypervisor_create(HYPERVISOR, REGISTER)


@pytest.fixture(scope="session")
def globalconf():
    """Instantication of class VirtwhoGlobalConfig()"""
    return VirtwhoGlobalConfig(HYPERVISOR)


@pytest.fixture(scope="class")
def class_globalconf_clean(globalconf):
    """
    Clean all the settings in /etc/virt-who.conf and /etc/sysconfig/virt-who
    """
    globalconf.clean()
    if "RHEL-8" in RHEL_COMPOSE:
        sysconfig = VirtwhoSysConfig(HYPERVISOR)
        sysconfig.clean()


@pytest.fixture(scope="function")
def function_globalconf_clean(globalconf):
    """
    Clean all the settings in /etc/virt-who.conf and /etc/sysconfig/virt-who
    """
    globalconf.clean()
    if "RHEL-8" in RHEL_COMPOSE:
        sysconfig = VirtwhoSysConfig(HYPERVISOR)
        sysconfig.clean()


@pytest.fixture(scope="function")
def function_virtwho_d_conf_clean(ssh_host):
    """Clean all config files in /etc/virt-who.d/ folder"""
    cmd = "rm -rf /etc/virt-who.d/*"
    ssh_host.runcmd(cmd)


@pytest.fixture(scope="class")
def class_virtwho_d_conf_clean(ssh_host):
    """Clean all config files in /etc/virt-who.d/ folder"""
    cmd = "rm -rf /etc/virt-who.d/*"
    ssh_host.runcmd(cmd)


@pytest.fixture(scope="function")
def function_sysconfig():
    return VirtwhoSysConfig(HYPERVISOR)


@pytest.fixture(scope="class")
def class_debug_true(globalconf):
    """Set the debug=True in /etc/virt-who.conf"""
    globalconf.update("global", "debug", "true")


@pytest.fixture(scope="function")
def function_debug_true(globalconf):
    """Set the debug=True in /etc/virt-who.conf"""
    globalconf.update("global", "debug", "true")


@pytest.fixture(scope="function")
def function_debug_false(globalconf):
    """Set the debug=False in /etc/virt-who.conf"""
    globalconf.update("global", "debug", "false")


@pytest.fixture(scope="session")
def virtwho():
    """Instantication of class VirtwhoRunner()"""
    return VirtwhoRunner(HYPERVISOR, REGISTER)


@pytest.fixture(scope="session")
def ssh_host():
    """ssh connect access to virt-who host"""
    return virtwho_ssh_connect(HYPERVISOR)


@pytest.fixture(scope="session")
def ssh_guest():
    """ssh connect access to hypervisor guest"""
    port = 22
    if HYPERVISOR == "kubevirt":
        port = hypervisor_handler.guest_port
    return SSHConnect(
        host=hypervisor_handler.guest_ip,
        user=hypervisor_handler.guest_username,
        pwd=hypervisor_handler.guest_password,
        port=port,
    )


@pytest.fixture(scope="session")
def sm_host():
    """
    Instantication of class SubscriptionManager() for virt-who host
    with default org
    """
    vw_server = config.virtwho.server
    vw_username = config.virtwho.username
    vw_password = config.virtwho.password
    vw_port = config.virtwho.port or 22
    if HYPERVISOR == "local":
        vw_server = config.local.server
        vw_username = config.local.username
        vw_password = config.local.password
        vw_port = config.local.port or 22
    return SubscriptionManager(
        host=vw_server,
        username=vw_username,
        password=vw_password,
        port=vw_port,
        register_type=REGISTER,
        org=register_handler.default_org,
    )


@pytest.fixture(scope="session")
def sm_guest():
    """
    Instantication of class SubscriptionManager() for hypervisor guest
    with default org
    """
    port = 22
    if HYPERVISOR == "kubevirt":
        port = hypervisor_handler.guest_port
    return SubscriptionManager(
        host=hypervisor_handler.guest_ip,
        username=hypervisor_handler.guest_username,
        password=hypervisor_handler.guest_password,
        port=port,
        register_type=REGISTER,
        org=register_handler.default_org,
    )


@pytest.fixture(scope="function")
def function_host_register(sm_host):
    """register the virt-who host"""
    sm_host.register()


@pytest.fixture(scope="function")
def function_host_register_for_local_mode(sm_host):
    """register the virt-who host only when run for local mode"""
    if HYPERVISOR == "local":
        sm_host.register()


@pytest.fixture(scope="class")
def class_host_unregister(sm_host):
    """unregister the virt-who host"""
    sm_host.unregister()


@pytest.fixture(scope="function")
def function_guest_register(sm_guest):
    """register the guest"""
    sm_guest.register()


@pytest.fixture(scope="class")
def class_guest_register(sm_guest):
    """register the guest"""
    sm_guest.register()


@pytest.fixture(scope="class")
def class_guest_unregister(sm_guest):
    """unregister the guest"""
    sm_guest.unregister()


@pytest.fixture(scope="session")
def satellite():
    """Instantication of class Satellite() with default org"""
    if REGISTER == "satellite":
        return Satellite(
            server=config.satellite.server,
            org=config.satellite.default_org,
            activation_key=config.satellite.activation_key,
        )
    return None


@pytest.fixture(scope="session")
def rhsm():
    """Instantication of class RHSM()"""
    if REGISTER == "rhsm":
        return RHSM()
    return None


@pytest.fixture(scope="session")
def rhsmconf():
    """Instantication of class RHSMConf()"""
    return RHSMConf(HYPERVISOR)


@pytest.fixture(scope="function")
def function_rhsmconf_recovery(rhsmconf):
    """Recover the rhsm.conf to default one."""
    rhsmconf.recovery()


@pytest.fixture(scope="session")
def hypervisor_data(ssh_guest):
    """Hypervisor data for testing, mainly got from virtwho.ini file"""
    data = dict()
    data["guest_name"] = hypervisor_handler.guest_name
    data["guest_ip"] = hypervisor_handler.guest_ip
    data["guest_uuid"] = hypervisor_handler.guest_uuid
    data["guest_hostname"] = hostname_get(ssh_guest)
    data["hypervisor_hwuuid"] = ""
    data["cluster"] = ""
    if HYPERVISOR == "esx":
        data["hypervisor_uuid"] = hypervisor_handler.esx_uuid
        data["hypervisor_hostname"] = hypervisor_handler.esx_hostname
        data["hypervisor_hwuuid"] = hypervisor_handler.esx_hwuuid
        data["type"] = hypervisor_handler.esx_type
        data["version"] = hypervisor_handler.esx_version
        data["cpu"] = hypervisor_handler.esx_cpu
        data["cluster"] = hypervisor_handler.esx_cluster
        data["host_ip"] = hypervisor_handler.esx_ip
        data["ssh_ip"] = hypervisor_handler.ssh_ip
        data["ssh_username"] = hypervisor_handler.ssh_username
        data["ssh_password"] = hypervisor_handler.ssh_password
    elif HYPERVISOR == "rhevm":
        data["hypervisor_uuid"] = hypervisor_handler.vdsm_uuid
        data["hypervisor_hostname"] = hypervisor_handler.vdsm_hostname
        data["hypervisor_hwuuid"] = hypervisor_handler.vdsm_hwuuid
        data["type"] = hypervisor_handler.vdsm_type
        data["version"] = hypervisor_handler.vdsm_version
        data["cpu"] = hypervisor_handler.vdsm_cpu
        data["cluster"] = hypervisor_handler.vdsm_cluster
    elif HYPERVISOR == "local":
        data["hypervisor_hostname"] = hypervisor_handler.hostname
    else:
        data["hypervisor_uuid"] = hypervisor_handler.uuid
        data["hypervisor_hostname"] = hypervisor_handler.hostname
        data["type"] = hypervisor_handler.type
        data["version"] = hypervisor_handler.version
        data["cpu"] = hypervisor_handler.cpu
    if HYPERVISOR == "ahv":
        data["cluster"] = hypervisor_handler.cluster
    if HYPERVISOR == "kubevirt":
        data["hypervisor_server"] = hypervisor_handler.endpoint
        data["hypervisor_config_file"] = hypervisor_handler.config_file
        data["hypervisor_config_file_no_cert"] = hypervisor_handler.config_file_no_cert
        data["hypervisor_config_url"] = hypervisor_handler.config_url
        data["hypervisor_config_url_no_cert"] = hypervisor_handler.config_url_no_cert
    else:
        data["hypervisor_password"] = hypervisor_handler.password
        data["hypervisor_server"] = hypervisor_handler.server
        data["hypervisor_username"] = hypervisor_handler.username
    return data


@pytest.fixture(scope="session")
def register_data():
    """Register data for testing from virtwho.ini file"""
    data = dict()
    data["server"] = register_handler.server
    data["username"] = register_handler.username
    data["password"] = register_handler.password
    data["prefix"] = register_handler.prefix
    data["port"] = register_handler.port
    data["username"] = register_handler.username
    data["password"] = register_handler.password
    data["default_org"] = register_handler.default_org
    data["activation_key"] = register_handler.activation_key
    data["secondary_org"] = ""
    if REGISTER == "satellite":
        data["secondary_org"] = register_handler.secondary_org
    return data


@pytest.fixture(scope="session")
def proxy_data():
    """Proxy data for testing"""
    proxy = dict()
    proxy_server = config.virtwho.proxy_server
    proxy_port = config.virtwho.proxy_port
    bad_proxy_server = "bad.proxy.redhat.com"
    bad_proxy_port = "9999"
    good_proxy = f"{proxy_server}:{proxy_port}"
    bad_proxy = f"{bad_proxy_server}:{bad_proxy_port}"
    proxy["server"] = proxy_server
    proxy["port"] = proxy_port
    proxy["bad_server"] = bad_proxy_server
    proxy["bad_port"] = bad_proxy_port
    proxy["http_proxy"] = f"http://{good_proxy}"
    proxy["https_proxy"] = f"https://{good_proxy}"
    proxy["bad_http_proxy"] = f"http://{bad_proxy}"
    proxy["bad_https_proxy"] = f"https://{bad_proxy}"
    proxy["connection_log"] = f"Connection built: " f"http_proxy={good_proxy}"
    proxy["proxy_log"] = f"Using proxy: {good_proxy}"
    proxy["error"] = [
        "Connection refused",
        "Cannot connect to proxy",
        "Connection timed out",
        "Unable to connect",
    ]
    return proxy


@pytest.fixture(scope="session")
def owner_data():
    """Owner data for testing"""
    owner = dict()
    bad_owner = "bad_owner"
    owner["owner"] = register_handler.default_org
    owner["bad_owner"] = bad_owner
    owner["error"] = [
        f"Organization with id {bad_owner} could not be found",
        f"Couldn't find Organization '{bad_owner}'",
        f"[Owner] with ID(s) {bad_owner} could not be found",
        f"Owner with ID(s) {bad_owner} could not be found",
    ]
    # the errors for null are different when virt-who host registered and unreigstered.
    owner["null_error"] = [
        "Communication with subscription manager failed",
        "Unable to read certificate, system is not registered or you are not root",
    ]
    return owner


@pytest.fixture(scope="session")
def configs_data():
    """Configs data for testing"""
    configs = dict()
    configs["wrong_configs"] = "xxxx"
    configs["error"] = [
        "Unable to read configuration file",
        "No valid configuration file provided using -c/--config",
    ]
    return configs
