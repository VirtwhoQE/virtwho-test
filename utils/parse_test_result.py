import argparse
import os
import sys

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from xml.dom import minidom
from properties_update import virtwho_ini_props_update


def test_result_parser(args):
    """
    Parse the test result in xml file produced by Jenkins.
    Then update the test result to virtwho.ini.
    """
    dom = minidom.parse(args.xml_file)
    test_suite = dom.getElementsByTagName("testsuite")
    total_case = int(test_suite[0].getAttribute("tests"))
    failed_case = int(test_suite[0].getAttribute("errors")) + int(
        test_suite[0].getAttribute("failures")
    )
    skipped_case = int(test_suite[0].getAttribute("skipped"))
    passed_case = total_case - failed_case - skipped_case
    # Update the virtwho.in
    print(
        f"The test result is:\n"
        f"total_case: {total_case}\n"
        f"passed_case: {passed_case}\n"
        f"failed_case: {failed_case}\n"
        f"skipped_case: {skipped_case}\n"
    )
    args.section = "report"
    virtwho_ini_props = {
        "total_case": str(total_case),
        "passed_case": str(passed_case),
        "failed_case": str(failed_case),
        "skipped_case": str(skipped_case),
    }
    for args.option, args.value in virtwho_ini_props.items():
        virtwho_ini_props_update(args)


def arguments_parser():
    """
    Parse and convert the arguments from command line to parameters
    for function using, and generate help and usage messages for
    each argument.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--xml-file", required=True, default="", help="The path of xml file"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = arguments_parser()
    test_result_parser(args)
