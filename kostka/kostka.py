#!/usr/bin/env python3

from . import utils
import os
from .commands import *  # noqa

cli = utils.cli
os.chdir(os.path.dirname(utils.__file__))

if __name__ == '__main__':
    utils.cli()
