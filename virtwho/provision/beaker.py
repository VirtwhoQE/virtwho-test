#!/usr/bin/python
import random
import re
import string
import time
import os
import sys
import argparse
curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(os.path.split(rootPath)[0])

from virtwho import logger, FailException
from virtwho.settings import config
from virtwho.ssh import SSHConnect


def install_rhel_by_beaker(args):
    """
    Install rhel by submitting job to beaker with required arguments.
    Please refer to the README for usage.
    :param args:
        rhel_compose: required option, such as RHEL-7.9-20200917.0.
        arch: required option, such as x86_64, s390x, ppc64...
        variant: optional, default using BaseOS for rhel8 and later.
        job_group: optional, associate a group to this job.
        system_require:
        host_require: optional, additional <hostRequires/> for job,
            separate multiple options with commas.
    """
    random_str = ''.join(random.sample(string.digits, 4))
    job_name = f'virtwho-ci-{args.rhel_compose}({random_str})'
    ssh_client = SSHConnect(
        host=config.beaker.client,
        user=config.beaker.client_username,
        pwd=config.beaker.client_password
    )
    beaker_client_kinit(ssh_client)
    job_id = beaker_job_submit(
        ssh_client,
        job_name,
        args.rhel_compose,
        args.arch,
        args.variant,
        args.job_group,
        args.system_require,
        args.host_require,
    )
    while beaker_job_status(ssh_client, job_name, job_id):
        time.sleep(60)
    host = beaker_job_result(ssh_client, job_name, job_id)
    if host:
        config.update('satellite', 'server', host)


def beaker_job_submit(ssh, job_name, distro, arch, variant=None,
                      job_group=None, system_require=None,
                      host_require=None):
    """
    Submit beaker job by command and return the job id.
    :param ssh: ssh access of client to run command
    :param job_name: beaker job name
    :param distro: such as RHEL-7.9-20200917.0
    :param arch: x86_64, s390x, ppc64, ppc64le or aarch64
    :param variant: Server, Client, Workstation or BaseOS
    :param job_group:
    :param system_require:
    :param host_require:
    :return: beaker job id
    """
    task = ('--suppress-install-task '
            '--task /distribution/dummy '
            '--task /distribution/reservesys')
    whiteboard = f'--whiteboard="reserve host for {job_name}"'
    reserve = '--reserve --reserve-duration 259200 --priority Urgent'
    cmd = (f'bkr workflow-simple --prettyxml '
           f'{task} {whiteboard} {reserve} '
           f'--distro={distro} '
           f'--arch={arch} ')
    if variant:
        cmd += f'--variant={variant} '
    if job_group:
        cmd += f'--job-group={job_group} '
    if system_require:
        cmd += f'--hostrequire "<and><system><name op=\'like\' value=\'{system_require}\'/></system></and>" '
    if host_require:
        require_list = host_require.split(',')
        for item in require_list:
            cmd += f'--hostrequire "{item.strip()}" '
    ret, output = ssh.runcmd(cmd)
    if ret == 0 and 'Submitted' in output:
        job_id = re.findall(r"Submitted: \['(.*?)'", output)[0]
        logger.info(f'Succeeded to submit beaker job: {job_name}:{job_id}')
        return job_id
    raise FailException(f'Failed to submit beaker job {job_name}')


def beaker_job_status(ssh, job_name, job_id):
    """
    Check the beaker job status.
    :param ssh: ssh access of client to run command
    :param job_name: beaker job name
    :param job_id: beaker job id
    :return: True/False
    """
    _, output = ssh.runcmd(f'bkr job-results {job_id} --no-logs')
    status = ('Aborted', 'Completed', 'Cancelled')
    for item in status:
        if f'status="{item}"' in output:
            logger.info(f'Beaker Job:{job_name} status: {item}')
            return False
    logger.info(f'Beaker Job:{job_name} status: Pending')
    return True


def beaker_job_result(ssh, job_name, job_id):
    """
    Check the beaker job result.
    :param ssh: ssh access of client to run command
    :param job_name: beaker job name
    :param job_id: beaker job id
    :return: the completed host (hostname)
    """
    ret, output = ssh.runcmd(f'bkr job-results {job_id} --no-logs')
    if ret == 0 and 'status="Completed"' in output:
        output = re.findall(r'system="(.*?)"', output)
        if len(output) > 0:
            host = output[0]
            logger.info(f'Succeeded to install {host} for {job_name}')
            return host
    logger.error(f'No available machine found for job {job_name}')
    return None


def beaker_client_kinit(ssh):
    """
    Initiate beaker client.
    :param ssh: ssh access of client to run command
    :return: True/False
    """
    ret, output = ssh.runcmd(f'kinit -k -t {config.beaker.keytab} '
                             f'{config.beaker.principal}')
    if ret == 0:
        logger.info(f'Succeeded to initiate beaker client')
        return True
    logger.error(f'Failed to initiate beaker client')
    return False


def beaker_arguments_parser():
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
        default=None,
        help='Associate a group to the job')
    parser.add_argument(
        '--system-require',
        required=False,
        default=None,
        help='Define the system for hostrequire. '
             'Such as: %ent-02-vm%, ent-02-vm-20.lab.eng.nay.redhat.com')
    parser.add_argument(
        '--host-require',
        required=False,
        default=None,
        help='Separate multiple options with commas. '
             'Such as: hypervisor!=,memory > 7000.')
    return parser.parse_args()


if __name__ == "__main__":
    args = beaker_arguments_parser()
    install_rhel_by_beaker(args)
