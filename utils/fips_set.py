import os
import argparse
import sys

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from virtwho.ssh import SSHConnect
from virtwho import config, logger
from virtwho.base import system_reboot
from virtwho import FailException


def fips_set_for_rhel_host(args):
    """
    Disable/Enable the fips mode for RHEL (>=RHEL8) host
    """
    fips = "1"
    if args.mode == "disable":
        fips = "0"
    fips_check = "cat /proc/sys/crypto/fips_enabled"
    ssh_host = SSHConnect(host=args.server, user=args.username, pwd=args.password)
    _, stdout = ssh_host.runcmd(fips_check)
    if fips in stdout:
        logger.info(f"The host has been in the Fips/{args.mode} mode.")
        return True
    else:
        ssh_host.runcmd(f"fips-mode-setup --{args.mode}")
        system_reboot(ssh_host)
        _, stdout = ssh_host.runcmd(fips_check)
        if fips in stdout:
            logger.info(f"The host was set to Fips/{args.mode} mode.")
            return True
        raise FailException(f"Failed to set the Fips/{args.mode} mode")


def arguments_parser():
    """
    Parse and convert the arguments from command line to parameters
    for function using, and generate help and usage messages for
    each arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--server",
        default=config.virtwho.server,
        required=False,
        help="RHEL host IP address/hostname, default to use the virtwho.ini:virtwho:server",
    )
    parser.add_argument(
        "--username",
        default=config.virtwho.username,
        required=False,
        help="RHEL host access username, default to use the virtwho.ini:virtwho:username.",
    )
    parser.add_argument(
        "--password",
        default=config.virtwho.password,
        required=False,
        help="RHEL host access password, default to use the virtwho.ini:virtwho:password.",
    )
    parser.add_argument(
        "--mode",
        default="enable",
        required=False,
        help="enable/disable fips mode, default is enable",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = arguments_parser()
    fips_set_for_rhel_host(args)
