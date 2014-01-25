#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Initializes a location for running aimless shooting.  The contents
of the "skel" subdirectory is copied into the target directory.
This currently includes aimless.ini, an AimlessShooter configuration
file, an input directory, and a tpl directory.  The AimlessShooter
script expects aimless.ini to be in the current working directory.
The skell aimless.ini assumes the input directory contains the
topology and coordinates file while the tpl directory contains
all of the templates used by the script.
"""

import ConfigParser
import logging
import os
import shutil
import sys
import optparse
import common

logger = logging.getLogger(__name__)

DEF_SKEL_LOC = os.path.join(os.path.dirname(__file__), 'skel')

# Logic #

def copy_skel(src, dest):
    """Copies the contents of src to dest."""
    common.copytree(src, dest)

def parse_cmdline(argv):
    """
    Return a 2-tuple: (opts object, args list).
    `argv` is a list of arguments, or `None` for ``sys.argv[1:]``.
    """
    if argv is None:
        argv = sys.argv[1:]
    # initialize the parser object:
    parser = optparse.OptionParser(
        formatter=optparse.TitledHelpFormatter(width=78),
        add_help_option=None)

    # define options here:
    parser.add_option('-s', '--skel_dir', default=DEF_SKEL_LOC,
                      help="Specify skel directory.", metavar="SKEL")
    parser.add_option(# customized description; put --help last
                      '-h', '--help', action='help',
                      help='Show this help message and exit.')

    opts, args = parser.parse_args(argv)

    # check number of arguments, verify values, etc.:
    if len(args) == 0:
        parser.error('Please specify a location to initialize')

    # further process opts & args if necessary

    return opts, args


def main(argv=None):
    opts, args = parse_cmdline(argv)
    copy_skel(opts.skel_dir, args[0])
    return 0        # success

if __name__ == '__main__':
    status = main()
    sys.exit(status)