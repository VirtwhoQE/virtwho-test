import os
import re
import time
import argparse
import sys
import subprocess
from lxml import etree
from funcy import first
from .beaker_types import Report

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from virtwho import logger, FailException
from virtwho.settings import config

"""
The function is wrapper to unify a way to call a command.
   - using a remote machine (by ssh)
   - using localhost (by subprocess)
"""


def run_cmd(cmd):
    # ssh_client = SSHConnect(
    #     host=config.beaker.client,
    #     user=config.beaker.client_username,
    #     pwd=config.beaker.client_password,
    # )
    # #beaker_client_kinit(ssh_client, config.beaker.keytab, config.beaker.principal)
    # ssh.runcmd(cmd)
    logger.info(f"subprocess cmd >>> {cmd}")
    process = subprocess.run(cmd, shell=True, capture_output=True, encoding="UTF-8")
    logger.info("<<< stdout\n{}".format(process.stdout))
    return (process.returncode, process.stdout)


def install_host_by_beaker(args):
    """
    Install rhel/fedora os by submitting job to beaker with required arguments.
    Please refer to the utils/README for usage.
    """
    job_name = f"virtwho-{args.distro}"

    start_time = time.time()
    current_time = time.time()
    time_span = (config.beaker.get("timeout") and float(config.beaker.timeout)) or (
        2 * 3600.0
    )  # 2 hours

    job_id = beaker_job_submit(
        job_name,
        args.distro,
        args.arch,
        args.variant,
        args.fips,
        args.job_group,
        args.host,
        args.host_type,
        args.host_require,
        args.reserve_duration,
    )
    report = beaker_job_report(job_id)
    logger.info(f"{report}")
    while not (report.is_reserved or report.is_completed_except_reservesysTask):
        time.sleep(60)
        report = beaker_job_report(job_id)
        logger.info(f"{report}")
        current_time = time.time()
        if (current_time - start_time) > time_span:
            raise FailException(
                f"Failed to get beaker job ready in {time_span / 3600.0} hours"
            )
    if report.job.status in ("Aborted", "Cancelled"):
        raise FailException(f"Failed to submit beaker job {job_name}")

    host = report.job.hostname
    logger.info(f"Succeeded to install {host} for {job_name}")
    if host:
        logger.info(f"Succeeded to install {args.distro} by beaker ({host})")
        return host

    # the right way to exit this function is 'return' statement in the 'while' loop.
    raise FailException(f"Failed to install {args.distro} by beaker")


def beaker_job_submit(
    job_name,
    distro,
    arch,
    variant=None,
    fips=False,
    job_group=None,
    host=None,
    host_type=None,
    host_require=None,
    reserve_duration=None,
):
    """
    Submit beaker job by command and return the job id.
    :param job_name: beaker job name
    :param distro: such as RHEL-7.9-20200917.0
    :param arch: x86_64, s390x, ppc64, ppc64le or aarch64
    :param variant: Server, Client, Workstation or BaseOS
    :param job_group: associate a group to this job
    :param host: define/filter system as hostrequire
    :param host_type: virtual, physical
    :param host_require: optional, additional <hostRequires/> for job
    :return: beaker job id
    """
    task = (
        "--task /distribution/check-install "
        + "--task /tools/beaker-rhsm/Install/rhsm-qe-keys "
        + ("--task /distribution/fips/setup-fips-enabled " if fips else "")
        + "--task /distribution/reservesys "
    )
    install_pkg = "beakerlib"
    ks_meta = "method=nfs harness='restraint-rhts beakerlib beakerlib-redhat'"
    whiteboard = f'--whiteboard="reserve host for a job {job_name}"'
    reserve = "--reserve  --priority Urgent" + (
        (reserve_duration and f" --reserve-duration {reserve_duration}")
        or (
            config.beaker.get("reserve_duration")
            and f" --reserve-duration {config.beaker.get('reserve_duration')}"
        )
        or ""
    )
    cmd = (
        f"bkr workflow-simple --prettyxml "
        f"--username {config.beaker.username} "
        f"--password {config.beaker.password} "
        f"{task} {whiteboard} {reserve} "
        f"--distro={distro} "
        f"--arch={arch} "
        f"--install={install_pkg} "
        f'--ks-meta="{ks_meta}" '
    )
    if variant:
        cmd += f"--variant={variant} "
    if job_group:
        cmd += f"--job-group={job_group} "
    if host:
        cmd += (
            f"--hostrequire \"<and><system><name op='like' "
            f"value='{host}'/></system></and>\" "
        )
    if host_type:
        if host_type.lower() == "virtual":
            cmd += f'--hostrequire "hypervisor!=" '
        else:
            cmd += f'--hostrequire "hypervisor=" '
    if host_require:
        require_list = host_require.split(",")
        for item in require_list:
            cmd += f'--hostrequire "{item.strip()}" '
    ret, output = run_cmd(cmd)
    if ret == 0 and "Submitted" in output:
        job_id = re.findall(r"Submitted: \['(.*?)'", output)[0]
        logger.info(f"Succeeded to submit beaker job: {job_name}:{job_id}")
        return job_id
    raise FailException(f"Failed to submit beaker job {job_name}")


def beaker_job_status(job_name, job_id):
    """
    Check the beaker job status.
    :param job_name: beaker job name
    :param job_id: beaker job id
    :return: True/False
    """

    def status_from_xml(xml):
        root = etree.XML(xml)
        elements = root.xpath("/job/@status")
        return first(elements)

    auth_args = (
        f"--username {config.beaker.username} " f"--password {config.beaker.password} "
    )
    _, output = run_cmd(f"bkr job-results {job_id} {auth_args} --no-logs")
    status = status_from_xml(output)
    logger.info(f"Beaker Job:{job_name} status: {status}")
    return status


def beaker_job_result(job_name, job_id):
    """
    Check the beaker job result.
    :param job_name: beaker job name
    :param job_id: beaker job id
    :return: the completed host (hostname)
    """
    auth_args = (
        f"--username {config.beaker.username} " f"--password {config.beaker.password} "
    )
    ret, output = run_cmd(f"bkr job-results {job_id} {auth_args} --no-logs")
    if ret == 0:

        def hostname_from_xml(xml):
            root = etree.XML(xml)
            elements = root.xpath("/job/recipeSet/recipe/@system")
            return first(elements)

        host = hostname_from_xml(output)
        logger.info(f"Succeeded to install {host} for {job_name}")
        return host
    logger.error(f"No available machine found for job {job_name}")
    return None


def beaker_job_report(job_id):
    """
    Check the beaker job status.
    :param job_name: beaker job name
    :param job_id: beaker job id
    :return: Report
    """
    auth_args = (
        f"--username {config.beaker.username} " f"--password {config.beaker.password} "
    )
    _, output = run_cmd(f"bkr job-results {job_id} {auth_args} --no-logs")
    report = Report.from_beaker_results(output)
    return report


def beaker_client_kinit(keytab, principal):
    """
    Initiate beaker client.
    :param keytab: jenkins keytab
    :param principal: jenkins principal
    :return: True/False
    """
    ret, output = run_cmd(f"kinit -k -t {keytab} {principal}")
    if ret == 0:
        logger.info(f"Succeeded to initiate beaker client")
        return True
    logger.error(f"Failed to initiate beaker client")
    return False


def beaker_arguments_parser():
    """
    Parse and convert the arguments from command line to parameters
    for function using, and generate help and usage messages for
    each arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--distro",
        required=True,
        help="Such as: RHEL-8.0-20181005.1, Fedora-40-20240419.n.0",
    )
    parser.add_argument(
        "--variant",
        required=False,
        default=None,
        help="One of [Server, Client, Workstation, BaseOS]. "
        "Unnecessary for RHEL-8 and later, default using BaseOS.",
    )
    parser.add_argument(
        "--arch",
        required=False,
        default="x86_64",
        help="One of [x86_64, s390x, ppc64, ppc64le, aarch64], default is x86_64.",
    )
    parser.add_argument(
        "--job-group",
        required=False,
        default=None,
        help="Associate a group to the job based on the requirement",
    )
    parser.add_argument(
        "--host-type",
        required=False,
        default=None,
        help="Define the system type as hostrequire. " "Such as: physical or virtual",
    )
    parser.add_argument(
        "--host",
        required=False,
        default=None,
        help="Define/filter system as hostrequire. "
        "Such as: %%ent-02-vm%%, ent-02-vm-20.lab.eng.nay.redhat.com",
    )
    parser.add_argument(
        "--host-require",
        required=False,
        default=None,
        help="Separate multiple options with commas. "
        "Such as: labcontroller=lab.example.com, memory > 7000",
    )
    parser.add_argument(
        "--reserve-duration",
        required=False,
        default=config.beaker.get("reserve_duration", "259200"),
        help="A time to keep a machine reservered (in seconds). "
        " a default value is 259200 (3days)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = beaker_arguments_parser()
    install_host_by_beaker(args)
