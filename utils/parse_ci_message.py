import json
import os
import re
import argparse
import sys
sys.path.append(".")

from virtwho import logger, FailException
from virtwho.settings import config


def umb_ci_message_parser(args):
    """
    Parse the umb ci message to a dic
    """
    ci_msg_dic = dict()
    ci_msg = args.gating_msg
    if not ci_msg:
        raise FailException("Failed to get the UMB CI MESSAGE")
    ci_msg = json.loads(ci_msg)
    if "info" in ci_msg.keys():
        build_id = ci_msg["info"]["build_id"]
        task_id = ci_msg["info"]["task_id"]
        owner_name = ci_msg["info"]["owner_name"]
        source = ci_msg["info"]["source"]
    else:
        build_id = re.findall(r'"build_id":(.*?),', ci_msg)[-1].strip()
        task_id = re.findall(r'"task_id":(.*?),', ci_msg)[-1].strip()
        owner_name = re.findall(r'"owner_name":(.*?),', ci_msg)[-1].strip()
        source = re.findall(r'"source":(.*?),', ci_msg)[-1].strip()
    brew_build_url = f"{config.virtwho.brew}/brew/buildinfo?buildID={build_id}"
    output = os.popen(f"curl -k -s -i {brew_build_url}").read()
    pkg_url = re.findall(r'<a href="https://(.*?).noarch.rpm">download</a>', output)[-1]
    if not pkg_url:
        raise FailException("no package url found")
    items = pkg_url.split("/")
    rhel_release = items[3]
    ci_msg_dic["build_id"] = build_id
    ci_msg_dic["task_id"] = task_id
    ci_msg_dic["owner_name"] = owner_name
    ci_msg_dic["source"] = source
    ci_msg_dic["pkg_url"] = "http://" + pkg_url + ".noarch.rpm"
    ci_msg_dic["pkg_name"] = items[5]
    ci_msg_dic["pkg_version"] = items[6]
    ci_msg_dic["pkg_release"] = items[7]
    ci_msg_dic["pkg_arch"] = items[8]
    ci_msg_dic["pkg_nvr"] = items[9]
    ci_msg_dic["rhel_release"] = rhel_release
    logger.info(f"Succeeded to parse the ci-message:\n{ci_msg_dic}\n")
    return ci_msg_dic


def arguments_parser():
    """
    Parse and convert the arguments from command line to parameters
    for function using, and generate help and usage messages for
    each argument.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--gating-msg", required=True, default="", help="Json ci message got by umb"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = arguments_parser()
    umb_ci_message_parser(args)
