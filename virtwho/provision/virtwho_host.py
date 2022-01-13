#!/usr/bin/python
import os
import sys
import argparse

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(os.path.split(rootPath)[0])

from virtwho import logger, FailException
from virtwho.settings import config
from virtwho.ssh import SSHConnect
from virtwho import base
from utils.beaker import install_rhel_by_beaker


def provision_virtwho_host(args):
    """
    Configure virt-who host for an existing server or a new one installed by beaker.
    Please refer to the provision/README for usage.
    """
    if args.gating_msg:
        msg = base.gating_msg_parser(args.gating_msg)
        args.virtwho_pkg_url = msg['pkg_url']
        if not args.rhel_compose:
            args.rhel_compose = msg['latest_rhel_compose']

    if not args.server:
        beaker_args_define(args)
        args.server = install_rhel_by_beaker(args)
        args.username = config.beaker.default_username
        args.password = config.beaker.default_password
    ssh_host = SSHConnect(
        host=args.server,
        user=args.username,
        pwd=args.password
    )

    base.rhel_compose_repo(
        ssh_host, args.rhel_compose, '/etc/yum.repos.d/compose.repo'
    )
    base.system_init(ssh_host, 'virtwho')
    virtwho_install(ssh_host, args.virtwho_pkg_url)
    if config.job.mode == 'libvirt':
        libvirt_access_no_password(ssh_host)
    if config.job.mode == 'kubevirt':
        kubevirt_config_file(ssh_host)
    config.update('virtwho', 'server', args.server)
    config.update('virtwho', 'username', args.username)
    config.update('virtwho', 'password', args.password)


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
    args.host = args.beaker_host
    args.host_type = None
    args.host_require = None


def virtwho_install(ssh, url=None):
    """
    Install virt-who package, default is from repository,
    or gating msg, or brew url.
    :param ssh: ssh access of virt-who host
    :param url: url link of virt-who package from brew
    """
    rhel_ver = base.rhel_version(ssh)
    cmd = ('rm -rf /var/lib/rpm/__db*;'
           'mv /var/lib/rpm /var/lib/rpm.old;'
           'rpm --initdb;'
           'rm -rf /var/lib/rpm;'
           'mv /var/lib/rpm.old /var/lib/rpm;'
           'rm -rf /var/lib/yum/history/*.sqlite;'
           'rpm -v --rebuilddb')
    if rhel_ver == '6':
        cmd = 'dbus-uuidgen > /var/lib/dbus/machine-id'
    if rhel_ver == '8':
        cmd = 'localectl set-locale en_US.utf8; source /etc/profile.d/lang.sh'
    _, _ = ssh.runcmd(cmd)
    if url:
        virtwho_install_by_url(ssh, url)
    else:
        ssh.runcmd('yum remove -y virt-who;'
                   'yum install -y virt-who')
    _, output = ssh.runcmd('rpm -qa virt-who')
    if 'virt-who' not in output:
        raise FailException('Failed to install virt-who package')
    logger.info(f'Succeeded to install {output.strip()}')


def virtwho_install_by_url(ssh, url):
    """
    Install virt-who package by a designated url.
    :param ssh: ssh access of virt-who host
    :param url: virt-who package url, whick can be local installed.
    """
    if not base.url_validation(url):
        raise FailException(f'package {url} is not available')
    ssh.runcmd('rm -rf /var/cache/yum/;'
               'yum clean all;'
               'yum remove -y virt-who')
    ssh.runcmd(f'yum localinstall -y {url}')


def libvirt_access_no_password(ssh):
    """
    Configure virt-who host accessing remote libvirt host by ssh
    without password.
    :param ssh: ssh access of virt-who host
    """
    ssh_libvirt = SSHConnect(
        host=config.libvirt.server,
        user=config.libvirt.username,
        pwd=config.libvirt.password
    )
    _, _ = ssh.runcmd('echo -e "\n" | '
                      'ssh-keygen -N "" &> /dev/null')
    ret, output = ssh.runcmd('cat ~/.ssh/id_rsa.pub')
    if ret != 0 or output is None:
        raise FailException("Failed to create ssh key")
    _, _ = ssh_libvirt.runcmd(f"mkdir ~/.ssh/;"
                              f"echo '{output}' >> ~/.ssh/authorized_keys")
    ret, _ = ssh.runcmd(f'ssh-keyscan -p 22 {config.libvirt.server} >> '
                        f'~/.ssh/known_hosts')
    if ret != 0:
        raise FailException('Failed to configure access libvirt without passwd')


def kubevirt_config_file(ssh):
    """
    Download the both config_file and config_file_no_cert.
    :param ssh: ssh access of virt-who host.
    """
    base.url_file_download(ssh,
                           config.kubevirt.config_file,
                           config.kubevirt.config_url)
    base.url_file_download(ssh,
                           config.kubevirt.config_file_no_cert,
                           config.kubevirt.config_url_no_cert)


def virtwho_arguments_parser():
    """
    Parse and convert the arguments from command line to parameters
    for function using, and generate help and usage messages for
    each arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--rhel-compose',
        required=False,
        default=None,
        help='Such as: RHEL-8.5.0-20211013.2, optional for gating test.')
    parser.add_argument(
        '--server',
        required=False,
        default=None,
        help='IP/fqdn of virt-who host, '
             'will install one by beaker if not provide.')
    parser.add_argument(
        '--username',
        required=False,
        default=config.virtwho.username,
        help='Username to access the server, '
             'default to the [virtwho]:username in virtwho.ini')
    parser.add_argument(
        '--password',
        required=False,
        default=config.virtwho.password,
        help='Password to access the server, '
             'default to the [virtwho]:password in virtwho.ini')
    parser.add_argument(
        '--beaker-host',
        required=False,
        default=None,
        help='Define/filter system as hostrequire. '
             'Such as: %ent-02-vm%, ent-02-vm-20.lab.eng.nay.redhat.com')
    parser.add_argument(
        '--gating-msg',
        default=None,
        required=False,
        help='Gating msg from UMB')
    parser.add_argument(
        '--virtwho-pkg-url',
        default=None,
        required=False,
        help='Brew url of virt-who package for localinstall.')
    return parser.parse_args()


if __name__ == "__main__":
    args = virtwho_arguments_parser()
    provision_virtwho_host(args)
