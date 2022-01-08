#!/usr/bin/python

import os
import sys
import argparse

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(os.path.split(rootPath)[0])

from virtwho import logger, FailException
from utils.beaker import install_rhel_by_beaker
from utils.satellite import satellite_deploy
from virtwho.ssh import SSHConnect
from virtwho.settings import config


def satellite_deploy_for_virtwho(args):
    """
    Deploy satellite by cdn or dogfood with required arguments to.
    Please refer to the README for usage.
    :param args: version, repo, os and server are required options.
        version: satellite version, such as 6.8, 6.9
        repo: repo resources, cdn or dogfood
        os: rhel host, such as RHEL-7.9-20200917.0
        server: server FQDN or IP
    """
    satellite = args.satellite.split('-')
    args.rhel_compose = rhel_compose_for_satellite(satellite[2])
    args.version = satellite[0]
    args.repo = satellite[1]

    if not args.server:
        beaker_args_define(args)
        args.server = install_rhel_by_beaker(args)
        args.ssh_username = config.beaker.default_username
        args.ssh_password = config.beaker.default_password
    ssh_host = SSHConnect(
        host=args.server,
        user=args.ssh_username,
        pwd=args.ssh_password
    )

    satellite_deploy(args)
    satellite_settings(ssh_host, 'failed_login_attempts_limit', '0')
    satellite_settings(ssh_host, 'unregister_delete_host', 'true')
    config.update('satellite', 'server', args.server)
    config.update('satellite', 'username', args.admin_username)
    config.update('satellite', 'password', args.admin_password)
    config.update('satellite', 'ssh_username', args.ssh_username)
    config.update('satellite', 'ssh_password', args.ssh_password)


def rhel_compose_for_satellite(rhel_version):
    compose = ''
    if 'rhel7' in rhel_version:
        compose = 'RHEL-7.9-20200917.0'
    if 'rhel8' in rhel_version:
        compose = 'RHEL-8.5.0-20211013.2'
    return compose


def beaker_args_define(args):
    """
    Define the necessary args to call the utils/beaker.by
    :param args: arguments to define
    """
    args.arch = 'x86_64'
    args.variant = 'BaseOS'
    if 'RHEL-7' in args.rhel_compose:
        args.variant = 'Server'
    args.job_group = 'virt-who-ci-server-group'
    args.host = '%ent-02-vm%'
    args.host_type = None
    args.host_require = None


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


def virtwho_satellite_arguments_parser():
    """
    Parse and convert the arguments from command line to parameters
    for function using, and generate help and usage messages for
    each arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--satellite',
        required=True,
        help='Such as: 6.10-cdn-rhel7, 6.9-dogfood-rhel7')
    parser.add_argument(
        '--server',
        default=config.satellite.server,
        required=False,
        help='ip/fqdn, default to the [satellite]:server in virtwho.ini, '
             'will install a new system if no server provide.')
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
    args = virtwho_satellite_arguments_parser()
    satellite_deploy_for_virtwho(args)
