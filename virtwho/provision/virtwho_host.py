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
        rhel_compose: required option, such as RHEL-7.9-20200917.0.
        arch: required option, such as x86_64, s390x, ppc64...
        variant: optional, default using BaseOS for rhel8 and later.
        job_group: optional, associate a group to this job.
        host: optional, define/filter system as hostrequire
        host_type: optional, physical or virtual
        host_require: optional, other hostRequires for job
        gating_msg: optional, install virt-who from gating msg
        brew_url: optional, install virt-who from brew url
    """
    host = install_rhel_by_beaker(args)
    host = '10.66.144.5'
    username = config.beaker.default_username
    password = config.beaker.default_password
    ssh_host = SSHConnect(
        host=host,
        user=username,
        pwd=password
    )
    base.system_init(ssh_host, 'virtwho')
    virtwho_install(ssh_host, args.gating_msg, args.brew_url)
    config.update('virtwho', 'server', host)
    config.update('virtwho', 'username', username)
    config.update('virtwho', 'password', password)


def virtwho_install(ssh, gating_msg=None, brew_url=None):
    """
    Install virt-who package, default is from repository,
    or gating msg, or brew url.
    :param ssh: ssh access of virt-who host
    :param gating_msg: JSON, got from UMB
    :param brew_url: brew url link of virt-who package
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
    ssh.runcmd(cmd)
    if gating_msg:
        env = base.gating_msg_parser(gating_msg)
        pkg_url = env['pkg_url']
        virtwho_install_by_url(ssh, pkg_url)
    elif brew_url:
        virtwho_install_by_url(ssh, brew_url)
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


def virtwho_arguments_parser():
    """
    Parse and convert the arguments from command line to parameters
    for function using, and generate help and usage messages for
    each arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--rhel-compose',
        required=True,
        help='Such as: RHEL-7.9-20200917.0, RHEL-8.0-20181005.1')
    parser.add_argument(
        '--arch',
        required=True,
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
        help='It is a json got from UMB to provide virt-who pkg url')
    parser.add_argument(
        '--brew-url',
        default=None,
        required=False,
        help='It is used to install virt-who pkg by brew url')
    return parser.parse_args()


if __name__ == "__main__":
    args = virtwho_arguments_parser()
    provision_virtwho_host_by_beaker(args)
