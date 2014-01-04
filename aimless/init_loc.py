#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Creates and runs AMBER processes for aimless shooting.
"""

import ConfigParser
import logging
import os
import shutil
import sys
import optparse
import common

DEF_SKEL_LOC = os.path.join(os.path.dirname(__file__), 'skel')

# Logic #

def copy_skel(src, dest):
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