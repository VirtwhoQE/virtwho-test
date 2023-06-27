import argparse
import os
import sys

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(os.path.split(rootPath)[0])

from virtwho import FailException, logger
from virtwho.register import Satellite
from virtwho.ssh import SSHConnect
from virtwho.settings import config
from utils.beaker import install_rhel_by_beaker
from utils.satellite import satellite_deploy
from utils.properties_update import virtwho_ini_props_update


def satellite_deploy_for_virtwho(args):
    """
    Deploy satellite by cdn or dogfood with required arguments.
    If no server provided, will firstly install a new system by beaker.
    And will configure the satellite as virt-who testing requirements.
    Please refer to the README for usage.
    """
    logger.info("+++ Start to deploy the Satellite +++")
    satellite = args.satellite.split("-")
    args.version = satellite[0]
    args.repo = satellite[1]
    args.rhel_compose = rhel_compose_for_satellite(satellite[2])
    args.manifest = config.satellite.manifest

    # Install a new host by beaker to deploy satellite when no server provided.
    if not args.server:
        beaker_args_define(args)
        args.server = install_rhel_by_beaker(args)
        args.ssh_username = config.beaker.default_username
        args.ssh_password = config.beaker.default_password
        satellite_deploy(args)
    ssh_satellite = SSHConnect(
        host=args.server, user=args.ssh_username, pwd=args.ssh_password
    )

    # Start to configure the satellite server
    satellite_settings(ssh_satellite, "failed_login_attempts_limit", "0")
    satellite_settings(ssh_satellite, "unregister_delete_host", "true")

    # Default Org: setup SCA mode and upload manifest as requirement
    satellite = Satellite(server=args.server)
    satellite.sca(org=None, sca=args.sca)
    satellite_manifest_upload(
        org="Default_Organization",
        ssh=ssh_satellite,
        url=config.satellite.manifest,
        admin_username=args.admin_username,
        admin_password=args.admin_password,
    )

    # Second org: create org, then setup sca and upload manifest as requirement.
    second_org = config.satellite.secondary_org
    if second_org:
        satellite.org_create(name=second_org, label=second_org)
        satellite.sca(org=second_org, sca=args.sca)
        satellite_manifest_upload(
            org=second_org,
            ssh=ssh_satellite,
            url=config.satellite.manifest_second,
            admin_username=args.admin_username,
            admin_password=args.admin_password,
        )

    # Create the activation key as requirement
    activation_key = config.satellite.activation_key
    if activation_key:
        satellite.activation_key_create(key=activation_key)

    # Update the virtwho.ini:[satellite]
    args.section = "satellite"
    virtwho_ini_props = {
        "server": args.server,
        "username": args.admin_username,
        "password": args.admin_password,
        "ssh_username": args.ssh_username,
        "ssh_password": args.ssh_password,
    }
    for args.option, args.value in virtwho_ini_props.items():
        virtwho_ini_props_update(args)

    logger.info(
        f"+++ Succeeded to deploy the Satellite " f"{args.satellite}/{args.server} +++"
    )


def rhel_compose_for_satellite(rhel_version):
    """
    Define the stable rhel compose to deploy satellite.
    :param rhel_version: such as rhel7, rhel8
    :return: rhel compose id
    """
    compose_id = ""
    if "rhel7" in rhel_version:
        compose_id = "RHEL-7.9-20200917.0"
    if "rhel8" in rhel_version:
        compose_id = "RHEL-8.7.0"
    return compose_id


def beaker_args_define(args):
    """
    Define the necessary args to call the utils/beaker.by
    :param args: arguments to define
    """
    args.arch = "x86_64"
    args.variant = "BaseOS"
    if "RHEL-7" in args.rhel_compose:
        args.variant = "Server"
    args.job_group = "virt-who-ci-server-group"
    args.host = args.beaker_host
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
    ret, output = ssh.runcmd(f"hammer settings set --name={name} --value={value}")
    if ret == 0 and f"Setting [{name}] updated to" in output:
        return True
    raise FailException(f"Failed to set {name}:{value} for satellite")


def satellite_manifest_upload(ssh, org, url, admin_username, admin_password):
    """
    Upload manifest to satellite by hammer command.
    :param org: organization.
    :param ssh: ssh access to satellite host.
    :param url: manifest url
    :param admin_username: username of admin account.
    :param admin_password: password of admin account.
    """
    path = "/tmp/manifest"
    ssh.runcmd(f"rm -rf {path}; mkdir -p {path}")
    ssh.runcmd(f"wget {url} -P {path}")
    ret, output = ssh.runcmd(f"ls {path}")
    if output:
        filename = f"{path}/{output.strip()}"
    else:
        raise FailException("No manifest file found")
    ssh.runcmd(f"hammer subscription delete-manifest --organization-label {org}")
    ret, _ = ssh.runcmd(
        f"hammer subscription upload "
        f"--organization-label {org} "
        f"--file {filename}"
    )
    if ret != 0:
        raise FailException("Failed to upload manifest for satellite")


def virtwho_satellite_arguments_parser():
    """
    Parse and convert the arguments from command line to parameters
    for function using, and generate help and usage messages for
    each arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--satellite", required=True, help="Such as: 6.13-cdn-rhel8, 6.14-repo-rhel8"
    )
    parser.add_argument(
        "--server",
        default=config.satellite.server,
        required=False,
        help="ip/fqdn, default to the [satellite]:server in virtwho.ini, "
        "will install a new system if no server provide.",
    )
    parser.add_argument(
        "--ssh-username",
        default=config.satellite.ssh_username,
        required=False,
        help="Username to access the server, "
        "default to the [satellite]:ssh_username in virtwho.ini",
    )
    parser.add_argument(
        "--ssh-password",
        default=config.satellite.ssh_password,
        required=False,
        help="Password to access the server, "
        "default to the [satellite]:ssh_password in virtwho.ini",
    )
    parser.add_argument(
        "--admin-username",
        default=config.satellite.username,
        required=False,
        help="Account name for the satellite administrator, "
        "default to the [satellite]:username in virtwho.ini",
    )
    parser.add_argument(
        "--admin-password",
        default=config.satellite.password,
        required=False,
        help="Account password for the satellite administrator, "
        "default to the [satellite]:password in virtwho.ini",
    )
    parser.add_argument(
        "--beaker-host",
        default="%dell-per740-69-vm%",
        required=False,
        help="Define/filter system as hostrequire. Such as: %hp-dl360g9-08-vm%",
    )
    parser.add_argument(
        "--sca",
        default="enable",
        required=False,
        help="SCA mode, disable/enable",
    )
    parser.add_argument(
        "--snap", required=False, help="Satellite snap version, such as '5.0', '6.0'"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = virtwho_satellite_arguments_parser()
    satellite_deploy_for_virtwho(args)
