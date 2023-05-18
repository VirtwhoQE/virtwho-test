import json
import argparse
import os
import sys

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from configparser import ConfigParser


def ini2json(args):
    """
    Translate ini file to json file.
    """
    d = {}
    cfg = ConfigParser()
    cfg.read(args.ini_file)
    for section in cfg.sections():
        d[section] = dict(cfg.items(section))
    with open(args.json_file, "w") as f:
        json.dump(d, f)


def arguments_parser():
    """
    Parse and convert the arguments from command line to parameters
    for function using, and generate help and usage messages for
    each arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--ini-file", required=True, help="The initial .ini file path")
    parser.add_argument("--json-file", required=True, help="The target .json file path")
    return parser.parse_args()


if __name__ == "__main__":
    args = arguments_parser()
    ini2json(args)
