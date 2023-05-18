import argparse
import os
import sys

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from virtwho import FailException
from virtwho.base import system_init
from virtwho.ssh import SSHConnect
from virtwho.register import SubscriptionManager
from virtwho.settings import config


def satellite_deploy(args):
    """
    Deploy satellite server by cdn or dogfood with required arguments.
    Please refer to the README for usage.
    """
    sat_ver = args.version
    sat_repo = args.repo
    rhel_ver = args.rhel_compose.split("-")[1].split(".")[0]
    ssh = SSHConnect(host=args.server, user=args.ssh_username, pwd=args.ssh_password)
    system_init(ssh, "satellite")

    # Enable repos of cnd or dogfood
    if "cdn" in sat_repo:
        sm = SubscriptionManager(
            host=args.server,
            username=args.ssh_username,
            password=args.ssh_password,
            register_type="rhsm",
        )
        satellite_repo_enable_cdn(sm, ssh, rhel_ver, sat_ver)
    if "dogfood" in sat_repo:
        satellite_repo_enable_dogfood(ssh, rhel_ver, sat_ver)
    if "repo" in sat_repo:
        sm = SubscriptionManager(
            host=args.server,
            username=args.ssh_username,
            password=args.ssh_password,
            register_type="rhsm",
        )
        satellite_repo_enable(sm, ssh, rhel_ver, sat_ver)

    # Install satellite
    satellite_pkg_install(ssh)
    satellite_installer(ssh, args.admin_password, sat_ver)


def satellite_repo_enable_cdn(sm, ssh, rhel_ver, sat_ver):
    """
    Enable satellite related repos from cnd content
    :param ssh: ssh access to satellite host.
    :param sm: subscription-manager instance
    :param rhel_ver: rhel version, such as 6, 7, 8
    :param sat_ver: satellite version, such as 6.13, 6.12
    """
    sm.unregister()
    sm.register()
    employee_sku_pool = sm.available(config.sku.employee, "Physical")["pool_id"]
    satellite_sku_pool = sm.available(config.sku.satellite, "Physical")["pool_id"]
    sm.attach(pool=employee_sku_pool)
    sm.attach(pool=satellite_sku_pool)
    sm.repo("disable", "*")
    sm.repo("enable", satellite_repos_cdn(rhel_ver, sat_ver))
    if rhel_ver == "8":
        ssh.runcmd(f"dnf -y module enable satellite:el{rhel_ver}")


def satellite_repo_enable(sm, ssh, rhel_ver, sat_ver):
    """
    Enable the required repos for installing satellite that is still
    in development.
    :param sm: subscription-manager instance
    :param ssh: ssh access to satellite host.
    :param sat_ver: satellite version, such as 6.13, 6.12.
    :param rhel_ver: rhel version, such as 6, 7, 8.
    :return: True or raise Fail.
    """
    sm.register()
    employee_sku_pool = sm.available(config.sku.employee, "Physical")["pool_id"]
    sm.attach(pool=employee_sku_pool)
    sm.repo("disable", "*")
    if rhel_ver == "8":
        sm.repo("enable", f"rhel-{rhel_ver}-for-x86_64-baseos-rpms")
        sm.repo("enable", f"rhel-{rhel_ver}-for-x86_64-appstream-rpms")
    elif rhel_ver == "7":
        sm.repo("enable", f"rhel-{rhel_ver}-server-rpms")
        sm.repo("enable", f"rhel-server-rhscl-{rhel_ver}-rpms")
        sm.repo("enable", f"rhel-{rhel_ver}-server-ansible-2.9-rpms")

    ssh.runcmd(
        "curl -o /etc/pki/ca-trust/source/anchors/satellite-sat-engineering-ca.crt "
        "http://satellite.sat.engineering.redhat.com/pub/katello-server-ca.crt; "
        "update-ca-trust"
    )

    ret, _ = ssh.runcmd(
        f"curl -o /etc/yum.repos.d/satellite-capsule.repo "
        f"http://ohsnap.sat.engineering.redhat.com/api/releases/"
        f"{sat_ver}.0/el{rhel_ver}/satellite/repo_file"
    )

    if ret == 0:
        if rhel_ver == "8":
            ssh.runcmd(f"dnf -y module enable satellite:el{rhel_ver}")
        return True
    raise FailException("Failed to enable repo.")


def satellite_repo_enable_dogfood(ssh, rhel_ver, sat_ver, repo_type="satellite"):
    """
    Enable the required repos for installing satellite that is still
    in development.
    :param ssh: ssh access to satellite host.
    :param sat_ver: satellite version, such as 6.13, 6.12.
    :param rhel_ver: rhel version, such as 6, 7, 8.
    :param repo_type: satellite, capsule or satellite-tools.
    :return: True or raise Fail.
    """
    maintenance_pool = "8a88800f5ca45116015cc807610319ed"
    dogfood = config.satellite.dogfood
    org = "Sat6-CI"
    ssh.runcmd("subscription-manager unregister;" "subscription-manager clean")
    ssh.runcmd("rpm -qa |" "grep katello-ca-consumer |" "xargs rpm -e |" "sort")
    ssh.runcmd(f"yum -y localinstall {dogfood}")
    ret, _ = ssh.runcmd(
        f"subscription-manager register "
        f"--org {org} "
        f'--activationkey "{repo_type}-{sat_ver}-qa-rhel{rhel_ver}"'
    )
    if ret == 0:
        ssh.runcmd(f"subscription-manager attach " f"--pool {maintenance_pool}")
        return True
    raise FailException("Failed to enable dogfood repo.")


def satellite_repos_cdn(rhel_ver, sat_ver):
    """
    Gather all required repos for installing released satellite from cdn.
    :param rhel_ver: rhel version, such as 6, 7, 8.
    :param sat_ver: satellite version, such as 6.13, 6.12
    :return: A string with comma to separate repos.
    """
    repos_sat = (
        f"rhel-{rhel_ver}-server-satellite-maintenance-6-rpms,"
        f"rhel-{rhel_ver}-server-satellite-{sat_ver}-rpms,"
        f"rhel-{rhel_ver}-server-ansible-2.9-rpms"
    )
    repos_rhel = (
        f"rhel-{rhel_ver}-server-rpms,"
        f"rhel-{rhel_ver}-server-optional-rpms,"
        f"rhel-{rhel_ver}-server-extras-rpms,"
        f"rhel-server-rhscl-{rhel_ver}-rpms"
    )
    if rhel_ver == "8":
        repos_sat = (
            f"satellite-{sat_ver}-for-rhel-{rhel_ver}-x86_64-rpms,"
            f"satellite-maintenance-{sat_ver}-for-rhel-{rhel_ver}-x86_64-rpms"
        )
        repos_rhel = (
            f"rhel-{rhel_ver}-for-x86_64-baseos-rpms,"
            f"rhel-{rhel_ver}-for-x86_64-appstream-rpms"
        )
    return repos_sat + "," + repos_rhel


def satellite_pkg_install(ssh):
    """
    Run command to install satellite package.
    :param ssh: ssh access to satellite host.
    """
    # clean yum history and rebuilddb
    ssh.runcmd(
        "rm -f /var/lib/rpm/__db*;"
        "rpm --rebuilddb;"
        "rm -rf /var/lib/yum/history/*.sqlite;"
        "rm -rf /var/cache/yum/*;"
        "yum clean all;"
        "rm -rf /etc/yum.repos.d/beaker*"
    )
    ret, output = ssh.runcmd("yum install -y satellite")
    if ret != 0:
        raise FailException("Failed to install satellite package")


def satellite_installer(ssh, admin_password, sat_ver):
    """
    Run command to deploy satellite by satellite-installer.
    :param ssh: ssh access to satellite host.
    :param admin_password: password for admin account.
    :param sat_ver: satellite version, such as 6.13, 6.12.
    """
    cmd = (
        f"satellite-installer --scenario satellite "
        f"--disable-system-checks "
        f"--foreman-initial-admin-password={admin_password}"
    )
    if sat_ver >= "6.13":
        cmd = (
            f"satellite-installer --scenario satellite "
            f"--tuning development "
            f"--foreman-initial-admin-password={admin_password}"
        )
    ret, output = ssh.runcmd(cmd)
    if ret != 0:
        raise FailException("Failed to run satellite-installer")


def satellite_arguments_parser():
    """
    Parse and convert the arguments from command line to parameters
    for function using, and generate help and usage messages for
    each arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--version", required=True, help="Satellite version, such as '6.13', '6.12'"
    )
    parser.add_argument(
        "--repo", required=True, help="One of ['cdn', 'dogfood', 'repo']"
    )
    parser.add_argument(
        "--rhel-compose",
        required=True,
        help="such as: RHEL-7.9-20200917.0, RHEL-8.0-20181005.1",
    )
    parser.add_argument(
        "--server", required=True, help="The server ip/fqdn to deploy satellite"
    )
    parser.add_argument(
        "--ssh-username",
        default=config.satellite.ssh_username,
        required=False,
        help="Username to access the server, "
        "default to the [satellite]:ssh_username in virtwho.ini",
    )
    parser.add_argument(
        "--ssh-password",
        default=config.satellite.ssh_password,
        required=False,
        help="Password to access the server, "
        "default to the [satellite]:ssh_password in virtwho.ini",
    )
    parser.add_argument(
        "--admin-username",
        default=config.satellite.username,
        required=False,
        help="Account name for the satellite administrator, "
        "default to the [satellite]:username in virtwho.ini",
    )
    parser.add_argument(
        "--admin-password",
        default=config.satellite.password,
        required=False,
        help="Account password for the satellite administrator, "
        "default to the [satellite]:password in virtwho.ini",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = satellite_arguments_parser()
    satellite_deploy(args)
