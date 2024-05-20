import os
import sys

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(os.path.split(rootPath)[0])

from virtwho import logger
from virtwho.register import RHSM


def rhsm_setup_for_virtwho():
    """
    Setup sca mode for rhsm/stage candlepin account.
    """
    logger.info("+++ Start to setup the RHSM +++")
    rhsm = RHSM()
    rhsm.sca()


if __name__ == "__main__":
    rhsm_setup_for_virtwho()
