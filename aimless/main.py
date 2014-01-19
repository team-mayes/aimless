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
                     COORDS_KEY, calc_params, EnvError, write_tpl_files,
                     init_dir, write_text_report, write_csv_report,
                     AimlessShooter)

DEF_CFG_NAME = 'aimless.ini'
TPL_DIR_KEY = 'tpldir'
TGT_DIR_KEY = 'tgtdir'
TEXT_REPORT_KEY = 'text_report'
CSV_REPORT_KEY = 'csv_report'

TEXT_FMT = 't'
CSV_FMT = 'c'
VALID_FMTS = [TEXT_FMT, CSV_FMT]
DEF_OUT_FMTS = TEXT_FMT

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


class CfgError(Exception):
    pass

# Note that ConfigParser expects all of these values to be strings
CFG_DEFAULTS = {
    TEXT_REPORT_KEY: 'aimless_results.txt',
    CSV_REPORT_KEY: 'aimless_results.csv',
}
# Logic #


def fetch_calc_params(config):
    """
    Calculates and returns the calculation parameters based on the contents of
    the given configuration file.

    Args:
    config -- A ConfigParser-style object with a 'main' section containing
              'numpaths' and 'totalsteps' values.
    Returns:
    A map of values used for filling in the templates used for the aimless
    shooting calculations.
    """
    params = calc_params(config.getint(MAIN_SEC, TOTAL_STEPS_KEY))
    params[NUM_PATHS_KEY] = config.getint(MAIN_SEC, NUM_PATHS_KEY)
    return params


def write_tpls(config, params):
    """
    Fills the templates in the configuration's 'tpldir' and writes the results
    to the configuration's 'tgtdir'.

    config -- A ConfigParser-style object with a 'main' section containing
              'tpldir' and 'tgtdir' values.
    """
    tpl_dir = config.get(MAIN_SEC, TPL_DIR_KEY)
    if not os.path.exists(tpl_dir):
        raise EnvError("Template directory '%s' does not exist" % tpl_dir)
    tgt_dir = config.get(MAIN_SEC, TGT_DIR_KEY)
    if not os.path.exists(tgt_dir):
        os.makedirs(tgt_dir)
    write_tpl_files(tpl_dir, tgt_dir, params)


def run(config):
    """
    Extracts configuration data for the AimlessShooting run, returning the
    results of the execution.

    Arguments:
    config -- A ConfigParser-style object with the necessary sections and
    values.
    """
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
    return aims.run_calcs(num_paths)

# Command-line processing and control #


def read_config(file_loc):
    """
    Loads and returns the configuration file from the given location.

    Arguments:
    file_loc -- The location of the configuration file.
    Returns:
    A ConfigParser object containing the file's configuration data.
    """
    config = ConfigParser.ConfigParser(CFG_DEFAULTS)
    good_files = config.read(file_loc)
    if not good_files:
        logger.debug("Did not load config file %s" % file_loc)

    if not config.has_section(MAIN_SEC):
        config.add_section(MAIN_SEC)
    if not config.has_section(JOBS_SEC):
        config.add_section(JOBS_SEC)
    if not config.has_section(BASINS_SEC):
        config.add_section(BASINS_SEC)
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
    parser.add_option('-o', '--out_formats', default=DEF_OUT_FMTS,
                      help="Specify output formats (t and/or c).",
                      metavar="FMTS")
    parser.add_option('-h', '--help', action='help',
                      help='Show this help message and exit.')

    opts, args = parser.parse_args(argv)

    # check number of arguments, verify values, etc.:
    if args:
        parser.error('program takes no command-line arguments; '
                     '"%s" ignored.' % (args,))

    # further process opts & args if necessary
    for fmt in opts.out_formats:
        if fmt not in VALID_FMTS:
            parser.error("Unhandled output format '%s'\n" % fmt)

    return opts, args


def main(argv=None):
    opts, args = parse_cmdline(argv)
    config = read_config(opts.cfg_file)
    params = fetch_calc_params(config)
    write_tpls(config, params)
    pres = run(config)

    for fmt in opts.out_formats:
        if fmt.lower() == TEXT_FMT:
            with open(config.get(MAIN_SEC, TEXT_REPORT_KEY)) as txt_tgt:
                write_text_report(pres, txt_tgt)
        elif fmt.lower() == CSV_FMT:
            with open(config.get(MAIN_SEC, CSV_REPORT_KEY)) as csv_tgt:
                write_csv_report(pres, csv_tgt)
        else:
            raise CfgError("Unhandled output format '%s'" % fmt)

    return 0        # success


if __name__ == '__main__':
    status = main()
    sys.exit(status)