#!/usr/bin/python

import os
import sys
import argparse

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from virtwho.settings import Configure, TEST_DATA


def virtwho_ini_props_update(args):
    """
    Update the property of virtwho.ini for testing/using
    """
    config = Configure(TEST_DATA)
    if args.section and args.option:
        config.update(args.section, args.option, args.value)


def arguments_parser():
    """
    Parse and convert the arguments from command line to parameters
    for function using, and generate help and usage messages for
    each arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--section", default=None, required=False)
    parser.add_argument("--option", default=None, required=False)
    parser.add_argument("--value", default=None, required=False)
    return parser.parse_args()


if __name__ == "__main__":
    args = arguments_parser()
    virtwho_ini_props_update(args)


def virtwho_ini_update(section, option, value):
    """
    Update the property of virtwho.ini for testing/using
    Used to called by other functions
    """
    os.system(
        f"python3 {curPath}/properties_update.py "
        f"--section={section} "
        f"--option={option} "
        f'--value="{value}"'
    )
