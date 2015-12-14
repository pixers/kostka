#!/usr/bin/env python3

from .utils import cli
import os
from .commands import *  # noqa

if __name__ == '__main__':
    os.chdir(os.path.dirname(utils.__file__))
    cli()
