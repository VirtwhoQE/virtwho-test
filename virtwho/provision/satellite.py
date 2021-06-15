#!/usr/bin/python

import os
import sys
import argparse
curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(os.path.split(rootPath)[0])

from virtwho.provision import base
from virtwho import logger, FailException
from virtwho.ssh import SSHConnect
from virtwho.register import SubscriptionManager
from virtwho.settings import config


def satellite_deploy(args):
    """
    Deploy satellite by cdn or dogfood with required arguments to.
    Please refer to the README for usage.
    :param args: version, repo and os are required options.
        version: satellite version, such as 6.8, 6.9
        repo: repo resources, such as cdn or dogfood
        os: rhel host, such as RHEL-7.9-20200917.0
    """
    sat_ver = args.version
    sat_repo = args.repo
    rhel_ver = args.os.split('-')[1].split('.')[0]
    host = args.server
    ssh_username = args.ssh_username
    ssh_password = args.ssh_password
    ssh = SSHConnect(host=host,
                     user=ssh_username,
                     pwd=ssh_password)
    admin_username = args.admin_username
    admin_password = args.admin_password
    manifest = args.manifest
    base.system_init(ssh, 'satellite')
    if 'cdn' in sat_repo:
        sm = SubscriptionManager(host=host,
                                 username=ssh_username,
                                 password=ssh_password,
                                 register_type='rhsm_product')
        sm.register()
        sm.attach(pool=config.rhsm_product.employee_sku)
        sm.attach(pool=config.rhsm_product.satellite_sku)
        sm.repo('disable', '*')
        repos = satellite_repos_cdn(rhel_ver, sat_ver)
        sm.repo('enable', repos)
    if 'dogfood' in sat_repo:
        satellite_repo_enable_dogfood(ssh, sat_ver, rhel_ver)
    satellite_pkg_install(ssh)
    satellite_installer(ssh, admin_password)
    satellite_settings(ssh, 'failed_login_attempts_limit', '0')
    satellite_settings(ssh, 'unregister_delete_host', 'true')
    if manifest:
        satellite_manifest_upload(ssh, manifest, admin_username, admin_password)


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
    repos_rhel = base.rhel_repos(rhel_ver)
    return repos_sat + ',' + repos_rhel


def satellite_repo_enable_dogfood(ssh, sat_ver, rhel_ver, repo_type='satellite'):
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
        f'--activationkey '
        f'"{repo_type}-{sat_ver}-qa-rhel{rhel_ver}"'
    )
    if ret == 0:
        ssh.runcmd(f'subscription-manager attach '
                   f'--pool {maintenance_pool}')
        logger.info('Succeeded to enable dogfood repo.')
        return True
    raise FailException('Failed to enable dogfood repo')


def satellite_pkg_install(ssh):
    """
    Run command to install satellite package.
    :param ssh: ssh access to satellite host.
    :return: True or raise Fail.
    """
    # clean yum history and rebuilddb
    ssh.runcmd('rm -f /var/lib/rpm/__db*;'
               'rpm --rebuilddb;'
               'rm -rf /var/lib/yum/history/*.sqlite;'
               'rm -rf /var/cache/yum/*;'
               'yum clean all;'
               'rm -rf /etc/yum.repos.d/beaker*')

    ret, output = ssh.runcmd('yum install -y satellite')
    if ret == 0:
        logger.info(f'Succeeded to install satellite package')
        return True
    raise FailException('Failed to install satellite package')


def satellite_installer(ssh, admin_password):
    """
    Run command to deploy satellite by satellite-installer.
    :param ssh: ssh access to satellite host.
    :param admin_password: password for admin account.
    :return: True or raise Fail
    """
    ret, output = ssh.runcmd(
        f'satellite-installer --scenario satellite '
        f'--disable-system-checks '
        f'--foreman-initial-admin-password={admin_password}'
    )
    if ret == 0:
        logger.info('Succeeded to run satellite-installer')
        return True
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
    if ret == 0:
        logger.info(f'Succeeded to upload manifest for satellite')
    else:
        raise FailException('Failed to upload manifest for satellite')
    ret, _ = ssh.runcmd(f'hammer -u {admin_username} -p {admin_password} '
                        f'subscription refresh-manifest '
                        f'--organization="Default Organization"')
    if ret == 0:
        logger.info('Succeeded to refresh satellite manifest')
    else:
        raise FailException('Failed to refresh satellite manifest')


def satellite_settings(ssh, name, value):
    """
    Update the settings by hammer command.
    :param ssh: ssh access to satellite host.
    :param name: such as unregister_delete_host.
    :param value: the value.
    :return: True or raise Fail.
    """
    ret, output = ssh.runcmd(f'hammer settings set '
                             f'--name={name} '
                             f'--value={value}')
    if ret == 0 and f'Setting [{name}] updated to' in output:
        logger.info(f'Succeeded to set {name}:{value} for satellite')
        return True
    raise FailException(f'Failed to set {name}:{value} for satellite')


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
        help="One of ['6.5', '6.6', '6.7', '6.8', '6.9', '6.10']")
    parser.add_argument(
        '--repo',
        required=True,
        help="One of ['cdn', 'dogfood']")
    parser.add_argument(
        '--os',
        required=True,
        help='such as: RHEL-7.9-20200917.0, RHEL-8.0-20181005.1')
    parser.add_argument(
        '--server',
        default=config.satellite.server,
        required=False,
        help='The server hostname or ip to deploy satellite, '
             'default to the [satellite]:server in virtwho.ini')
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
        default=config.satellite.ssh_username,
        required=False,
        help='Account name for the satellite administrator, '
             'default to the [satellite]:username in virtwho.ini')
    parser.add_argument(
        '--admin-password',
        default=config.satellite.ssh_password,
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
