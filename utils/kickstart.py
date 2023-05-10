#!/usr/bin/python
import os
import random
import argparse
import string
import sys
import time

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from virtwho import base, logger, FailException
from virtwho.settings import config
from virtwho.ssh import SSHConnect


def install_rhel_by_grup(args):
    """
    Install a rhel system beased on an available host by change the grub files.
    Please refer to the utils/README for usage.
    """
    ssh_nfs = SSHConnect(
        host=config.nfs.server, user=config.nfs.username, pwd=config.nfs.password
    )
    ssh_host = SSHConnect(host=args.server, user=args.username, pwd=args.password)
    repo_base, repo_extra = base.rhel_compose_url(args.rhel_compose)
    ks_url, ks_path, vmlinuz_url, initrd_url = grup_params(repo_base)
    try:
        ks_file_create(ssh_nfs, ks_path, repo_base, repo_extra)
        grub_update(ssh_host, ks_url, vmlinuz_url, initrd_url, repo_base)
        grub_reboot(ssh_host)
        for i in range(60):
            if base.host_ping(args.server):
                base.ssh_connect(ssh_host)
                base.rhel_compose_repo(
                    ssh_host, args.rhel_compose, "/etc/yum.repos.d/compose.repo"
                )
            time.sleep(30)
    except Exception as e:
        logger.error(e)
    finally:
        ssh_host.runcmd(f"rm -rf {ks_path}")


def grup_params(repo_base):
    """
    Gether the necessary parameters for install rhel os by grub
    :param repo_base: xxx/compose/AppStream/x86_64/os
    """
    random_str = "".join(random.sample(string.ascii_letters + string.digits, 8))
    ks_name = f"{random_str}.cfg"
    ks_url = f"{config.nfs.ks_url}/{ks_name}"
    ks_path = f"{config.nfs.ks_mount}/{ks_name}"
    vmlinuz_url = f"{repo_base}/isolinux/vmlinuz"
    initrd_url = f"{repo_base}/isolinux/initrd.img"
    return ks_url, ks_path, vmlinuz_url, initrd_url


def ks_file_create(ssh, ks_path, repo_base, repo_extra):
    """
    Create ks file
    :param ssh: ssh access to nfs server
    :param ks_path: the path of ks file
    :param repo_base: base repo of rhel compose
    :param repo_extra: optional/appstream repo of rhel compose
    """
    cmd = (
        f"cat <<EOF > {ks_path}\n"
        f"text\n"
        f"bootloader --location=mbr\n"
        f"lang en_US.UTF-8\n"
        f"keyboard us\n"
        f"network  --bootproto=dhcp --activate\n"
        f"rootpw --plaintext {args.password}\n"
        f"firewall --disabled\n"
        f"selinux --disabled\n"
        f"timezone Asia/Shanghai\n"
        f"zerombr\n"
        f"clearpart --all --initlabel\n"
        f"autopart\n"
        f"reboot\n"
        f"repo --name=base --baseurl={repo_base}\n"
        f"repo --name=extra --baseurl={repo_extra}\n"
        f"%packages --ignoremissing\n"
        f"@base\n"
        f"%end\n"
        f"%post\n"
        f'sed -i "s/#*PermitRootLogin.*/PermitRootLogin yes/g" /etc/ssh/sshd_config\n'
        f'sed -i "s@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g" /etc/pam.d/sshd\n'
        f"%end\n"
        f"EOF"
    )
    for i in range(10):
        _, _ = ssh.runcmd(cmd)
        ret, _ = ssh.runcmd(f"ls {ks_path}")
        if ret == 0:
            return
        time.sleep(10)
    raise FailException(f"Failed to create ks file")


def grub_update(ssh, ks_url, vmlinuz_url, initrd_url, repo_url):
    """
    Update grub menuentry
    :param ssh: ssh access to the host
    :param ks_url: url of ks file
    :param vmlinuz_url: url of compose vmlinuz file
    :param initrd_url: url of compose initrd file
    :param repo_url: url of compose repo
    """
    logger.info(f"-----{ks_url}")
    logger.info(f"-----{vmlinuz_url}")
    logger.info(f"-----{initrd_url}")
    logger.info(f"-----{repo_url}")
    if (
        not base.url_validation(ks_url)
        or not base.url_validation(vmlinuz_url)
        or not base.url_validation(initrd_url)
        or not base.url_validation(repo_url)
    ):
        raise FailException("The necessary urls are not available")
    menu_title = "rhel-reinstall"
    vmlinuz_name = "vmlinuz-reinstall"
    initrd_name = "initrd-reinstall.img"
    ssh.runcmd(
        f"rm -f /boot/{vmlinuz_name};"
        f"curl -L {vmlinuz_url} -o /boot/{vmlinuz_name};"
        f"sync"
    )
    ssh.runcmd(
        f"rm -f /boot/{initrd_name};"
        f"curl -L {initrd_url} -o /boot/{initrd_name};"
        f"sync"
    )
    cmd = (
        "cat <<EOF > /etc/grub.d/40_custom\n"
        "#!/bin/sh\n"
        "exec tail -n +3 \$0\n"
        "menuentry '%s' --class red --class gnu-linux --class gnu --class os {\n"
        "load_video\n"
        "set gfxpayload=keep\n"
        "insmod gzio\n"
        "insmod part_msdos\n"
        "insmod xfs\n"
        'set root="hd0,msdos1"\n'
        "linux16 /%s ksdevice=bootif ip=dhcp ks=%s repo=%s quiet LANG=en_US.UTF-8 acpi=off\n"
        "initrd16 /%s\n"
        "}\n"
        "EOF"
    ) % (menu_title, vmlinuz_name, ks_url, repo_url, initrd_name)
    ret1, _ = ssh.runcmd(cmd)
    ret2, _ = ssh.runcmd("grub2-mkconfig -o /boot/grub2/grub.cfg")
    ret3, _ = ssh.runcmd(f'grub2-set-default "{menu_title}"; grub2-editenv list')
    if ret1 != 0 or ret2 != 0 or ret3 != 0:
        raise FailException("Failed to update grub file.")
    time.sleep(60)


def grub_reboot(ssh):
    """
    Reboot the host to reinstall os by grub
    :param ssh: ssh access to the host
    """
    ssh.runcmd("sync; sync; sync; sync;" "reboot -f > /dev/null 2>&1 &")
    time.sleep(20)


def rhel_arguments_parser():
    """
    Parse and convert the arguments from command line to parameters
    for function using, and generate help and usage messages for
    each arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--rhel-compose",
        required=True,
        help="[Required] Such as: RHEL-7.9-20200917.0, RHEL-8.0-20181005.1",
    )
    parser.add_argument(
        "--server", required=True, help="[Required] Host ip/fqdn to re-install"
    )
    parser.add_argument(
        "--username",
        required=False,
        default="root",
        help="[Optional] Default to use root",
    )
    parser.add_argument(
        "--password", required=True, help="[Required] Password to access the server"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = rhel_arguments_parser()
    install_rhel_by_grup(args)
