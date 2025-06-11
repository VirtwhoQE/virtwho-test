import os
import argparse
import sys
import time

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(os.path.split(rootPath)[0])

from virtwho import logger, FailException
from virtwho.settings import config
from virtwho.ssh import SSHConnect
from virtwho.base import ssh_connect, rhel_compose_repo, system_init, rhel_version
from virtwho.base import url_validation, url_file_download, hostname_get
from virtwho.base import ipaddr_get, random_string
from utils.parse_ci_message import umb_ci_message_parser
from utils.beaker import install_host_by_beaker
from utils.properties_update import virtwho_ini_props_update
from hypervisor.virt.libvirt.libvirtcli import LibvirtCLI


def provision_virtwho_host(args):
    """
    Configure virt-who host for an existing server or a new one installed
    by beaker. Please refer to the provision/README for usage.
    """
    logger.info("+++ Start to deploy the virt-who host +++")

    virtwho_ini_props = dict()
    # Parse CI_MESSAGE for gating test
    if args.gating_msg:
        msg = umb_ci_message_parser(args)
        args.virtwho_pkg_url = msg["pkg_url"]
        gating_stable_server = config.gating.host_el9
        if "el8" in msg["pkg_nvr"]:
            gating_stable_server = config.gating.host_el8
        if "el10" in msg["pkg_nvr"]:
            gating_stable_server = config.gating.host_el10
        ssh_gating_server = SSHConnect(
            host=gating_stable_server,
            user=args.username,
            pwd=args.password,
        )
        if ssh_connect(ssh_gating_server):
            args.server = gating_stable_server

        if not args.distro:
            args.distro = rhel_latest_compose(msg["rhel_release"])

        virtwho_ini_props["gating"] = {
            "package_nvr": msg["pkg_nvr"],
            "build_id": str(msg["build_id"]),
            "task_id": str(msg["task_id"]),
            "owner_name": str(msg["owner_name"]),
            "source": msg["source"],
        }

    # Deploy a new host by beaker if no server provided
    if not args.server:
        beaker_args_define(args)
        args.server = install_host_by_beaker(args)
        args.username = config.beaker.default_username
        args.password = config.beaker.default_password

    ssh_host = SSHConnect(host=args.server, user=args.username, pwd=args.password)
    # Initially setup the rhel virt-who host
    if "RHEL" in args.distro:
        ssh_host.runcmd(cmd="rm -f /etc/yum.repos.d/*.repo")
        rhel_compose_repo(
            ssh=ssh_host,
            repo_file="/etc/yum.repos.d/compose.repo",
            compose_id=args.distro,
            compose_path=args.rhel_compose_path,
        )
    # temporary hack
    ssh_host.runcmd(
        "rm -rf /var/lib/rpm/.rpm.lock; rm -rf /usr/lib/sysimage/rpm/.rpm.lock; pkill yum"
    )
    ssh_host.runcmd("yum install -y subscription-manager expect net-tools wget")
    ssh_host.runcmd(cmd="subscription-manager unregister; subscription-manager clean")
    rhsm_conf_backup(ssh_host)
    system_init(ssh_host, "virtwho")
    virtwho_pkg = virtwho_install(ssh_host, args.virtwho_pkg_url)

    # Configure the virt-who host for remote libvirt mode
    if config.job.hypervisor == "libvirt" or "libvirt" in config.job.multi_hypervisors:
        libvirt_access_no_password(ssh_host)

    # Configure the virt-who host for kubevirt mode
    if (
        config.job.hypervisor == "kubevirt"
        or "kubevirt" in config.job.multi_hypervisors
    ):
        kubevirt_config_file(ssh_host)

    # Configure the virt-who host for local libvirt mode
    if config.job.hypervisor == "local" or "local" in config.job.multi_hypervisors:
        libvirt_pkg_install(ssh_host)
        libvirt_bridge_setup("br0", ssh_host)
        guest_data = local_mode_guest_add(ssh_host)
        virtwho_ini_props["local"] = {
            "server": args.server,
            "username": args.username,
            "password": args.password,
            "hostname": hostname_get(ssh_host),
            "uuid": guest_data["host_uuid"],
            "guest_ip": guest_data["guest_ip"],
            "guest_uuid": guest_data["guest_uuid"],
        }

    # Update the virtwho.ini properties
    virtwho_ini_props["job"] = {
        "rhel_compose": args.distro,
        "rhel_compose_path": args.rhel_compose_path,
    }
    virtwho_ini_props["virtwho"] = {
        "server": args.server,
        "username": args.username,
        "password": args.password,
        "package": virtwho_pkg,
    }
    for args.section, data in virtwho_ini_props.items():
        for args.option, args.value in data.items():
            virtwho_ini_props_update(args)

    logger.info(
        f"+++ Suceeded to deploy the virt-who host " f"{args.distro}/{args.server} +++"
    )


def rhel_latest_compose(rhel_release):
    """
    Use the latest rhel compose for gating test if no rhel_compose provid.
    """
    version = "10"
    if "rhel-8" in rhel_release:
        version = "8"
    if "rhel-9" in rhel_release:
        version = "9"
    latest_compose_url = (
        f"{config.virtwho.repo}/rhel-{version}/nightly/"
        f"RHEL-{version}/latest-RHEL-{version}/COMPOSE_ID"
    )
    if version == "10":
        latest_compose_url = (
            f"{config.virtwho.repo}/rhel-{version}/nightly/"
            f"RHEL-{version}-Public-Beta/latest-RHEL-{version}/COMPOSE_ID"
        )
    latest_compose_id = os.popen(f"curl -s -k -L {latest_compose_url}").read().strip()
    return latest_compose_id


def beaker_args_define(args):
    """
    Define the necessary args to call the utils/beaker.by
    :param args: arguments to define
    """
    args.variant = "BaseOS"
    if "RHEL-7" in args.distro or "Fedora" in args.distro:
        args.variant = "Server"
    args.arch = "x86_64"
    args.job_group = None  # "virt-who-ci-server-group"
    args.host = args.beaker_host
    args.host_type = "physical"
    args.host_require = None
    args.reserve_duration = None


def virtwho_install(ssh, url=None):
    """
    Install virt-who package, default is from repository,
    or gating msg, or brew url.
    :param ssh: ssh access of virt-who host
    :param url: url link of virt-who package from brew
    """
    rhel_ver = rhel_version(ssh)
    cmd = (
        "rm -rf /var/lib/rpm/__db*;"
        "mv /var/lib/rpm /var/lib/rpm.old;"
        "rpm --initdb;"
        "rm -rf /var/lib/rpm;"
        "rm -rf /usr/lib/sysimage/rpm/.rpm.lock;"
        "mv /var/lib/rpm.old /var/lib/rpm;"
        "rm -rf /var/lib/yum/history/*.sqlite;"
        "rpm -v --rebuilddb"
    )
    if rhel_ver == "6":
        cmd = "dbus-uuidgen > /var/lib/dbus/machine-id"
    if rhel_ver == "8":
        cmd = "localectl set-locale en_US.utf8; source /etc/profile.d/lang.sh"
    ssh.runcmd(cmd)
    if url:
        virtwho_install_by_url(ssh, url)
    else:
        ssh.runcmd("yum remove -y virt-who;" "yum install -y virt-who")
    _, output = ssh.runcmd("rpm -qa virt-who")
    if "virt-who" not in output:
        raise FailException("Failed to install virt-who package")
    logger.info(f"Succeeded to install {output.strip()}")
    return output.strip()


def virtwho_install_by_url(ssh, url):
    """
    Install virt-who package by a designated url.
    :param ssh: ssh access of virt-who host
    :param url: virt-who package url, whick can be local installed.
    """
    if not url_validation(url):
        raise FailException(f"package {url} is not available")
    _, output = ssh.runcmd("grep 'sslverify=false' /etc/yum.conf")
    if not output:
        ssh.runcmd("echo 'sslverify=false' >> /etc/yum.conf")
    ssh.runcmd("rm -rf /var/cache/yum/;" "yum clean all;" "yum remove -y virt-who")
    ssh.runcmd(f"yum localinstall -y {url} --allowerasing")


def rhsm_conf_backup(ssh):
    """
    Backup the rhsm.conf to /backup
    :param ssh: ssh access of virt-who host
    """
    ret, output = ssh.runcmd("ls /backup/rhsm.conf")
    if ret != 0 or "No such file or directory" in output:
        ssh.runcmd(
            "rm -rf /backup/;" "mkdir -p /backup/;" "cp /etc/rhsm/rhsm.conf /backup/"
        )


def libvirt_access_no_password(ssh):
    """
    Configure virt-who host accessing remote libvirt host by ssh
    without password.
    :param ssh: ssh access of virt-who host
    """
    ssh_libvirt = SSHConnect(
        host=config.libvirt.server,
        user=config.libvirt.username,
        pwd=config.libvirt.password,
    )
    ssh.runcmd('echo -e "\n" | ' 'ssh-keygen -N "" &> /dev/null')
    ret, output = ssh.runcmd("cat ~/.ssh/*.pub")
    if ret != 0 or output is None:
        raise FailException("Failed to create ssh key")
    ssh_libvirt.runcmd(f"mkdir ~/.ssh/;echo '{output}' >> ~/.ssh/authorized_keys")
    ret, _ = ssh.runcmd(
        f"ssh-keyscan -p 22 {config.libvirt.server} >> ~/.ssh/known_hosts"
    )
    if ret != 0:
        raise FailException("Failed to configure access libvirt without passwd")


def kubevirt_config_file(ssh):
    """
    Download the both config_file and config_file_no_cert.
    :param ssh: ssh access of virt-who host.
    """
    url_file_download(ssh, config.kubevirt.config_file, config.kubevirt.config_url)
    url_file_download(
        ssh, config.kubevirt.config_file_no_cert, config.kubevirt.config_url_no_cert
    )


def local_mode_guest_add(ssh):
    """
    Add rhel guest for the local mode.
    :param ssh: ssh access of virt-who host.
    Return the guest data dic.
    """
    server_ip = ipaddr_get(ssh)
    local = LibvirtCLI(server_ip, args.username, args.password)
    guest_name = config.local.guest_name
    if not local.guest_exist(guest_name):
        local.guest_add(
            guest_name=guest_name,
            image_url=config.local.guest_image_url,
            xml_url=config.local.guest_xml_url,
            image_path=config.local.guest_image_path,
            xml_path=config.local.guest_xml_path,
        )
    else:
        local.guest_start(guest_name)
    for i in range(10):
        time.sleep(30)
        guest_ip = local.guest_ip(guest_name)
        if guest_ip:
            logger.error(f"timeout to get guest_ip for guest_name {guest_name}")
            break
    guest_info = local.guest_search(guest_name)
    ssh_guest = SSHConnect(
        host=guest_info["guest_ip"],
        user=config.local.guest_username,
        pwd=config.local.guest_password,
    )
    hostname = hostname_get(ssh_guest)
    if (
        "localhost" in hostname
        or "unused" in hostname
        or "openshift" in hostname
        or hostname is None
    ):
        hostname = "local-libvirt-vm-" + random_string()
        ssh_guest.runcmd(f"hostnamectl set-hostname {hostname}")
        ssh_guest.runcmd(f"echo '{hostname}' > /etc/hostname")
    return guest_info


def libvirt_pkg_install(ssh):
    """
    Install libvirt related packages.
    :param ssh: ssh access of virt-who host.
    """
    package = "nmap iproute rpcbind libvirt*"
    ssh.runcmd(f"yum clean all; yum install -y {package}")
    ret, _ = ssh.runcmd("systemctl restart libvirtd;systemctl enable libvirtd")
    if ret == 0:
        logger.info("Succeeded to start libvirtd service")
    else:
        raise FailException("Failed to start libvirtd service")


def libvirt_bridge_setup(bridge_name, ssh):
    """
    Setup bridge for libvirt host
    :param bridge_name: bridge name.
    :param ssh: ssh access of virt-who host.
    """
    local_file = os.path.join(rootPath, "../utils/libvirt_bridge_setup.sh")
    remote_file = "/tmp/libvirt_bridge_setup.sh"
    ssh.put_file(local_file, remote_file)
    _, output = ssh.runcmd(f"sh {remote_file} -b {bridge_name}")
    logger.info(output)


def virtwho_arguments_parser():
    """
    Parse and convert the arguments from command line to parameters
    for function using, and generate help and usage messages for
    each arguments.
    """

    def value_to_boolean(value):
        return (
            (value is not None)
            and value.lower()
            in ["yes", "y", "1", "true", "t", "ok", "enabled", "enable"]
        ) or False

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--distro",
        required=False,
        default=config.job.rhel_compose,
        help="Such as: RHEL-8.5.0-20211013.2, optional for gating test.",
    )
    parser.add_argument(
        "--rhel-compose-path",
        required=False,
        default=config.job.rhel_compose_path,
        help="Such as http://download.devel.redhat.com/rhel-9/nightly/RHEL-9. "
        "If leave it None, will use the specified path in code.",
    )
    parser.add_argument(
        "--fips",
        required=False,
        action=argparse.BooleanOptionalAction,
        default=False,
        help="--fips/--no-fips: a machine about to create should complain FIPS standard.",
    )

    parser.add_argument(
        "--server",
        required=False,
        default=config.virtwho.server,
        help="IP/fqdn of virt-who host, will install one by beaker if not provide.",
    )
    parser.add_argument(
        "--username",
        required=False,
        default=config.virtwho.username,
        help="Username to access the server, "
        "default to the [virtwho]:username in virtwho.ini",
    )
    parser.add_argument(
        "--password",
        required=False,
        default=config.virtwho.password,
        help="Password to access the server, "
        "default to the [virtwho]:password in virtwho.ini",
    )
    parser.add_argument(
        "--beaker-host",
        required=False,
        default="",
        help="Define/filter system as hostrequire."
        "Such as: %hp-z220%, %hp-dl360g9-08-vm%, %dell-per740-69-vm%",
    )
    parser.add_argument(
        "--gating-msg", default="", required=False, help="Gating msg from UMB"
    )
    parser.add_argument(
        "--virtwho-pkg-url",
        default="",
        required=False,
        help="Brew url of virt-who package for localinstall.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = virtwho_arguments_parser()
    provision_virtwho_host(args)
