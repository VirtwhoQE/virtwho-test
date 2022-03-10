#!/usr/bin/python

import os
import sys
import argparse

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(os.path.split(rootPath)[0])

from virtwho.settings import config


def virtwho_ini_props_update(args):
    """
    Update the properties of virtwho.ini for testing
    """
    if args.section and args.option:
        config.update(args.section, args.option, args.value)


def arguments_parser():
    """
    Parse and convert the arguments from command line to parameters
    for function using, and generate help and usage messages for
    each arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--section',
        default=None,
        required=False)
    parser.add_argument(
        '--option',
        default=None,
        required=False)
    parser.add_argument(
        '--value',
        default=None,
        required=False)
    return parser.parse_args()


if __name__ == "__main__":
    args = arguments_parser()
    virtwho_ini_props_update(args)
