#!/usr/bin/env python3

from . import utils
import os
from .commands import *  # noqa
import pkg_resources

for ep in pkg_resources.iter_entry_points(group='kostka'):
    ep.load()

cli = utils.cli
os.chdir(os.path.dirname(utils.__file__))

if __name__ == '__main__':
    utils.cli()
