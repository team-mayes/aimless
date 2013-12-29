#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Creates and runs AMBER processes for aimless shooting.
"""

import ConfigParser
import logging
import os
import sys
import optparse
from aimless.aimless import (NUM_PATHS_KEY, TOTAL_STEPS_KEY, TOPO_KEY,
                             COORDS_KEY, TPL_DIR_KEY, MAIN_SEC, calc_params, EnvError, TGT_DIR_KEY, write_tpl_files)


DEF_CFG_NAME = 'aimless.ini'

# Log Setup #
# logdir = os.environ.get("LOGDIR")
# if logdir:
#     logfile = os.path.join(logdir, "jslave.log")
# else:
#     logfile = expanduser('~/.jslave/jslave.log')

# if not os.path.exists(logfile):
#     cmakedir(os.path.dirname(logfile))
#
# logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#                     filename=logfile)

logger = logging.getLogger("aimless")
logger.debug("Testing the logger")

CFG_DEFAULTS = {
    NUM_PATHS_KEY: 20,
    TOTAL_STEPS_KEY: 2500,
    TOPO_KEY: 'input/cel6a_solv.prmtop',
    COORDS_KEY: 'input/cel6amc_qmmm_tryTS.rst',
    TPL_DIR_KEY: os.path.join(os.path.dirname(__file__), 'tpl'),
    TGT_DIR_KEY: os.path.getcwd(),
}

# Logic #

def fetch_calc_params(config):
    params = dict()
    params[TOTAL_STEPS_KEY] = config.getint(MAIN_SEC, TOTAL_STEPS_KEY)
    params[NUM_PATHS_KEY] = config.getint(MAIN_SEC, NUM_PATHS_KEY)
    return calc_params(params)

def write_tpls(config, params):
    tpl_dir = config.get(MAIN_SEC, TPL_DIR_KEY)
    if not os.path.exists(tpl_dir):
        raise EnvError("Template directory '%s' does not exist" % tpl_dir)
    tgt_dir = config.get(MAIN_SEC, TGT_DIR_KEY)
    if not os.path.exists(tgt_dir):
        os.makedirs(tgt_dir)
    write_tpl_files(tpl_dir, tgt_dir, params)

# Command-line processing and control #

def read_config(file_loc):
    config = ConfigParser.ConfigParser(defaults=CFG_DEFAULTS)
    good_files = config.read(file_loc)
    if not good_files:
        logger.debug("Did not load config file %s" % file_loc)

    if not config.has_section(MAIN_SEC):
        config.add_section(MAIN_SEC)

    return config

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
    parser.add_option('-c', '--cfg_file', default=DEF_CFG_NAME,
                      help="Specify config file location.", metavar="CFG")
    parser.add_option(# customized description; put --help last
                      '-h', '--help', action='help',
                      help='Show this help message and exit.')

    opts, args = parser.parse_args(argv)

    # check number of arguments, verify values, etc.:
    if args:
        parser.error('program takes no command-line arguments; '
                     '"%s" ignored.' % (args,))

    # further process opts & args if necessary

    return opts, args


def main(argv=None):
    opts, args = parse_cmdline(argv)
    config = read_config(opts.cfg_file)
    params = fetch_calc_params(config)
    write_tpls(config, params)
    return 0        # success

if __name__ == '__main__':
    status = main()
    sys.exit(status)