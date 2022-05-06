#!/usr/bin/python
import argparse
import os
import sys

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from virtwho import logger, FailException
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
    rhel_ver = args.rhel_compose.split('-')[1].split('.')[0]
    ssh = SSHConnect(host=args.server,
                     user=args.ssh_username,
                     pwd=args.ssh_password)
    system_init(ssh, 'satellite')

    # Enable repos of cnd or dogfood
    if 'cdn' in sat_repo:
        sm = SubscriptionManager(host=args.server,
                                 username=args.ssh_username,
                                 password=args.ssh_password,
                                 register_type='rhsm')
        satellite_repo_enable_cdn(sm, rhel_ver, sat_ver)
    if 'dogfood' in sat_repo:
        satellite_repo_enable_dogfood(ssh, rhel_ver, sat_ver)

    # Install satellite
    satellite_pkg_install(ssh)
    satellite_installer(ssh, args.admin_password)

    # Upload manifest as requirement
    if args.manifest:
        satellite_manifest_upload(
            ssh, args.manifest, args.admin_username, args.admin_password
        )
    logger.info(f'Succeeded to deploy satellite ({sat_ver})')


def satellite_repo_enable_cdn(sm, rhel_ver, sat_ver):
    """
    Enable satellite related repos from cnd content
    :param sm: subscription-manager instance
    :param rhel_ver: rhel version, such as 6, 7
    :param sat_ver: satellite version, such as 6.9, 6.10
    """
    sm.register()
    employee_sku_pool = sm.available(
        config.sku.employee, 'Physical')['pool_id']
    satellite_sku_pool = sm.available(
        config.sku.satellite, 'Physical')['pool_id']
    sm.attach(pool=employee_sku_pool)
    sm.attach(pool=satellite_sku_pool)
    sm.repo('disable', '*')
    sm.repo('enable', satellite_repos_cdn(rhel_ver, sat_ver))


def satellite_repo_enable_dogfood(ssh, rhel_ver, sat_ver,
                                  repo_type='satellite'):
    """
    Enable the required repos for installing satellite that is still
    in development.
    :param ssh: ssh access to satellite host.
    :param sat_ver: satellite version, such as 6.8, 6.9.
    :param rhel_ver: rhel version, such as 6, 7, 8.
    :param repo_type: satellite, capsule or satellite-tools.
    :return: True or raise Fail.
    """
    maintenance_pool = '8a88800f5ca45116015cc807610319ed'
    dogfood = config.satellite.dogfood
    org = 'Sat6-CI'
    ssh.runcmd('subscription-manager unregister;'
               'subscription-manager clean')
    ssh.runcmd('rpm -qa |'
               'grep katello-ca-consumer |'
               'xargs rpm -e |'
               'sort')
    ssh.runcmd(f'yum -y localinstall {dogfood}')
    ret, _ = ssh.runcmd(
        f'subscription-manager register '
        f'--org {org} '
        f'--activationkey "{repo_type}-{sat_ver}-qa-rhel{rhel_ver}"'
    )
    if ret == 0:
        ssh.runcmd(f'subscription-manager attach '
                   f'--pool {maintenance_pool}')
        return True
    raise FailException('Failed to enable dogfood repo.')


def satellite_repos_cdn(rhel_ver, sat_ver):
    """
    Gather all required repos for installing released satellite from cdn.
    :param rhel_ver: rhel version, such as 6, 7, 8.
    :param sat_ver: satellite version, such as 6.8, 6.9
    :return: A string with comma to separate repos.
    """
    repos_sat = (f'rhel-{rhel_ver}-server-satellite-maintenance-6-rpms,'
                 f'rhel-{rhel_ver}-server-satellite-capsule-{sat_ver}-rpms,'
                 f'rhel-{rhel_ver}-server-satellite-{sat_ver}-rpms,'
                 f'rhel-{rhel_ver}-server-satellite-tools-{sat_ver}-rpms,'
                 f'rhel-{rhel_ver}-server-ansible-2.9-rpms')
    repos_rhel = (f'rhel-{rhel_ver}-server-rpms,'
                  f'rhel-{rhel_ver}-server-optional-rpms,'
                  f'rhel-{rhel_ver}-server-extras-rpms,'
                  f'rhel-server-rhscl-{rhel_ver}-rpms')
    return repos_sat + ',' + repos_rhel


def satellite_pkg_install(ssh):
    """
    Run command to install satellite package.
    :param ssh: ssh access to satellite host.
    """
    # clean yum history and rebuilddb
    ssh.runcmd('rm -f /var/lib/rpm/__db*;'
               'rpm --rebuilddb;'
               'rm -rf /var/lib/yum/history/*.sqlite;'
               'rm -rf /var/cache/yum/*;'
               'yum clean all;'
               'rm -rf /etc/yum.repos.d/beaker*')
    ret, output = ssh.runcmd('yum install -y satellite')
    if ret != 0:
        raise FailException('Failed to install satellite package')


def satellite_installer(ssh, admin_password):
    """
    Run command to deploy satellite by satellite-installer.
    :param ssh: ssh access to satellite host.
    :param admin_password: password for admin account.
    """
    ret, output = ssh.runcmd(
        f'satellite-installer --scenario satellite '
        f'--disable-system-checks '
        f'--foreman-initial-admin-password={admin_password}'
    )
    if ret != 0:
        raise FailException('Failed to run satellite-installer')


def satellite_manifest_upload(ssh, url, admin_username, admin_password):
    """
    Upload manifest to satellite by hammer command.
    :param ssh: ssh access to satellite host.
    :param url: manifest url
    :param admin_username: username of admin account.
    :param admin_password: password of admin account.
    """
    path = "/tmp/manifest"
    ssh.runcmd(f'rm -rf {path}; mkdir -p {path}')
    ssh.runcmd(f'wget {url} -P {path}')
    ret, output = ssh.runcmd(f'ls {path}')
    if output:
        filename = f'{path}/{output.strip()}'
    else:
        raise FailException('No manifest file found')
    ret, _ = ssh.runcmd(f'hammer -u {admin_username} -p {admin_password} '
                        f'subscription upload '
                        f'--organization-label Default_Organization '
                        f'--file {filename}')
    if ret != 0:
        raise FailException('Failed to upload manifest for satellite')
    # ret, _ = ssh.runcmd(f'hammer -u {admin_username} -p {admin_password} '
    #                     f'subscription refresh-manifest '
    #                     f'--organization="Default Organization"')
    # if ret != 0:
    #     raise FailException('Failed to refresh satellite manifest')


def satellite_arguments_parser():
    """
    Parse and convert the arguments from command line to parameters
    for function using, and generate help and usage messages for
    each arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--version',
        required=True,
        help="Satellite version, such as '6.9', '6.10'")
    parser.add_argument(
        '--repo',
        required=True,
        help="One of ['cdn', 'dogfood']")
    parser.add_argument(
        '--rhel-compose',
        required=True,
        help='such as: RHEL-7.9-20200917.0, RHEL-8.0-20181005.1')
    parser.add_argument(
        '--server',
        required=True,
        help='The server ip/fqdn to deploy satellite')
    parser.add_argument(
        '--ssh-username',
        default=config.satellite.ssh_username,
        required=False,
        help='Username to access the server, '
             'default to the [satellite]:ssh_username in virtwho.ini')
    parser.add_argument(
        '--ssh-password',
        default=config.satellite.ssh_password,
        required=False,
        help='Password to access the server, '
             'default to the [satellite]:ssh_password in virtwho.ini')
    parser.add_argument(
        '--admin-username',
        default=config.satellite.username,
        required=False,
        help='Account name for the satellite administrator, '
             'default to the [satellite]:username in virtwho.ini')
    parser.add_argument(
        '--admin-password',
        default=config.satellite.password,
        required=False,
        help='Account password for the satellite administrator, '
             'default to the [satellite]:password in virtwho.ini')
    parser.add_argument(
        '--manifest',
        default=config.satellite.manifest,
        required=False,
        help='Manifest url to upload after complete deploying satellite, '
             'default to the [satellite]:manifest in virtwho.ini')
    return parser.parse_args()


if __name__ == "__main__":
    args = satellite_arguments_parser()
    satellite_deploy(args)
