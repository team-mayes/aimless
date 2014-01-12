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
from aimless import (NUM_PATHS_KEY, TOTAL_STEPS_KEY, TOPO_KEY,
                     COORDS_KEY, calc_params, EnvError, write_tpl_files, init_dir)
from aimless import NUMNODES_KEY, NUMCPUS_KEY, WALLTIME_KEY, MAIL_KEY, AimlessShooter

DEF_CFG_NAME = 'aimless.ini'
TPL_DIR_KEY = 'tpldir'
TGT_DIR_KEY = 'tgtdir'

# Config Sections #
MAIN_SEC = 'main'
JOBS_SEC = 'jobs'
BASINS_SEC = 'basins'

# TODO: Consider merging into aimless

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

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger("aimless_main")
logger.debug("Testing the logger")

# # Note that ConfigParser expects all of these values to be strings
# CFG_DEFAULTS = {
#     NUM_PATHS_KEY: '20',
#     TOTAL_STEPS_KEY: '2500',
#     TOPO_KEY: 'input/cel6a_solv.prmtop',
#     COORDS_KEY: 'input/cel6amc_qmmm_tryTS.rst',
#     TPL_DIR_KEY: 'tpl',
#     TGT_DIR_KEY: os.getcwd(),
#     NUMNODES_KEY: '1',
#     NUMCPUS_KEY: '8',
#     WALLTIME_KEY: '999:00:00',
#     MAIL_KEY: 'hmayes@hmayes.com',
# }
#
# JOBS_KEYS = [NUMNODES_KEY, NUMCPUS_KEY, WALLTIME_KEY, MAIL_KEY]

# Logic #

def fetch_calc_params(config):
    params = calc_params(config.getint(MAIN_SEC, TOTAL_STEPS_KEY))
    params[NUM_PATHS_KEY] = config.getint(MAIN_SEC, NUM_PATHS_KEY)
    return params


def write_tpls(config, params):
    tpl_dir = config.get(MAIN_SEC, TPL_DIR_KEY)
    if not os.path.exists(tpl_dir):
        raise EnvError("Template directory '%s' does not exist" % tpl_dir)
    tgt_dir = config.get(MAIN_SEC, TGT_DIR_KEY)
    if not os.path.exists(tgt_dir):
        os.makedirs(tgt_dir)
    write_tpl_files(tpl_dir, tgt_dir, params)


def run(config):
    num_paths = config.getint(MAIN_SEC, NUM_PATHS_KEY)
    tgt_dir = config.get(MAIN_SEC, TGT_DIR_KEY)
    tpl_dir = config.get(MAIN_SEC, TPL_DIR_KEY)
    coords_file = config.get(MAIN_SEC, COORDS_KEY)
    init_dir(tgt_dir, coords_file)
    bparams = dict()
    for bkey, bval in config.items(BASINS_SEC):
        bparams[bkey] = float(bval)
    topo_file = config.get(MAIN_SEC, TOPO_KEY)
    aims = AimlessShooter(tpl_dir, tgt_dir, topo_file,
                          dict(config.items(JOBS_SEC)), bparams)
    aims.run_calcs(num_paths)

# Command-line processing and control #

def read_config(file_loc):
    config = ConfigParser.ConfigParser()
    good_files = config.read(file_loc)
    if not good_files:
        logger.debug("Did not load config file %s" % file_loc)

    if not config.has_section(MAIN_SEC):
        config.add_section(MAIN_SEC)
    if not config.has_section(JOBS_SEC):
        config.add_section(JOBS_SEC)

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
    run(config)
    return 0        # success


if __name__ == '__main__':
    status = main()
    sys.exit(status)