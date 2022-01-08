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
from virtwho.provision import base
from utils.beaker import install_rhel_by_beaker


def provision_virtwho_host_by_beaker(args):
    """
    Install rhel by submitting job to beaker with required arguments.
    Please refer to the provision/README for usage.
    :param args:
        rhel_compose: optional for gating test, default using the latest one.
        arch: optional, default using x86_64.
        variant: optional, default using BaseOS for rhel8 and later.
        job_group: optional, associate a group to this job.
        host: optional, define/filter system as hostrequire
        host_type: optional, physical or virtual
        host_require: optional, other hostRequires for job
        gating_msg: optional, install virt-who from gating msg
        brew_url: optional, install virt-who from brew url
    """
    virtwho_pkg = args.brew_url
    if args.gating_msg:
        msg = base.gating_msg_parser(args.gating_msg)
        virtwho_pkg = msg['pkg_url']
        if not args.rhel_compose:
            args.rhel_compose = msg['latest_rhel_compose']
    host = install_rhel_by_beaker(args)
    username = config.beaker.default_username
    password = config.beaker.default_password
    ssh_host = SSHConnect(
        host=host,
        user=username,
        pwd=password
    )
    virtwho_install(ssh_host, virtwho_pkg)
    base.system_init(ssh_host, 'virtwho')

    if config.job.mode == 'libvirt':
        libvirt_access_no_password(ssh_host)
    if config.job.mode == 'kubevirt':
        kubevirt_config_file(ssh_host)

    config.update('virtwho', 'server', host)
    config.update('virtwho', 'username', username)
    config.update('virtwho', 'password', password)


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
        help='Such as: RHEL-8.0-20181005.1, optional for gating test.')
    parser.add_argument(
        '--arch',
        required=False,
        default='x86_64',
        help='One of [x86_64, s390x, ppc64, ppc64le, aarch64]')
    parser.add_argument(
        '--variant',
        required=False,
        default=None,
        help='One of [Server, Client, Workstation, BaseOS]. '
             'Unnecessary for RHEL-8 and later, default using BaseOS.')
    parser.add_argument(
        '--job-group',
        required=False,
        default='virt-who-ci-server-group',
        help='Associate a group to the job')
    parser.add_argument(
        '--host',
        required=False,
        default=None,
        help='Define/filter system as hostrequire. '
             'Such as: %ent-02-vm%, ent-02-vm-20.lab.eng.nay.redhat.com')
    parser.add_argument(
        '--host-type',
        required=False,
        default=None,
        help='Define the system type as hostrequire. '
             'Such as: physical or virtual')
    parser.add_argument(
        '--host-require',
        required=False,
        default=None,
        help='Separate multiple options with commas. '
             'Such as: labcontroller=lab.example.com,memory > 7000')
    parser.add_argument(
        '--gating-msg',
        default=None,
        required=False,
        help='Gating msg from UMB')
    parser.add_argument(
        '--brew-url',
        default=None,
        required=False,
        help='Brew url of virt-who package')
    return parser.parse_args()


if __name__ == "__main__":
    args = virtwho_arguments_parser()
    provision_virtwho_host_by_beaker(args)
