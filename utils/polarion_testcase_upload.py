import json
import os
import subprocess
import argparse
import time
import sys

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from virtwho import logger, FailException


def polarion_test_case_upload(args):
    """
    Upload the test cases to Polarion.
    Requires curl and betelgeuse pypi package installed
    """
    xml_file_generate()
    xml_file_upload()
    log_analyzer(job_id_get())


def xml_file_generate():
    """
    Use Betelgeuse to generate testcases xml file.
    Reference: https://betelgeuse.readthedocs.io/en/latest/
    """
    cmd = (
        f"betelgeuse test-case "
        f"--automation-script-format {args.automation_script_format} "
        f"{args.test_directory} "
        f"{args.project} "
        f"{args.xml_file}"
    )
    logger.info(cmd)
    ret, _ = subprocess.getstatusoutput(cmd)
    _, output = subprocess.getstatusoutput(f"ls {args.xml_file}")
    if ret == 0 and args.xml_file in output:
        logger.info(f"Succeeded to generate test case xml file")
    else:
        raise FailException(f"Failed to generate test case xml file")


def xml_file_upload():
    """
    Upload the xml file to Polarion
    """
    cmd = (
        f"curl -k "
        f"-u {args.username}:{args.password} "
        f"-X POST -F file=@{args.xml_file} "
        f"{args.url} > {args.log_file}"
    )
    logger.info(cmd)
    ret, output = subprocess.getstatusoutput(cmd)
    time.sleep(60)
    if ret == 0:
        logger.info(f"Finished the upload step")
    else:
        raise FailException(f"Failed the upload step")


def job_id_get():
    """
    Get the job id of polarion upload
    """
    ret, output = subprocess.getstatusoutput(
        "cat %s | awk '{print $4}' | awk '$1=$1'" % args.log_file
    )
    if ret == 0:
        logger.info(f"Succeeded to get the polarion job id: {output}")
        return output
    raise FailException("Fail to get polarion job id")


def log_analyzer(job_id):
    """
    Analyse the log file got from polarion
    :param job_id: polarion job id
    """
    ret, output = subprocess.getstatusoutput(
        f"curl -k "
        f"-u {args.username}:{args.password} "
        f"-X GET {args.url}-log?jobId={job_id} > {args.log_file}"
    )
    if ret == 0:
        ret, output = subprocess.getstatusoutput(f"cat {args.log_file}")
        output = output.replace("&#034;", '"').replace("&#039;", "'")
        log = json.loads(
            output[output.rfind("Message Content:") + 17 : output.rfind("}") + 1],
            strict=False,
        )
        case_pass_num = 0
        case_fail_num = 0
        log_url = log["log-url"]
        case_list = log["import-testcases"]
        for i in range(len(case_list)):
            case_status = case_list[i]["status"]
            if case_status == "passed":
                case_pass_num += 1
            else:
                case_fail_num += 1
        case_total_num = case_pass_num + case_fail_num
        logger.info(
            f"Total uploading case number: {case_total_num}\n"
            f"Passed uploading case number: {case_pass_num}\n"
            f"Failed uploading case number: {case_fail_num}\n"
            f"Log URL: {log_url}"
        )
        if case_fail_num > 0:
            raise FailException("Failed to upload all test cases to polarion")
    else:
        raise FailException("Failed to get the polarion job log")


def arguments_parser():
    """
    Parse and convert the arguments from command line to parameters
    for function using, and generate help and usage messages for
    each arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url",
        required=False,
        default="https://polarion.engineering.redhat.com/polarion/import/testcase",
        help="The polarion url to import test cases",
    )
    parser.add_argument("--username", required=True, help="The polarion account")
    parser.add_argument(
        "--password", required=True, help="The polarion account password"
    )
    parser.add_argument(
        "--project", required=True, help="The project id, such as 'RHELSS'"
    )
    parser.add_argument(
        "--test-directory",
        required=False,
        default="tests/",
        help="The directory of the test cases",
    )
    parser.add_argument(
        "--xml-file",
        required=False,
        default="temp/polarion_testcase.xml",
        help="The path to store the test cases xml file",
    )
    parser.add_argument(
        "--automation-script-format",
        required=True,
        help="Example: https://github.com/.../tree/main/tests/{path}#{line_number}",
    )
    parser.add_argument(
        "--log-file",
        required=False,
        default="temp/polarion_testcase.log",
        help="The path to store the result log file",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = arguments_parser()
    polarion_test_case_upload(args)
