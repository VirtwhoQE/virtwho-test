import os
import argparse
import re
import subprocess
import sys

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from virtwho import logger, config, FailException


def polarion_test_run_upload(args):
    """
    Upload the test results to Polarion.
    Requires curl and betelgeuse pypi package installed
    """
    results_xml = f"{args.directory}/results.xml"
    polarion_xml = f"{args.directory}/polarion_testrun.xml"
    betelgeuse_xml_file_transform(results_xml, polarion_xml)
    xml_file_testrun_id_remove(polarion_xml)
    polarion_xml_file_import(polarion_xml)


def betelgeuse_xml_file_transform(xml_file, output_xml_file):
    """
    Transform the original xml file by betelgeuse to match the polarion request.
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
        f'--custom-fields jenkinsjobs="{args.jenkinsjobs}" '
        f'--custom-fields logs="{args.jenkinsjobs}artifact/virtwho-test/logs/" '
        f'--custom-fields notes="{args.notes}" '
        f'--test-run-template-id="{args.template_id}" '
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


def xml_file_testrun_id_remove(xml_file):
    """
    Remove the testrun id property to use the default id of Polarion
    """
    with open(xml_file, "r+") as f:
        contents = f.read()
        res = re.findall(
            r'<property name="polarion-testrun-id" value="test-run-\d{10,}" />',
            contents,
        )
        contents = contents.replace(res[0], "")
        f.seek(0)
        f.write(contents)
        f.truncate()
        f.close()


def polarion_xml_file_import(polarion_xml_file):
    """
    Import the xml file to Polarion to create testrun.
    :param polarion_xml_file: the polarion xml file that match the polarion format
    """
    import_url = f"{args.url}/import/xunit"
    # testrun_url = f"{args.url}/#/project/{args.project}"
    cmd = (
        f"curl -k -u {args.username}:{args.password} -X POST -F "
        f"file=@{polarion_xml_file} {import_url}"
    )
    output = os.popen(cmd).read()
    logger.info(f"\n{cmd}")
    logger.info(output)
    if "error-message" not in output:
        # testrun = f"{testrun_url}/testrun?id={testrun_id}"
        logger.info(f"Successed to import xml to polarion")
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
        "--template-id", required=False, default="", help="The testrun template id"
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
