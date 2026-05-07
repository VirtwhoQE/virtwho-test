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
            continue
        release_conf = release.kwargs
        if rhelver not in release_conf:
            continue
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


def _kubevirt_discover(data):
    """Query the KubeVirt API to populate hypervisor identity fields that are
    left blank in virtwho.ini.  This allows the test suite to run without
    pre-populating uuid/hostname/version/cpu in the INI.

    When the Nodes API is forbidden (ITUP), ``get_host_info`` only returns a
    derived ``hostname`` -- no ``uuid``, ``cpu``, or ``version``.  In that
    case, virt-who's runtime-patched ``getHostGuestMapping`` uses the raw
    ``nodeName`` as the hypervisorId, so we mirror that here."""
    from hypervisor.virt.kubevirt.kubevirtapi import KubevirtApi

    namespace = getattr(hypervisor_handler, "namespace", None) or None
    api = KubevirtApi(
        hypervisor_handler.endpoint,
        hypervisor_handler.token,
        namespace=namespace,
    )
    guest_name = hypervisor_handler.guest_name

    vm_info = api.get_vm_info(guest_name)
    node_name = vm_info.get("hostname", "")
    host_info = api.get_host_info(node_name) if node_name else {}
    logger.info(
        f"KubeVirt auto-discovery for {guest_name}: "
        f"vm_info={vm_info}, host_info={host_info}"
    )

    nodes_api_available = "uuid" in host_info

    if nodes_api_available:
        data["hypervisor_uuid"] = host_info["uuid"]
        data["hypervisor_hostname"] = host_info["hostname"]
        data["version"] = host_info.get("version", "")
        data["cpu"] = host_info.get("cpu", "")
    elif node_name:
        data["hypervisor_uuid"] = node_name
        data["hypervisor_hostname"] = node_name
    if vm_info.get("guest_uuid") and not data.get("guest_uuid"):
        data["guest_uuid"] = vm_info["guest_uuid"]


def _parse_oneshot_json(output, hyp_type):
    """Extract the JSON mapping dict from raw ``virt-who -p`` output.

    Returns the parsed dict or ``None`` if no valid JSON is found."""
    import json as json_mod

    raw = output.strip()
    json_start = raw.find("{")
    if json_start == -1:
        logger.warning(f"{hyp_type} oneshot-discover: no JSON found in output")
        return None
    raw = raw[json_start:]
    try:
        mapping = json_mod.loads(raw)
    except json_mod.JSONDecodeError as exc:
        logger.warning(
            f"{hyp_type} oneshot-discover: malformed JSON (truncated?): {exc}"
        )
        return None
    hypervisors = mapping.get("hypervisors", [])
    if not hypervisors:
        logger.warning(f"{hyp_type} oneshot-discover: no hypervisors in mapping")
        return None
    return mapping


def _extract_hv_facts(matched_hv, data):
    """Populate *data* with hypervisor identity and facts from a matched
    hypervisor entry returned by ``virt-who -p``."""
    hv_id = matched_hv.get("hypervisorId", {})
    if isinstance(hv_id, dict):
        data["hypervisor_uuid"] = hv_id.get("hypervisorId", "")
    else:
        data["hypervisor_uuid"] = str(hv_id)

    data["hypervisor_hostname"] = matched_hv.get("name", "")

    raw_facts = matched_hv.get("facts", [])
    facts = {}
    if isinstance(raw_facts, dict):
        facts = raw_facts
    elif isinstance(raw_facts, list):
        for f in raw_facts:
            if isinstance(f, dict):
                facts[f.get("name", "")] = f.get("value", "")
            elif isinstance(f, str) and "=" in f:
                k, _, v = f.partition("=")
                facts[k] = v
    if facts.get("cpu.cpu_socket(s)"):
        data["cpu"] = facts["cpu.cpu_socket(s)"]
    if facts.get("hypervisor.version"):
        data["version"] = facts["hypervisor.version"]
    if facts.get("hypervisor.cluster"):
        data["cluster"] = facts["hypervisor.cluster"]


def _resolve_guest_uuid(ssh, matched_hv, hyp_type, guest_uuid_ini):
    """Try to resolve a guest UUID when it is blank in virtwho.ini.

    Strategy:
      1. For libvirt, ask ``virsh domuuid`` on the hypervisor host.
      2. Fall back to the first guestId reported by virt-who.

    Returns the resolved UUID string, or empty string on failure."""
    import sys

    if not guest_uuid_ini:
        guest_name = hypervisor_handler.guest_name
        if guest_name and hyp_type == "libvirt":
            try:
                _, virsh_uuid = ssh.runcmd(
                    f"virsh -c qemu+ssh://{hypervisor_handler.username}"
                    f"@{hypervisor_handler.server}/system"
                    f" domuuid '{guest_name}' 2>/dev/null"
                )
                if virsh_uuid and virsh_uuid.strip():
                    guest_uuid_ini = virsh_uuid.strip()
                    sys.stderr.write(
                        f"[oneshot-discover] resolved guest_uuid via "
                        f"virsh domuuid: {guest_uuid_ini}\n"
                    )
                    sys.stderr.flush()
            except Exception as virsh_err:
                sys.stderr.write(
                    f"[oneshot-discover] virsh domuuid failed "
                    f"for {guest_name}: {virsh_err}\n"
                )
                sys.stderr.flush()

        if not guest_uuid_ini:
            all_guests = matched_hv.get("guestIds", [])
            if all_guests:
                guest_uuid_ini = all_guests[0].get("guestId", "")
                sys.stderr.write(
                    f"[oneshot-discover] using first guest from "
                    f"hypervisor list: {guest_uuid_ini}\n"
                )
                sys.stderr.flush()

    return guest_uuid_ini or ""


def _oneshot_discover(data):
    """Run ``virt-who -p -d`` on the test host to discover hypervisor identity
    fields at runtime.  This is the universal approach: the test host already
    has network access to the hypervisor, and parsing virt-who's own JSON
    output guarantees test expectations match its runtime behavior (handles
    byte-swapped UUIDs for Hyper-V, correct hostname formats, etc.).

    A temporary config file is written to ``/etc/virt-who.d/``, the oneshot
    is executed, and the file is cleaned up.  Existing configs in that
    directory are preserved."""
    import sys

    mode = hypervisor_handler.type
    hyp_type = HYPERVISOR
    if hyp_type == "ahv":
        mode = "ahv"
    elif hyp_type == "libvirt":
        mode = "libvirt"
    elif hyp_type == "hyperv":
        mode = "hyperv"

    try:
        vw_host = config.virtwho.server
        vw_user = config.virtwho.username
        vw_port = config.virtwho.port or 22
        sys.stderr.write(
            f"[oneshot-discover] connecting to virt-who host "
            f"{vw_user}@{vw_host}:{vw_port} for {hyp_type}\n"
        )
        sys.stderr.flush()
        ssh = SSHConnect(
            host=vw_host,
            user=vw_user,
            pwd=config.virtwho.password,
            port=vw_port,
        )

        conf_path = "/etc/virt-who.d/_oneshot_discover.conf"
        owner = register_handler.default_org
        server = hypervisor_handler.server
        if hyp_type == "libvirt" and "://" not in server:
            server = f"qemu+ssh://{hypervisor_handler.username}@{server}/system"
        conf_lines = [
            "[oneshot-discover]",
            f"type={mode}",
            "hypervisor_id=uuid",
            f"server={server}",
            f"username={hypervisor_handler.username}",
            f"password={hypervisor_handler.password}",
            f"owner={owner}",
        ]
        sys.stderr.write(
            f"[oneshot-discover] writing config: {conf_path}\n"
            + "\n".join(conf_lines)
            + "\n"
        )
        sys.stderr.flush()
        ssh.runcmd(
            f"cat > {conf_path} << 'EOCONF'\n" + "\n".join(conf_lines) + "\nEOCONF"
        )

        sys.stderr.write("[oneshot-discover] running virt-who -p -d ...\n")
        sys.stderr.flush()
        _, output = ssh.runcmd(
            f"virt-who -p -d -c {conf_path} 2>/tmp/_oneshot_discover.log"
        )
        ssh.runcmd(f"rm -f {conf_path}")
        sys.stderr.write(
            f"[oneshot-discover] raw output length: {len(output) if output else 0}\n"
        )
        sys.stderr.flush()

        if not output or not output.strip():
            _, stderr_log = ssh.runcmd(
                "tail -20 /tmp/_oneshot_discover.log 2>/dev/null"
            )
            logger.warning(
                f"{hyp_type} oneshot-discover: virt-who -p returned no output. "
                f"stderr: {(stderr_log or '').strip()[:500]}"
            )
            return

        mapping = _parse_oneshot_json(output, hyp_type)
        if not mapping:
            return

        hypervisors = mapping["hypervisors"]
        guest_uuid_ini = data.get("guest_uuid") or hypervisor_handler.guest_uuid
        matched_hv = None
        for hv in hypervisors:
            guests = hv.get("guestIds", [])
            guest_uuids = [g.get("guestId", "").lower() for g in guests]
            if guest_uuid_ini and guest_uuid_ini.lower() in guest_uuids:
                matched_hv = hv
                break
        if not matched_hv:
            matched_hv = hypervisors[0]

        _extract_hv_facts(matched_hv, data)

        guest_uuid_ini = _resolve_guest_uuid(ssh, matched_hv, hyp_type, guest_uuid_ini)

        for guest in matched_hv.get("guestIds", []):
            gid = guest.get("guestId", "")
            if guest_uuid_ini and gid.lower() == guest_uuid_ini.lower():
                data["guest_uuid"] = gid
                break

        logger.info(
            f"{hyp_type} oneshot-discover: "
            f"uuid={data.get('hypervisor_uuid')}, "
            f"hostname={data.get('hypervisor_hostname')}, "
            f"cpu={data.get('cpu')}, version={data.get('version')}, "
            f"cluster={data.get('cluster')}, "
            f"guest_uuid={data.get('guest_uuid')}"
        )

    except Exception as e:
        import traceback

        sys.stderr.write(
            f"[oneshot-discover] FAILED for {hyp_type}: {e}\n{traceback.format_exc()}\n"
        )
        sys.stderr.flush()
        logger.warning(f"{hyp_type} oneshot-discover failed, using INI values: {e}")


@pytest.fixture(scope="session")
def hypervisor_data(ssh_guest):
    """Hypervisor data for testing.

    Starts with values from virtwho.ini, then overrides identity fields
    (uuid, hostname, version, cpu, cluster, guest_uuid) with values
    discovered from the hypervisor's API at runtime.  This avoids stale
    or incorrect INI data causing false test failures."""
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
    elif HYPERVISOR == "kubevirt":
        data["hypervisor_uuid"] = hypervisor_handler.uuid
        data["hypervisor_hostname"] = hypervisor_handler.hostname
        data["type"] = hypervisor_handler.type
        data["version"] = hypervisor_handler.version
        data["cpu"] = hypervisor_handler.cpu
        if not data["hypervisor_uuid"]:
            _kubevirt_discover(data)
    else:
        data["hypervisor_uuid"] = hypervisor_handler.uuid
        data["hypervisor_hostname"] = hypervisor_handler.hostname
        data["type"] = hypervisor_handler.type
        data["version"] = hypervisor_handler.version
        data["cpu"] = hypervisor_handler.cpu

    if HYPERVISOR == "ahv":
        data["cluster"] = hypervisor_handler.cluster
        _oneshot_discover(data)
    elif HYPERVISOR in ("libvirt", "hyperv"):
        _oneshot_discover(data)

    if data.get("guest_uuid") and not hypervisor_handler.guest_uuid:
        hypervisor_handler.guest_uuid = data["guest_uuid"]

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
    proxy["connection_log"] = f"Connection built: http_proxy={good_proxy}"
    proxy["proxy_log"] = f"Using proxy: {good_proxy}"
    proxy["error"] = [
        "Connection refused",
        "Cannot connect to proxy",
        "Connection timed out",
        "Unable to connect",
        "Name or service not known",
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
