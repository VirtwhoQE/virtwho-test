#!/usr/bin/python
import json
import os
import random
import re
import string
import operator

from virtwho import logger, FailException
from virtwho.settings import config


def system_init(ssh, keyword):
    """
    Initiate the rhel system before testing, including set hostname,
    stop firewall and disable selinux.
    :param ssh: ssh access of host
    :param keyword: keyword to set the hostname
    """
    host_ip = ipaddr_get(ssh)
    host_name = hostname_get(ssh)
    if ('localhost' in host_name
            or 'unused' in host_name
            or 'openshift' in host_name
            or host_name is None):
        random_str = ''.join(
            random.sample(string.ascii_letters + string.digits, 8)
        )
        host_name = f'{keyword}-{random_str}.redhat.com'
    hostname_set(ssh, host_name)
    etc_hosts_set(ssh, f'{host_ip} {host_name}')
    firewall_stop(ssh)
    selinux_disable(ssh)
    logger.info(f'Finished to init system {host_name}')


def ipaddr_get(ssh):
    """
    Get the host ip address.
    :param ssh: ssh access of host
    """
    ret, output = ssh.runcmd("ip route get 8.8.8.8 |"
                             "awk '/src/ { print $7 }'")
    if ret == 0 and output:
        return output.strip()
    else:
        logger.error(f'Failed to get ip address.')
        return None


def hostname_get(ssh):
    """
    Get the hostname.
    :param ssh: ssh access of host
    """
    ret, output = ssh.runcmd('hostname')
    if ret == 0 and output:
        return output.strip()
    else:
        logger.error('Failed to get hostname.')
        return None


def hostname_set(ssh, hostname):
    """
    Set hostname.
    :param ssh: ssh access of host
    :param hostname: hostname
    """
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
    """
    Set the /etc/hosts file.
    :param ssh: ssh access of host
    :param value: should be the format of '{ip} {hostname}'
    """
    ret, _ = ssh.runcmd(f"sed -i '/localhost/!d' /etc/hosts;"
                        f"echo '{value}' >> /etc/hosts")
    if ret != 0:
        raise FailException('Failed to set /etc/hosts')


def firewall_stop(ssh):
    """
    Stop firewall for one host.
    :param ssh: ssh access of host
    """
    cmd = ('systemctl stop firewalld.service;'
           'systemctl disable firewalld.service')
    if rhel_version(ssh) == '6':
        cmd = 'service iptables stop; chkconfig iptables off'
    ret, _ = ssh.runcmd(cmd)
    if ret != 0:
        raise FailException('Failed to stop firewall')


def selinux_disable(ssh):
    """
    Disable selinux for one host.
    :param ssh: ssh access of host
    """
    ret, _ = ssh.runcmd("setenforce 0;"
                        "sed -i -e 's/SELINUX=.*/SELINUX=disabled/g' "
                        "/etc/selinux/config")
    if ret != 0:
        raise FailException('Failed to disable selinux')


def ssh_connect(ssh):
    """
    Test if the host is running and can be accessed by ssh.
    :param ssh: ssh access of host
    """
    ret, output = ssh.runcmd('rpm -qa filesystem')
    if ret == 0 and 'filesystem' in output:
        logger.info(f'Suceeded to ssh connect the host')


def host_ping(host, port=22):
    """
    Test if the host is available to ping successfully.
    :param host: host ip/fqdn
    :param port: host port
    """
    ret = os.system(f'ping -w 5 {host} -p {port}')
    if ret == 0:
        return True
    return False


def rhel_version(ssh):
    """
    Check the rhel version.
    :param ssh: ssh access of host
    :return: one number, such as 7, 8, 9
    """
    ret, output = ssh.runcmd('cat /etc/redhat-release')
    if ret == 0 and output:
        m = re.search(r'(?<=release )\d', output)
        rhel_ver = m.group(0)
        return str(rhel_ver)
    raise FailException('Failed to check rhel version.')


def url_validation(url):
    """
    Test the url existence.
    :param url: url link
    :return: True or False
    """
    output = os.popen(f"if ( curl -o/dev/null -sfI '{url}' );"
                      f"then echo 'true';"
                      f"else echo 'false';"
                      f"fi").read()
    if output.strip() == 'true':
        return True
    return False


def gating_msg_parser(json_msg):
    """
    Parse the gating message to a dict with necessary options.
    :param json_msg: gating msg got from UMB, which should be a Json
    :return: a dict
    """
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
    return env


def url_file_download(ssh, local_file, url):
    """
    Test the url existence.
    :param ssh: ssh access of host
    :param local_file: local file path and name
    :param url: url link of remote file
    """
    _, _ = ssh.runcmd(f'rm -f {local_file};'
                      f'curl -L {url} -o {local_file};'
                      f'sync')
    ret, output = ssh.runcmd(f'cat {local_file}')
    if ret != 0 or 'Not Found' in output:
        raise FailException(f'Failed to download {url}')


def rhel_compose_repo(ssh, compose_id, repo_file):
    """
    Set the BaseOS and AppStream compose repository of rhel.
    :param ssh: ssh access of host
    :param compose_id: rhel compose id
    :param repo_file: repository file name
    """
    repo_base, repo_extra = rhel_compose_url(compose_id)
    cmd = (f'cat <<EOF > {repo_file}\n'
           f'[{compose_id}]\n'
           f'name={compose_id}\n'
           f'baseurl={repo_base}\n'
           f'enabled=1\n'
           f'gpgcheck=0\n\n'
           f'[{compose_id}-appstream]\n'
           f'name={compose_id}-appstream\n'
           f'baseurl={repo_extra}\n'
           f'enabled=1\n'
           f'gpgcheck=0\n'
           f'EOF')
    ret, _ = ssh.runcmd(cmd)
    if ret != 0:
        raise FailException('Failed to configure rhel compose repo.')


def rhel_compose_url(compose_id):
    """
    Configure the BaseOS and AppStream compose url
    :param compose_id: rhel compose id
    """
    base_url = config.virtwho.repo
    repo_base = ''
    repo_extra = ''
    if 'RHEL-7' in compose_id:
        if 'updates' in compose_id:
            repo_base = f'{base_url}/rhel-7/rel-eng/updates/RHEL-7/{compose_id}/compose/Server/x86_64/os'
            repo_extra = f'{base_url}/rhel-7/rel-eng/updates/RHEL-7/{compose_id}/compose/Server-optional/x86_64/os'
        elif '.n' in compose_id:
            repo_base = f'{base_url}/rhel-7/nightly/RHEL-7/{compose_id}/compose/Server/x86_64/os'
            repo_extra = f'{base_url}/rhel-7/nightly/RHEL-7/{compose_id}/compose/Server-optional/x86_64/os'
        else:
            repo_base = f'{base_url}/rhel-7/rel-eng/RHEL-7/{compose_id}/compose/Server/x86_64/os'
            repo_extra = f'{base_url}/rhel-7/rel-eng/RHEL-7/{compose_id}/compose/Server-optional/x86_64/os'
    if 'RHEL-8' in compose_id:
        if 'updates' in compose_id:
            repo_base = f'{base_url}/rhel-8/rel-eng/updates/RHEL-8/{compose_id}/compose/BaseOS/x86_64/os'
            repo_extra = f'{base_url}/rhel-8/rel-eng/updates/RHEL-8/{compose_id}/compose/AppStream/x86_64/os'
        elif '.d' in compose_id:
            repo_base = f'{base_url}/rhel-8/development/RHEL-8/{compose_id}/compose/BaseOS/x86_64/os'
            repo_extra = f'{base_url}/rhel-8/development/RHEL-8/{compose_id}/compose/AppStream/x86_64/os'
        else:
            repo_base = f'{base_url}/rhel-8/nightly/RHEL-8/{compose_id}/compose/BaseOS/x86_64/os'
            repo_extra = f'{base_url}/rhel-8/nightly/RHEL-8/{compose_id}/compose/AppStream/x86_64/os'
    elif 'RHEL-9' in compose_id:
        if '.d' in compose_id:
            repo_base = f'{base_url}/rhel-9/development/RHEL-9/{compose_id}/compose/BaseOS/x86_64/os'
            repo_extra = f"{base_url}/rhel-9/development/RHEL-9/{compose_id}/compose/AppStream/x86_64/os"
        else:
            repo_base = f'{base_url}/rhel-9/nightly/RHEL-9/{compose_id}/compose/BaseOS/x86_64/os'
            repo_extra = f'{base_url}/rhel-9/nightly/RHEL-9/{compose_id}/compose/AppStream/x86_64/os'
    return repo_base, repo_extra


def local_files_compare(file1, file2):
    """
    Compare two local files information.
    :param file1: local file 1
    :param file2: local file 2
    :reture: True or False
    """
    fp1 = open(file1)
    fp2 = open(file2)
    flist1 = [i for i in fp1]
    flist2 = [x for x in fp2]
    fp1.close()
    fp2.close()
    return operator.eq(flist1, flist2)


def url_validation(url):
    """
    Test if the url available or not.
    :param url: url link to check
    :reture: True or False
    """
    output = os.popen(
        f"if ( curl -o/dev/null -sfI '{url}' );"
        f"then echo 'true';"
        f"else echo 'false'; fi"
    ).read()
    if output.strip() == 'true':
        return True
    logger.warning(f'url({url}) not available')
    return False


def package_info_analyzer(ssh, pkg):
    """
    Analyze the package information after '#rpm -qa {pkg}'.
    :param ssh: ssh access of testing host
    :param pkg: package to test
    :reture: a dict
    """
    _, output = ssh.runcmd(f'rpm -qi {pkg}')
    data = dict()
    info = output.strip().split('\n')
    for line in info:
        if ': ' not in line:
            continue
        line = line.split(': ')
        data[line[0].strip()] = line[1].strip()
    return data


def package_install(ssh, pkg_name, rpm=None):
    """
    Install a package by yum or rpm
    :param ssh: ssh access of testing host
    :param pkg_name: package name, such as virt-who
    :param rpm: rpm path, such as /root/virt-who-1.31.23-1.el9.noarch.rpm
    """
    cmd = f'yum install -y {pkg_name}'
    if rpm:
        cmd = f'rpm -ivh {rpm}'
    _, _ = ssh.runcmd(cmd)
    if package_check(ssh, pkg_name) is False:
        raise FailException(f'Failed to install {pkg_name}')


def package_uninstall(ssh, pkg_name, rpm=False):
    """
    Uninstall a package by yum or rpm
    :param ssh: ssh access of testing host
    :param pkg_name: package name, such as virt-who
    :param rpm: rpm path, such as /root/virt-who-1.31.23-1.el9.noarch.rpm
    """
    cmd = f'yum remove -y {pkg_name}'
    if rpm:
        cmd = f'rpm -e {rpm} --nodeps'
    _, _ = ssh.runcmd(cmd)
    if package_check(ssh, pkg_name) is True:
        raise FailException(f'Failed to uninstall {pkg_name}')


def package_upgrade(ssh, pkg_name, rpm=None):
    """
    Upgrade a package by yum or rpm
    :param ssh: ssh access of testing host
    :param pkg_name: package name, such as virt-who
    :param rpm: rpm path, such as /root/virt-who-1.31.23-1.el9.noarch.rpm
    """
    cmd = f'yum upgrade -y {pkg_name}'
    if rpm:
        cmd = f'rpm -Uvh {rpm}'
    ret, output = ssh.runcmd(cmd)
    if ret != 0:
        raise FailException(f'Failed to upgrade {pkg_name}')


def package_downgrade(ssh, pkg_name, rpm=False):
    """
    Downgrade a package by yum or rpm
    :param ssh: ssh access of testing host
    :param pkg_name: package name, such as virt-who
    :param rpm: rpm path, such as /root/virt-who-1.31.23-1.el9.noarch.rpm
    """
    cmd = f'yum downgrade -y {pkg_name}'
    if rpm:
        cmd = f'rpm -Uvh --oldpackage {rpm}'
    ret, output = ssh.runcmd(cmd)
    if ret != 0:
        raise FailException(f'Failed to downgrade {pkg_name}')


def package_check(ssh, pkg_name):
    """
    Check a package by #rpm -qa
    :param ssh: ssh access of testing host
    :param pkg_name: package name, such as virt-who
    :return: the package or False
    """
    ret, output = ssh.runcmd(f'rpm -qa {pkg_name}')
    if ret == 0 and pkg_name in output:
        return output.strip()
    return False


def wget_download(ssh, url, file_path, file_name=None):
    """
    Download from url by wget
    :param ssh: ssh access of testing host
    :param url: download resource
    :param file_path: the save path
    :param file_name: the save name
    """
    _, ouput = ssh.runcmd(f'ls {file_path}')
    if 'No such file or directory' in ouput:
        _, _ = ssh.runcmd(f'mkdir -p {file_path}')
    cmd = f'wget {url} -P {file_path} '
    if file_name:
        cmd += f' -O {file_name}'
    ret, output = ssh.runcmd(cmd)
    if ret == 0 and '100%' in output:
        return True
    raise FailException(f'Failed to wget download from {url}')


def random_string(num=8):
    """
    Create a random string with ascii and digit, such as 'Ca9KGqlY'
    :param num: the string numbers, default is 8
    """
    random_str = ''.join(
        random.sample(string.ascii_letters + string.digits, num)
    )
    return random_str


def encrypt_password(ssh, password):
    """
    Encrypt password by virt-who-password command
    :param ssh: ssh access of testing host
    :param password: the password would like to Encrypt
    :return: the encrypted password
    """
    cmd = f'virt-who-password -p {password} > /tmp/vw.log'
    ret, output = ssh.runcmd(cmd)
    if ret == 0:
        ret, output = ssh.runcmd("cat /tmp/vw.log")
        if output is not None and output != '':
            encrypted_value = output.strip()
            logger.info(f'Succeeded to get encrypted_password : {encrypted_value}')
            return encrypted_value
        else:
            raise FailException("Failed to run virt-who-password")
    else:
        raise FailException("Failed to run virt-who-password")
