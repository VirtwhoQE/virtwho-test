#!/usr/bin/python
import json
import os
import random
import re
import string
import sys
import argparse
import time

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(os.path.split(rootPath)[0])

from virtwho import logger, FailException
from virtwho.settings import config
from virtwho.ssh import SSHConnect


def system_init(ssh, key):
    if ssh_connect(ssh):
        host_ip = ipaddr_get(ssh)
        host_name = hostname_get(ssh)
        if ('localhost' in host_name
                or 'unused' in host_name
                or 'openshift' in host_name
                or host_name is None):
            random_str = ''.join(
                random.sample(string.ascii_letters + string.digits, 8)
            )
            host_name = f'{key}-{random_str}.redhat.com'
        hostname_set(ssh, host_name)
        etc_hosts_set(ssh, f'{host_ip} {host_name}')
        firewall_stop(ssh)
        selinux_disable(ssh)
        logger.info("Finished to init system {0}".format(host_name))
    else:
        raise FailException("Failed to ssh login {0}".format(ssh['host']))


def ssh_connect(ssh):
    for i in range(60):
        ret, output = ssh.runcmd('rpm -qa filesystem')
        if ret == 0 and 'filesystem' in output:
            return True
        time.sleep(60)
    return False


def ipaddr_get(ssh):
    ret, output = ssh.runcmd("ip route get 8.8.8.8 |"
                             "awk '/src/ { print $7 }'")
    if ret == 0 and output:
        return output.strip()
    raise FailException(f'Failed to get ip address.')


def hostname_get(ssh):
    ret, output = ssh.runcmd('hostname')
    if ret == 0 and output:
        return output.strip()
    raise FailException('Failed to get hostname.')


def hostname_set(ssh, hostname):
    ret1, _ = ssh.runcmd(f'hostnamectl set-hostname {hostname}')
    cmd = (f"if [ -f /etc/hostname ];"
           f"then sed -i -e '/localhost/d' -e '/{hostname}/d' /etc/hostname;"
           f"echo {hostname} >> /etc/hostname; fi")
    if rhel_version(ssh) == '6':
        cmd = (f"sed -i '/HOSTNAME=/d' /etc/sysconfig/network;"
               f"echo 'HOSTNAME={hostname}' >> /etc/sysconfig/network")
    ret2, _ = ssh.runcmd(cmd)
    if ret1 != 0 or ret2 != 0:
        raise FailException(f'Failed to set hostname ({hostname})')


def etc_hosts_set(ssh, value):
    ret, _ = ssh.runcmd(f"sed -i '/localhost/!d' /etc/hosts;"
                        f"echo '{value}' >> /etc/hosts")
    if ret != 0:
        raise FailException('Failed to set /etc/hosts')


def firewall_stop(ssh):
    cmd = ('systemctl stop firewalld.service;'
           'systemctl disable firewalld.service')
    if rhel_version(ssh) == '6':
        cmd = 'service iptables stop; chkconfig iptables off'
    ret, _ = ssh.runcmd(cmd)
    if ret != 0:
        raise FailException('Failed to stop firewall')


def selinux_disable(ssh):
    ret, _ = ssh.runcmd("setenforce 0;"
                        "sed -i -e 's/SELINUX=.*/SELINUX=disabled/g' "
                        "/etc/selinux/config")
    if ret != 0:
        raise FailException('Failed to disable selinux')


def rhel_version(ssh):
    ret, output = ssh.runcmd('cat /etc/redhat-release')
    if ret == 0 and output:
        m = re.search(r'(?<=release )\d', output)
        rhel_ver = m.group(0)
        return str(rhel_ver)
    raise FailException('Failed to check rhel version.')


def url_validation(url):
    output = os.popen(f"if ( curl -o/dev/null -sfI '{url}' );"
                      f"then echo 'true';"
                      f"else echo 'false';"
                      f"fi").read()
    if output.strip() == 'true':
        return True
    return False


def gating_msg_parser(json_msg):
    env = dict()
    msg = json.loads(json_msg)
    if 'info' in msg.keys():
        build_id = msg['info']['build_id']
        task_id = msg['info']['task_id']
    else:
        build_id = re.findall(r'"build_id":(.*?),', json_msg)[-1].strip()
        task_id = re.findall(r'"task_id":(.*?),', json_msg)[-1].strip()
    brew_url = f'{config.virtwho.brew}/brew/buildinfo?buildID={build_id}'
    pkg_url = re.findall(
        r'<a href="http://(.*?).noarch.rpm">download</a>',
        os.popen(f'curl -k -s -i {brew_url}').read()
    )[-1]
    if not pkg_url:
        raise FailException('no package url found')
    items = pkg_url.split('/')
    rhel_release = items[3]
    version = '9'
    if 'rhel-8' in rhel_release:
        version = '8'
    latest_compose_url = (f'{config.virtwho.repo}/rhel-{version}/nightly/'
                          f'RHEL-{version}/latest-RHEL-{version}/COMPOSE_ID')
    latest_compose_id = os.popen(
        f'curl -s -k -L {latest_compose_url}'
    ).read().strip()
    env['build_id'] = build_id
    env['task_id'] = task_id
    env['pkg_url'] = 'http://' + pkg_url + '.noarch.rpm'
    env['pkg_name'] = items[5]
    env['pkg_version'] = items[6]
    env['pkg_release'] = items[7]
    env['pkg_arch'] = items[8]
    env['pkg_nvr'] = items[9]
    env['rhel_release'] = rhel_release
    env['latest_rhel_compose'] = latest_compose_id
    logger.info(f'{env}')
    return env


def url_file_download(ssh, local_file, remote_url):
    _, _ = ssh.runcmd(f'rm -f {local_file};'
                      f'curl -L {remote_url} -o {local_file};'
                      f'sync')
    ret, output = ssh.runcmd(f'cat {local_file}')
    if ret != 0 or 'Not Found' in output:
        raise FailException(f'Failed to download {remote_url}')
