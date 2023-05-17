import json
import os
import random
import re
import string
import operator
import time

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
    if (
        "localhost" in host_name
        or "unused" in host_name
        or "openshift" in host_name
        or host_name is None
    ):
        random_str = "".join(random.sample(string.ascii_letters + string.digits, 8))
        host_name = f"{keyword}-{random_str}.redhat.com"
    hostname_set(ssh, host_name)
    etc_hosts_set(ssh, f"{host_ip} {host_name}")
    firewall_stop(ssh)
    selinux_disable(ssh)
    logger.info(f"Finished to init system {host_name}")


def ipaddr_get(ssh):
    """
    Get the host ip address.
    :param ssh: ssh access of host
    """
    ret, output = ssh.runcmd("ip route get 8.8.8.8 |" "awk '/src/ { print $7 }'")
    if ret == 0 and output:
        return output.strip()
    else:
        logger.error(f"Failed to get ip address.")
        return None


def hostname_get(ssh):
    """
    Get the hostname.
    :param ssh: ssh access of host
    """
    ret, output = ssh.runcmd("hostname")
    if ret == 0 and output:
        return output.strip()
    else:
        logger.error("Failed to get hostname.")
        return None


def hostname_set(ssh, hostname):
    """
    Set hostname.
    :param ssh: ssh access of host
    :param hostname: hostname
    """
    ret1, _ = ssh.runcmd(f"hostnamectl set-hostname {hostname}")
    cmd = (
        f"if [ -f /etc/hostname ];"
        f"then sed -i -e '/localhost/d' -e '/{hostname}/d' /etc/hostname;"
        f"echo {hostname} >> /etc/hostname; fi"
    )
    if rhel_version(ssh) == "6":
        cmd = (
            f"sed -i '/HOSTNAME=/d' /etc/sysconfig/network;"
            f"echo 'HOSTNAME={hostname}' >> /etc/sysconfig/network"
        )
    ret2, _ = ssh.runcmd(cmd)
    if ret1 != 0 or ret2 != 0:
        raise FailException(f"Failed to set hostname ({hostname})")


def etc_hosts_set(ssh, value):
    """
    Set the /etc/hosts file.
    :param ssh: ssh access of host
    :param value: should be the format of '{ip} {hostname}'
    """
    ret, _ = ssh.runcmd(
        f"sed -i '/localhost/!d' /etc/hosts;" f"echo '{value}' >> /etc/hosts"
    )
    if ret != 0:
        raise FailException("Failed to set /etc/hosts")


def firewall_stop(ssh):
    """
    Stop firewall for one host.
    :param ssh: ssh access of host
    """
    cmd = "systemctl stop firewalld.service;" "systemctl disable firewalld.service"
    if rhel_version(ssh) == "6":
        cmd = "service iptables stop; chkconfig iptables off"
    ret, _ = ssh.runcmd(cmd)
    if ret != 0:
        raise FailException("Failed to stop firewall")


def selinux_disable(ssh):
    """
    Disable selinux for one host.
    :param ssh: ssh access of host
    """
    ret, _ = ssh.runcmd(
        "setenforce 0;"
        "sed -i -e 's/SELINUX=.*/SELINUX=disabled/g' "
        "/etc/selinux/config"
    )
    if ret != 0:
        raise FailException("Failed to disable selinux")


def ssh_connect(ssh):
    """
    Test if the host is running and can be accessed by ssh.
    :param ssh: ssh access of host
    """
    ret, output = ssh.runcmd("rpm -qa filesystem")
    if ret == 0 and "filesystem" in output:
        logger.info(f"Suceeded to ssh connect the host")
        return True
    return False


def host_ping(host, port=22):
    """
    Test if the host is available to ping successfully.
    :param host: host ip/fqdn
    :param port: host port
    """
    ret = os.system(f"ping -c 5 {host} -p {port}")
    if ret == 0:
        return True
    return False


def rhel_version(ssh):
    """
    Check the rhel version.
    :param ssh: ssh access of host
    :return: one number, such as 7, 8, 9
    """
    ret, output = ssh.runcmd("cat /etc/redhat-release")
    if ret == 0 and output:
        m = re.search(r"(?<=release )\d", output)
        rhel_ver = m.group(0)
        return str(rhel_ver)
    raise FailException("Failed to check rhel version.")


def url_validation(url):
    """
    Test the url existence.
    :param url: url link
    :return: True or False
    """
    output = os.popen(
        f"if ( curl -o/dev/null -sfI '{url}' );"
        f"then echo 'true';"
        f"else echo 'false';"
        f"fi"
    ).read()
    if output.strip() == "true":
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
    if "info" in msg.keys():
        build_id = msg["info"]["build_id"]
        task_id = msg["info"]["task_id"]
    else:
        build_id = re.findall(r'"build_id":(.*?),', json_msg)[-1].strip()
        task_id = re.findall(r'"task_id":(.*?),', json_msg)[-1].strip()
    brew_url = f"{config.virtwho.brew}/brew/buildinfo?buildID={build_id}"
    pkg_url = re.findall(
        r'<a href="http://(.*?).noarch.rpm">download</a>',
        os.popen(f"curl -k -s -i {brew_url}").read(),
    )[-1]
    if not pkg_url:
        raise FailException("no package url found")
    items = pkg_url.split("/")
    rhel_release = items[3]
    version = "9"
    if "rhel-8" in rhel_release:
        version = "8"
    latest_compose_url = (
        f"{config.virtwho.repo}/rhel-{version}/nightly/"
        f"RHEL-{version}/latest-RHEL-{version}/COMPOSE_ID"
    )
    latest_compose_id = os.popen(f"curl -s -k -L {latest_compose_url}").read().strip()
    env["build_id"] = build_id
    env["task_id"] = task_id
    env["pkg_url"] = "http://" + pkg_url + ".noarch.rpm"
    env["pkg_name"] = items[5]
    env["pkg_version"] = items[6]
    env["pkg_release"] = items[7]
    env["pkg_arch"] = items[8]
    env["pkg_nvr"] = items[9]
    env["rhel_release"] = rhel_release
    env["latest_rhel_compose"] = latest_compose_id
    return env


def url_file_download(ssh, local_file, url):
    """
    Test the url existence.
    :param ssh: ssh access of host
    :param local_file: local file path and name
    :param url: url link of remote file
    """
    ssh.runcmd(f"rm -f {local_file};" f"curl -L {url} -o {local_file};" f"sync")
    ret, output = ssh.runcmd(f"cat {local_file}")
    if ret != 0 or "Not Found" in output:
        raise FailException(f"Failed to download {url}")


def rhel_compose_repo(ssh, repo_file, compose_id, compose_path=""):
    """
    Set the BaseOS and AppStream compose repository of rhel.
    :param ssh: ssh access of host
    :param compose_id: rhel compose id
    :param compose_path: rhel compose path, use default setting when set null.
    :param repo_file: repository file name
    """
    repo_base, repo_extra = rhel_compose_url(compose_id, compose_path)
    cmd = (
        f"cat <<EOF > {repo_file}\n"
        f"[{compose_id}]\n"
        f"name={compose_id}\n"
        f"baseurl={repo_base}\n"
        f"enabled=1\n"
        f"gpgcheck=0\n\n"
        f"[{compose_id}-appstream]\n"
        f"name={compose_id}-appstream\n"
        f"baseurl={repo_extra}\n"
        f"enabled=1\n"
        f"gpgcheck=0\n"
        f"EOF"
    )
    ret, _ = ssh.runcmd(cmd)
    if ret != 0:
        raise FailException("Failed to configure rhel compose repo.")


def rhel_compose_url(compose_id, compose_path=""):
    """
    Configure the BaseOS and AppStream compose url
    :param compose_id: rhel compose id
    :param compose_path: rhel compose path, use default path when set null.
    """
    base_url = config.virtwho.repo
    repo_base = ""
    repo_extra = ""
    if compose_path:
        if "RHEL-7" in compose_id:
            repo_base = f"{compose_path}/{compose_id}/compose/Server/x86_64/os"
            repo_extra = (
                f"{compose_path}/{compose_id}/compose/Server-optional/x86_64/os"
            )
        else:
            repo_base = f"{compose_path}/{compose_id}/compose/BaseOS/x86_64/os"
            repo_extra = f"{compose_path}/{compose_id}/compose/AppStream/x86_64/os"
    else:
        if "RHEL-7" in compose_id:
            if "updates" in compose_id:
                repo_base = f"{base_url}/rhel-7/rel-eng/updates/RHEL-7/{compose_id}/compose/Server/x86_64/os"
                repo_extra = f"{base_url}/rhel-7/rel-eng/updates/RHEL-7/{compose_id}/compose/Server-optional/x86_64/os"
            elif ".n" in compose_id:
                repo_base = f"{base_url}/rhel-7/nightly/RHEL-7/{compose_id}/compose/Server/x86_64/os"
                repo_extra = f"{base_url}/rhel-7/nightly/RHEL-7/{compose_id}/compose/Server-optional/x86_64/os"
            else:
                repo_base = f"{base_url}/rhel-7/rel-eng/RHEL-7/{compose_id}/compose/Server/x86_64/os"
                repo_extra = f"{base_url}/rhel-7/rel-eng/RHEL-7/{compose_id}/compose/Server-optional/x86_64/os"
        if "RHEL-8" in compose_id:
            if "updates" in compose_id:
                repo_base = f"{base_url}/rhel-8/rel-eng/updates/RHEL-8/{compose_id}/compose/BaseOS/x86_64/os"
                repo_extra = f"{base_url}/rhel-8/rel-eng/updates/RHEL-8/{compose_id}/compose/AppStream/x86_64/os"
            elif ".d" in compose_id:
                repo_base = f"{base_url}/rhel-8/development/RHEL-8/{compose_id}/compose/BaseOS/x86_64/os"
                repo_extra = f"{base_url}/rhel-8/development/RHEL-8/{compose_id}/compose/AppStream/x86_64/os"
            else:
                repo_base = f"{base_url}/rhel-8/nightly/RHEL-8/{compose_id}/compose/BaseOS/x86_64/os"
                repo_extra = f"{base_url}/rhel-8/nightly/RHEL-8/{compose_id}/compose/AppStream/x86_64/os"
        elif "RHEL-9" in compose_id:
            if ".d" in compose_id:
                repo_base = f"{base_url}/rhel-9/development/RHEL-9/{compose_id}/compose/BaseOS/x86_64/os"
                repo_extra = f"{base_url}/rhel-9/development/RHEL-9/{compose_id}/compose/AppStream/x86_64/os"
            else:
                repo_base = f"{base_url}/rhel-9/nightly/RHEL-9/{compose_id}/compose/BaseOS/x86_64/os"
                repo_extra = f"{base_url}/rhel-9/nightly/RHEL-9/{compose_id}/compose/AppStream/x86_64/os"
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


def package_info_analyzer(ssh, pkg):
    """
    Analyze the package information after '#rpm -qi {pkg}'.
    :param ssh: ssh access of testing host
    :param pkg: package to test
    :reture: a dict
    """
    _, output = ssh.runcmd(f"rpm -qi {pkg}")
    data = dict()
    info = output.strip().split("\n")
    for line in info:
        if ": " not in line:
            continue
        line = line.split(": ")
        data[line[0].strip()] = line[1].strip()
    return data


def package_install(ssh, pkg_name, rpm=None):
    """
    Install a package by yum or rpm
    :param ssh: ssh access of testing host
    :param pkg_name: package name, such as virt-who
    :param rpm: rpm path, such as /root/virt-who-1.31.23-1.el9.noarch.rpm
    """
    cmd = f"yum install -y {pkg_name}"
    if rpm:
        cmd = f"rpm -ivh {rpm}"
    ssh.runcmd(cmd)
    if package_check(ssh, pkg_name) is False:
        raise FailException(f"Failed to install {pkg_name}")


def package_uninstall(ssh, pkg_name, rpm=False):
    """
    Uninstall a package by yum or rpm
    :param ssh: ssh access of testing host
    :param pkg_name: package name, such as virt-who
    :param rpm: rpm path, such as /root/virt-who-1.31.23-1.el9.noarch.rpm
    """
    cmd = f"yum remove -y {pkg_name}"
    if rpm:
        cmd = f"rpm -e {rpm} --nodeps"
    ssh.runcmd(cmd)
    if package_check(ssh, pkg_name) is True:
        raise FailException(f"Failed to uninstall {pkg_name}")


def package_upgrade(ssh, pkg_name, rpm=None):
    """
    Upgrade a package by yum or rpm
    :param ssh: ssh access of testing host
    :param pkg_name: package name, such as virt-who
    :param rpm: rpm path, such as /root/virt-who-1.31.23-1.el9.noarch.rpm
    """
    cmd = f"yum upgrade -y {pkg_name}"
    if rpm:
        cmd = f"rpm -Uvh {rpm}"
    ret, output = ssh.runcmd(cmd)
    if ret != 0:
        raise FailException(f"Failed to upgrade {pkg_name}")


def package_downgrade(ssh, pkg_name, rpm=False):
    """
    Downgrade a package by yum or rpm
    :param ssh: ssh access of testing host
    :param pkg_name: package name, such as virt-who
    :param rpm: rpm path, such as /root/virt-who-1.31.23-1.el9.noarch.rpm
    """
    cmd = f"yum downgrade -y {pkg_name}"
    if rpm:
        cmd = f"rpm -Uvh --oldpackage {rpm}"
    ret, output = ssh.runcmd(cmd)
    if ret != 0:
        raise FailException(f"Failed to downgrade {pkg_name}")


def package_check(ssh, pkg_name):
    """
    Check a package by #rpm -qa
    :param ssh: ssh access of testing host
    :param pkg_name: package name, such as virt-who
    :return: the package or False
    """
    ret, output = ssh.runcmd(f"rpm -qa {pkg_name}")
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
    _, ouput = ssh.runcmd(f"ls {file_path}")
    if "No such file or directory" in ouput:
        ssh.runcmd(f"mkdir -p {file_path}")
    cmd = f"wget {url} -P {file_path} "
    if file_name:
        cmd += f" -O {file_name}"
    ret, output = ssh.runcmd(cmd)
    if ret == 0 and "100%" in output:
        return True
    raise FailException(f"Failed to wget download from {url}")


def random_string(num=8):
    """
    Create a random string with ascii and digit, such as 'Ca9KGqlY'
    :param num: the string numbers, default is 8
    """
    random_str = "".join(random.sample(string.ascii_letters + string.digits, num))
    return random_str


def encrypt_password(ssh, password, option=None):
    """
    Encrypt password by virt-who-password command
    :param ssh: ssh access of testing host
    :param password: the password would like to Encrypt
    :param option: -p, --password
    :return: the encrypted password
    """
    log_file = "/tmp/virtwho_encry_password"
    if not option:
        attrs = [f"Password:|{password}"]
        ret, output = expect_run(ssh, "virt-who-password", attrs)
        if ret == 0 and output:
            encrypted_value = output.split("\r\n")[-2].strip()
            logger.info(
                f"Succeeded to get encrypted_password without option: "
                f"{encrypted_value}"
            )
            return encrypted_value
        raise FailException("Failed to get encrypted password without option")
    else:
        cmd = f"virt-who-password -p {password} > {log_file}"
        ret, output = ssh.runcmd(cmd)
        if ret == 0:
            ret, output = ssh.runcmd(f"cat {log_file}")
            if output:
                encrypted_value = output.strip()
                logger.info(
                    f"Succeeded to get encrypted_password with option "
                    f'"{option}": {encrypted_value}'
                )
                return encrypted_value
        raise FailException(f'Failed to get encrypted password with "{option}"')


def get_host_domain_id(host_hwuuid, log_info):
    """
    Get the host domain_id from rhsm.log using the regular expression
    :param host_hwuuid: the hwuuid for the host
    :param log_info: log info from the rhsm.log
    :return: the domain_id from the host
    """
    domain_id = re.findall(
        rf"Skipping host '{host_hwuuid}' because its parent '(.*?)'", log_info
    )[0]
    return domain_id


def rhel_host_uuid_get(ssh):
    """
    Get the host domain_id from rhsm.log using the regular expression
    :param ssh: ssh access of testing host
    :return: rhel host uuid
    """
    ret, output = ssh.runcmd(f"dmidecode -t system |grep UUID")
    if ret == 0 and "UUID" in output:
        uuid = output.split(":")[1].strip()
        return uuid
    return None


def msg_search(output, msgs, check="or"):
    """
    Check if the key messages exist or not in output.
    :param output: messages to search around
    :param msgs: key messages to be searched.
        msgs could be a string or a list, list is recommanded.
        If '|' in string, it means 'or' for the left and right.
    :param check: and, or
    :return: Ture or False
    """
    if type(msgs) is str:
        msgs = [msgs]
    search_list = list()
    for msg in msgs:
        if_find = "No"
        if "|" in msg:
            keys = msg.split("|")
            for key in keys:
                if msg_number(output, key) > 0:
                    if_find = "Yes"
        else:
            if msg_number(output, msg) > 0:
                if_find = "Yes"
                logger.info(f"Succeeded to find message: {msg}")
        search_list.append(if_find)
    if check == "or":
        if "Yes" in search_list:
            return True
        return False
    else:
        if "No" in search_list:
            return False
        return True


def msg_number(output, msg):
    """
    Get message numbers.
    :param output: output string to search around
    :param msg: message string to be searched
    :return: the message number
    """
    number = len(re.findall(msg, output, re.I))
    logger.info(f"Find '{msg}' {number} times")
    return number


def ssh_access_no_password(ssh_local, ssh_remote, remote_host, remote_port=22):
    """
    Configure virt-who host accessing remote host by ssh
    without password.
    :param ssh_local: local server access
    :param ssh_remote: destination server access
    :param remote_host: remote host ip/hostname
    :param remote_port: remote host port
    """
    # create ssh key for local host
    ssh_local.runcmd('echo -e "\n" | ssh-keygen -N "" &> /dev/null')
    ret, output = ssh_local.runcmd("cat ~/.ssh/id_rsa.pub")
    if ret != 0 or output is None:
        raise FailException("Failed to create ssh key ")

    # copy id_rsa.pup to remote host
    ssh_remote.runcmd(f"mkdir ~/.ssh/;echo '{output}' >> ~/.ssh/authorized_keys")

    # creat ~/.ssh/known_hosts for local host
    ssh_local.runcmd(
        f"ssh-keyscan -p {remote_port} {remote_host} >> ~/.ssh/known_hosts"
    )


def expect_run(ssh, cmd, attrs):
    """
    Run command in terminal with interactive mode
    without password.
    :param ssh: ssh access of testing host
    :param cmd: the command
    :param attrs: such as ['Password:|password']
    """
    options = list()
    filename = "/tmp/virtwho.sh"
    for attr in attrs:
        expect_value = attr.split("|")[0]
        send_value = attr.split("|")[1]
        expect = rf'expect "{expect_value}"'
        send = rf'send "{send_value}\r"'
        options.append(expect + "\n" + send)
    options = "\n".join(options)
    cmd = (
        f"cat <<EOF > {filename}\n"
        f"#!/usr/bin/expect\n"
        f"spawn {cmd}\n"
        f"{options}\n"
        f"expect eof\n"
        f"exit\n"
        f"EOF"
    )
    ssh.runcmd(cmd)
    ret, output = ssh.runcmd(f"chmod +x {filename}; {filename}")
    return ret, output


def system_reboot(ssh):
    """
    Reboot a RHEL system.
    :param ssh: ssh access of testing host
    :return: True or raise fail.
    """
    ssh.runcmd("sync;sync;sync;sync;reboot")
    time.sleep(120)
    if ssh_connect(ssh):
        return True
    raise FailException("Failed to reboot system")


def virtwho_package_url(pkg, rhel_compose_id, rhel_compose_path=""):
    """
    Get the virt-who package url from http://download.eng.pek2.redhat.com/
    for downloading.
    :param pkg: virt-who package, such as virt-who-1.31.26-1.el9.noarch
    :param rhel_compose_id: rhel compose id
    :param rhel_compose_path: the path of rhel compose id
    :return: virt-who pkg url
    """
    _, compose_url_extra = rhel_compose_url(rhel_compose_id, rhel_compose_path)
    pkg_url = compose_url_extra + "/Packages/" + pkg + ".rpm"
    return pkg_url
