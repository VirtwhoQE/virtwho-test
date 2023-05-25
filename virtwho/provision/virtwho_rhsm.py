import argparse
import os
import sys

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(os.path.split(rootPath)[0])

from virtwho import logger
from virtwho.register import RHSM


def rhsm_setup_for_virtwho(args):
    """
    Setup sca mode for rhsm/stage candlepin account.
    """
    logger.info("+++ Start to setup the RHSM +++")
    rhsm = RHSM()
    rhsm.sca(sca=args.sca)


def virtwho_rhsm_arguments_parser():
    """
    Parse and convert the arguments from command line to parameters
    for function using, and generate help and usage messages for
    each arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sca",
        default="enable",
        required=False,
        help="SCA mode, disable/enable",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = virtwho_rhsm_arguments_parser()
    rhsm_setup_for_virtwho(args)
