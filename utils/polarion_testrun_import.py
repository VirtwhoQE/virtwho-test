import os
import argparse
import re
import subprocess
import sys

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from virtwho import logger, config, FailException
from datetime import datetime


def polarion_test_run_upload(args):
    """
    Upload the test results to Polarion.
    Requires curl and betelgeuse pypi package installed
    """
    testrun_id = testrun_id_generate()
    results_xml = f"{args.directory}/results.xml"
    # results_update_xml = f"{args.directory}/results_update.xml"
    polarion_xml = f"{args.directory}/polarion_testrun.xml"
    # xml_file_update(results_update_xml)
    betelgeuse_xml_file_transform(testrun_id, results_xml, polarion_xml)
    polarion_xml_file_import(testrun_id, polarion_xml)


def testrun_id_generate():
    """
    Generate the polarion testrun id, eg: RHSS_2023-05-30_14-16-49
    """
    create_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    testrun_id = f"{args.id}_{create_time}"
    return testrun_id


def xml_file_update(update_xml_file):
    """
    Update the original args.xml_file to a new update_xml_file to support betelgeuse
    recoganization.
    :param update_xml_file: a new xml_file.
    """
    old_file = open(f"{args.directory}/{args.xml_file}")
    lines = old_file.readlines()
    # delete the useless lines before <testsuites>
    testsuits_index = lines.index("<testsuites>\n")
    del lines[0:testsuits_index]
    newlines = []
    for line in lines:
        line = line.replace("skipped=", "skip=")
        line = line.replace("...", "")
        if "failure message=" in line:
            # delete the long and useless message info, starting from "self ="
            res = re.findall(r"^.*?self =", line)
            if res:
                line = res[0].strip("self =") + "</failure>"
            # replace &, <, >, which are not recognized by xml file
            res = re.findall(r'(?<=<failure message=").*(?="></failure>)', line)
            replace_dict = {"&": "&amp;", "<": "&lt;", ">": "&gt;"}
            if res:
                res = res[0]
                for key, value in replace_dict.items():
                    if key in res:
                        res = res.replace(key, value)
                line = '<failure message="' + res + '"></failure>'
        newlines.append(line)
    new_file = open(update_xml_file, "w")
    new_file.writelines(newlines)
    new_file.close()
    old_file.close()


def betelgeuse_xml_file_transform(testrun_id, xml_file, output_xml_file):
    """
    Transform the original xml file by betelgeuse to match the polarion request.
    :param testrun_id: polarion testrun id
    :param xml_file: the original xml file
    :param output_xml_file: the new xml file to match the polarion format
    """
    cmd = (
        f"betelgeuse test-run "
        f'--custom-fields composeid="{args.composeid}" '
        f'--custom-fields isautomated="true" '
        f'--custom-fields arch="x86_64" '
        f'--custom-fields variant="server" '
        f'--custom-fields plannedin="{args.plannedin}" '
        f'--custom-fields assignee="{args.assignee}" '
        f'--custom-fields component="{args.component}" '
        f'--custom-fields build="{args.build}" '
        f'--custom-fields subsystemteam="{args.subsystemteam}" '
        f'--custom-fields type="{args.type}" '
        f'--custom-fields jenkinsjobs="{args.jenkinsjobs}" '
        f'--custom-fields notes="{args.notes}" '
        f'--test-run-id="{testrun_id}" '
        f'--test-run-title="{args.title}" '
        f'--status="finished" '
        f'"{xml_file}" '
        f'"{args.source_code}" '
        f'"{args.username}" '
        f'"{args.project}" '
        f'"{output_xml_file}"'
    )
    logger.info(f"\n{cmd}")
    ret, output = subprocess.getstatusoutput(cmd)
    if ret != 0:
        logger.info(f"\n{output}")
        raise FailException("\nThe betelgause failed to transform the xml file.")


def polarion_xml_file_import(testrun_id, polarion_xml_file):
    """
    Import the xml file to Polarion to create testrun.
    :param testrun_id: polarion testrun id
    :param polarion_xml_file: the polarion xml file that match the polarion format
    """
    import_url = f"{args.url}/import/xunit"
    testrun_url = f"{args.url}/#/project/{args.project}"
    cmd = (
        f"curl -k -u {args.username}:{args.password} -X POST -F "
        f"file=@{polarion_xml_file} {import_url}"
    )
    output = os.popen(cmd).read()
    logger.info(f"\n{cmd}")
    logger.info(output)
    if "error-message" not in output:
        testrun = f"{testrun_url}/testrun?id={testrun_id}"
        logger.info(f"Successed to import xml to polarion with link:\n{testrun}")
    else:
        raise FailException("Failed to import xml to polarion")


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
        default="https://polarion.engineering.redhat.com/polarion",
        help="The polarion url to import test run",
    )
    parser.add_argument(
        "--username",
        required=False,
        default=config.polarion.username,
        help="The polarion account",
    )
    parser.add_argument(
        "--password",
        required=False,
        default=config.polarion.password,
        help="The polarion account password",
    )
    parser.add_argument(
        "--project",
        required=False,
        default=config.polarion.project,
        help="The project id, such as 'RHELSS'",
    )
    parser.add_argument(
        "--id", required=False, default="", help="The testrun id, such as: RHSS"
    )
    parser.add_argument("--title", required=True, help="The testrun title")
    parser.add_argument(
        "--assignee", required=False, default="", help="The testrun title"
    )
    parser.add_argument(
        "--composeid",
        required=False,
        default=config.job.rhel_compose,
        help="The rhel compose, such as RHEL-9.2.0-20230516.55",
    )
    parser.add_argument(
        "--component",
        required=False,
        default="",
        help="The test component, such as virt-who",
    )
    parser.add_argument(
        "--build",
        required=False,
        default=config.virtwho.package,
        help="The component build, such as virt-who-1.31.26-1.el9.noarch",
    )
    parser.add_argument(
        "--jenkinsjobs", required=False, default="", help="The jenkins build url"
    )
    parser.add_argument(
        "--plannedin", required=False, default="", help="The plans of polarion project"
    )

    parser.add_argument(
        "--subsystemteam",
        required=False,
        default="",
        help="Subsystem Team, such as: sst_subscription_virtwho",
    )
    parser.add_argument("--type", required=False, default="regression", help="")
    parser.add_argument("--notes", required=False, default="", help="The custom notes")
    parser.add_argument(
        "--xml-file",
        required=False,
        default="results.xml",
        help="The name of the results.xml file",
    )
    parser.add_argument(
        "--directory",
        required=True,
        help="The path of the test results.xml file",
    )
    parser.add_argument(
        "--source-code",
        required=False,
        default="tests",
        help="The test case source code path",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = arguments_parser()
    polarion_test_run_upload(args)
