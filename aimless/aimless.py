#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Creates and runs AMBER processes for aimless shooting.

Logs go to ~/.jslave/jslave.log by default.  You may set the LOGDIR environment
variable to specify another log directory location.  Setting the LOGTERM
environment variable to any value will send all log messages to standard error.

Log levels are DEBUG by default.  Change the llvl value to another value if
you would prefer a different minimum log level.
"""

import ConfigParser
from ConfigParser import NoOptionError
import csv
import logging
from logging.handlers import RotatingFileHandler
import os
from os.path import expanduser
import random
import shutil
from string import Template
import sys
import time
import datetime
import math
from common import enum, cmakedir
from torque import TorqueJob, TorqueSubmissionHandler, is_running
import optparse

TEN_MB = 10485760
# Log Setup #
lfmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
llvl = logging.DEBUG
if os.environ.get("LOGTERM"):
    hdlr = logging.StreamHandler()
else:
    logdir = os.environ.get("LOGDIR")
    if logdir:
        logfile = os.path.join(logdir, "jslave.log")
    else:
        logfile = expanduser('~/.jslave/jslave.log')

    if not os.path.exists(logfile):
        cmakedir(os.path.dirname(logfile))
    hdlr = RotatingFileHandler(logfile, maxBytes=TEN_MB, backupCount=5)
hdlr.setLevel(llvl)
hdlr.setFormatter(lfmt)
rlogger = logging.getLogger()
rlogger.setLevel(llvl)
rlogger.addHandler(hdlr)

logger = logging.getLogger(__name__)

# Constants #
RES_DIR_FMT = "\t%-8s: %s%s"
SUM_FMT = "%-8s: %2d%s"
ACC_KEY = "accepted"
DEF_WAIT_SECS = 10
TSTAMP_FMT = '%Y-%m-%d %H:%M:%S'
FLOAT_FMT = " % 11.7f"

# Basin Constants #
# Three possible basin results
BRES = enum(A='A', B='B', INC='I')
BASIN_FWD_KEY = 'forward'
BASIN_BACK_KEY = 'backward'
RC1_FWD_KEY = 'RC1fw'
RC1_BACK_KEY = 'RC1bw'
RC2_FWD_KEY = 'RC2fw'
RC2_BACK_KEY = 'RC2bw'
RC1_LOW_A_KEY = 'RC1loA'
RC1_HIGH_A_KEY = 'RC1hiA'
RC2_LOW_A_KEY = 'RC2loA'
RC2_HIGH_A_KEY = 'RC2hiA'
RC1_LOW_B_KEY = 'RC1loB'
RC1_HIGH_B_KEY = 'RC1hiB'
RC2_LOW_B_KEY = 'RC2loB'
RC2_HIGH_B_KEY = 'RC2hiB'

# Shooter Resources #
XONE_RST = "x1.rst"
XTWO_RST = "x2.rst"
SHOOTER_RST = "shooter.rst"
FWD_RST_NAME = "forward.rst"
BACK_RST_NAME = "backward.rst"
POSTDT_RST_NAME = "postdt.rst"
POSTFWD_RST_NAME = "postforward.rst"
POSTBACK_RST_NAME = "postbackward.rst"
AMBER_JOB_TPL = 'amber_job.tpl'
OUT_DIR = 'output'

# Constant Files #
BACK_CONS_NAME = "cons_back.dat"
FWD_CONS_NAME = "cons_fwd.dat"
DT_CONS_NAME = "cons_dt.dat"

# Directional Input Files #
BACK_IN_NAME = "inbackward.in"
FWD_IN_NAME = "inforward.in"
DT_IN_NAME = "indt.in"
STARTER_IN_NAME = "instarter.in"

# Directional Output Files #
BACK_OUT_NAME = "backward.out"
FWD_OUT_NAME = "forward.out"
DT_OUT_NAME = "dt.out"
STARTER_OUT_NAME = "starter.out"

# MDCRD Files #
BACK_MDCRD_NAME = "backward.mdcrd"
FWD_MDCRD_NAME = "forward.mdcrd"
DT_MDCRD_NAME = "dt.mdcrd"
STARTER_MDCRD_NAME = "starter.mdcrd"

# Config Keys #
NUM_PATHS_KEY = 'numpaths'
TOTAL_STEPS_KEY = 'totalsteps'
BW_STEPS_KEY = 'bwsteps'
FW_STEPS_KEY = 'fwsteps'
DT_STEPS_KEY = 'dtsteps'
BW_OUT_KEY = 'bwout'
FW_OUT_KEY = 'fwout'
DT_OUT_KEY = 'dtout'
TOPO_KEY = 'topology'
COORDS_KEY = 'coordinates'
SHOOTER_KEY = 'shooter'
DIR_RST_KEY = 'dir_rst'
MDCRD_KEY = 'mdcrd'
NUMNODES_KEY = 'numnodes'
NUMCPUS_KEY = 'numcpus'
WALLTIME_KEY = 'walltime'
MAIL_KEY = 'mail'
INFILE_KEY = 'infile'
OUTFILE_KEY = 'outfile'

# Cleanup #
# Files generated by a path run
GEN_FILES = [BACK_OUT_NAME, FWD_OUT_NAME, DT_OUT_NAME, STARTER_OUT_NAME,
             BACK_MDCRD_NAME, FWD_MDCRD_NAME, DT_MDCRD_NAME, STARTER_MDCRD_NAME,
             BACK_CONS_NAME, FWD_CONS_NAME, DT_CONS_NAME]

# Exceptions #


class TemplateError(Exception):
    pass


class EnvError(Exception):
    pass

# Logic #


def calc_params(total_steps):
    """Returns a dict with calculated values based on the given number of total
    steps.
    """
    results = {TOTAL_STEPS_KEY: total_steps, BW_STEPS_KEY: total_steps / 2,
               FW_STEPS_KEY: total_steps / 2, DT_STEPS_KEY: total_steps / 100}
    results[BW_OUT_KEY] = results[BW_STEPS_KEY] - 1
    results[FW_OUT_KEY] = results[FW_STEPS_KEY] - 1
    results[DT_OUT_KEY] = results[DT_STEPS_KEY] - 1
    return results

# Associates the template with the target file name and a description of its purpose.
TPL_LIST = [
    ("cons.tpl", "cons.rst",
     "force constants are zero - this is just to get final bond lengths"),
    ("instarter.tpl", STARTER_IN_NAME,
     "generate the velocities for this shooting point"),
    ("indt.tpl", DT_IN_NAME, "Change in time for the trajectory"),
    ("inforward.tpl", FWD_IN_NAME, "forward portion of the trajectory"),
    ("inbackward.tpl", BACK_IN_NAME, "backward portion of the trajectory"),
]


def write_tpl_files(tpl_dir, tgt_dir, params):
    """Writes the templates in tpl_dir to tgt_dir using params as the source
    for template values

    tpl_dir -- The directory containing the templates.
    tgt_dir -- The target directory for the filled templates.
    params -- A dict of parameters to use when filling the templates.
    """
    for tpl_name, tgt_name, tpl_desc in TPL_LIST:
        tpl_loc = os.path.join(tpl_dir, tpl_name)
        try:
            with open(tpl_loc, 'r') as tpl_file:
                tpl = Template(tpl_file.read())
                result = tpl.safe_substitute(params)
                tgt_loc = os.path.join(tgt_dir, tgt_name)
                try:
                    with open(tgt_loc, 'w') as tgt_file:
                        tgt_file.write(result)
                except (OSError, IOError) as e:
                    raise EnvError(
                        "Couldn't write target '%s': %s" % (tgt_loc, e))
        except (OSError, IOError) as e:
            raise TemplateError(
                "Couldn't read template '%s' (this template creates '%s' for '%s'): %s" % (
                    tpl_loc, tgt_name, tpl_desc, e))


def init_dir(tgt_dir, coords_loc):
    """Copies the coordinates location to x1 and x2."""
    shutil.copy2(coords_loc, os.path.join(tgt_dir, XONE_RST))
    shutil.copy2(coords_loc, os.path.join(tgt_dir, XTWO_RST))


def write_text_report(pres, tgt=sys.stdout):
    """Creates a human-readable plain text report for the given path results.

    Positional arguments:
    pres -- The path results.
    Keyword arguments:
    tgt -- The target to write to (stdout by default)
    """
    acc_count = 0
    aa_count = 0
    bb_count = 0
    for path_id, res in pres.items():
        if ACC_KEY in res:
            acc_count += 1
        if res[BASIN_FWD_KEY] == BRES.A and res[BASIN_BACK_KEY] == BRES.A:
            aa_count += 1
        elif res[BASIN_FWD_KEY] == BRES.B and res[BASIN_BACK_KEY] == BRES.B:
            bb_count += 1

        tgt.write("%02d:%s" % (path_id, os.linesep))
        for dir_key in (BASIN_FWD_KEY, BASIN_BACK_KEY):
            tgt.write(RES_DIR_FMT % (dir_key,
                                     res[dir_key], os.linesep))
        tgt.write(RES_DIR_FMT % (ACC_KEY,
                                 "Y" if ACC_KEY in res else "N",
                                 os.linesep))
    tgt.write(os.linesep)
    tgt.write(SUM_FMT % ("Accepted", acc_count, os.linesep))
    tgt.write(SUM_FMT % ("Rejected", len(pres) - acc_count, os.linesep))
    tgt.write(SUM_FMT % ("Both A", aa_count, os.linesep))
    tgt.write(SUM_FMT % ("Both B", bb_count, os.linesep))


def write_csv_report(pres, tgt=sys.stdout, linesep=os.linesep):
    """Creates a CSV report for the given path results.

    Positional arguments:
    pres -- The path results.
    Keyword arguments:
    tgt -- The target to write to (stdout by default)
    """
    csv_writer = csv.writer(tgt, lineterminator=linesep)
    csv_writer.writerow(["path", BASIN_FWD_KEY, BASIN_BACK_KEY, ACC_KEY])
    for path_id, res in pres.items():
        csv_writer.writerow([path_id, res[BASIN_FWD_KEY], res[BASIN_BACK_KEY],
                             "Y" if ACC_KEY in res else "N"])


class AimlessShooter(object):
    """Encapsulates the process of running and analyzing compute jobs related
    to the Aimless Shooting modeling technique.  Instances are generally
    run using the run_calcs method.
    """

    def __init__(self, tpl_dir, tgt_dir, topo_loc, job_params, basins_params,
                 sub_handler=TorqueSubmissionHandler(), wait_secs=DEF_WAIT_SECS):
        """Sets up the initial state for this instance.

        Positional Arguments:
        tpl_dir -- The directory containing the templates.
        tgt_dir -- The working directory for this calculation.
        topo_loc -- Location of the topology file.
        job_params -- Dict of parameters used for filling in the Amber job
                      templates.
        basins_params -- Dict of parameters used for running basin calculations.
        Keyword Arguments:
        sub_handler -- The submission handler for jobs (defaults to
                        TorqueSubmissionHandler)
        out -- The target for output (defaults to stdout)
        wait_secs -- The length of time to wait while polling jobs (defaults to
                     10 seconds).
        """
        self.tgt_dir = tgt_dir
        self.tpl_dir = tpl_dir
        self.topo_loc = topo_loc
        self.job_params = job_params
        self.bp = basins_params
        self.sub_handler = sub_handler
        self.wait_secs = wait_secs
        self.x1_loc = self.tgtres(XONE_RST)
        self.x2_loc = self.tgtres(XTWO_RST)
        self.logger = logging.getLogger(
            '.'.join((__name__, self.__class__.__name__)))

    def run_calcs(self, num_paths):
        """Top-level runner for performing the aimless shooting calculations
        for the given number of paths, returning the results.

        Positional arguments:
        num_paths -- The number of paths to run.
        Returns:
        A nested dict keyed first by path, then by 'forward' and 'backward',
        with the values being the result of calc_basins for each path.
        """
        pres = {}
        for pnum in range(1, num_paths + 1):
            if random.randint(0, 1):
                shooter = self.x1_loc
            else:
                shooter = self.x2_loc
            self.logger.debug("Using '%s'\n" % shooter)
            self.run_starter(pnum, shooter)
            self.rev_vel()
            self.run_dt()
            self.run_fwd_and_back()
            pres[pnum] = self.calc_basins()
            self.proc_results(pres[pnum], shooter)
            self.clean(pnum)
        return pres

    def run_starter(self, pnum, shooter):
        """Runs the starter job, backing up the generated forward file.
        Returns when the submitted job is finished.

        pnum -- The path number currently running.
        shooter -- The chosen shooter file for this path.
        """
        self.logger.debug('running starter... generating velocities\n')
        start_id = self._sub_job(shooter,
                                 self.tgtres(FWD_IN_NAME),
                                 self.tgtres(STARTER_IN_NAME),
                                 self.tgtres(STARTER_OUT_NAME),
                                 self.tgtres(STARTER_MDCRD_NAME))
        self._wait_on_jobs([start_id])
        # Back up fwd rst
        path_out_dir = self.tgtres(OUT_DIR, str(pnum))
        if not os.path.exists(path_out_dir):
            os.makedirs(path_out_dir)
        shutil.copy2(self.tgtres(FWD_RST_NAME), path_out_dir)

    def rev_vel(self):
        """Generates the backward.rst file based on the contents of forward.rst.
        """
        self.logger.debug('reversing velocities\n')
        fwd_loc = self.tgtres(FWD_RST_NAME)
        back_loc = self.tgtres(BACK_RST_NAME)
        with open(fwd_loc) as fwd_file:
            fwd_lines = [line.rstrip('\n') for line in fwd_file]
        with open(back_loc, 'w') as back_file:
            back_file.write(fwd_lines[0].split()[0])
            back_file.write(" Made by %s at %s\n" % (os.path.basename(__file__),
                                                     datetime.datetime.now().
                                                     strftime(TSTAMP_FMT)))
            back_file.write(fwd_lines[1] + os.linesep)
            num_atoms = float(fwd_lines[1].split()[0])
            # Atom coordinates are two per line
            coord_lines = int(math.ceil(num_atoms / 2.0))
            # Don't touch the coordinates
            for sameline in range(2, coord_lines + 2):
                back_file.write(fwd_lines[sameline] + os.linesep)
                #Reverse the velocities
            for revline in range(2 + coord_lines, (coord_lines * 2) + 2):
                fline = map(float, fwd_lines[revline].split())
                back_file.write("".join(FLOAT_FMT % -num for num in fline))
                back_file.write(os.linesep)
                # Write out last line
            back_file.write(fwd_lines[-1])

    def calc_basins(self):
        """Performs the basin calculations for the current forward and bad
        backward cons data files.

        Returns a dict with the results (a, b, or i) keyed to 'forward'
        and 'backward'.  The results also contain 'RC1fw', 'RC1bw', 'RC2fw',
        and 'RC2bw'.
        """
        results = {}
        fwd_loc = self.tgtres(FWD_CONS_NAME)
        back_loc = self.tgtres(BACK_CONS_NAME)
        with open(fwd_loc) as fwd_file:
            fwd_lines = [line.rstrip('\n') for line in fwd_file]
        with open(back_loc) as back_file:
            back_lines = [line.rstrip('\n') for line in back_file]
        discard, results[RC1_FWD_KEY], results[RC2_FWD_KEY] = \
            map(float, fwd_lines[1].split())
        discard, results[RC1_BACK_KEY], results[RC2_BACK_KEY] = \
            map(float, back_lines[1].split())
        results[BASIN_FWD_KEY] = self.find_basin_dir(results[RC1_FWD_KEY],
                                                     results[RC2_FWD_KEY])
        results[BASIN_BACK_KEY] = self.find_basin_dir(results[RC1_BACK_KEY],
                                                      results[RC2_BACK_KEY])
        return results

    def run_dt(self):
        """Submits the DT job. Returns when the submitted job is finished.
        """
        self.logger.debug('running dt\n')
        start_id = self._sub_job(self.tgtres(FWD_RST_NAME),
                                 self.tgtres(POSTDT_RST_NAME),
                                 self.tgtres(DT_IN_NAME),
                                 self.tgtres(DT_OUT_NAME),
                                 self.tgtres(DT_MDCRD_NAME))
        self._wait_on_jobs([start_id])

    def run_fwd_and_back(self):
        """Submits the forward and backward jobs concurrently. Returns when
        the submitted jobs are finished.
        """
        self.logger.debug('running forward\n')
        fwd_id = self._sub_job(self.tgtres(POSTDT_RST_NAME),
                               self.tgtres(POSTFWD_RST_NAME),
                               self.tgtres(FWD_IN_NAME),
                               self.tgtres(FWD_OUT_NAME),
                               self.tgtres(FWD_MDCRD_NAME))

        self.logger.debug('running backward\n')
        back_id = self._sub_job(self.tgtres(POSTFWD_RST_NAME),
                                self.tgtres(POSTBACK_RST_NAME),
                                self.tgtres(BACK_IN_NAME),
                                self.tgtres(BACK_OUT_NAME),
                                self.tgtres(BACK_MDCRD_NAME))
        self._wait_on_jobs([fwd_id, back_id])

    def _wait_on_jobs(self, job_ids):
        """Polls the state of the given job IDs.  Returns when the IDs
        disappear from the status dict or the job's status is 'complete'.

        job_ids -- The list of IDs to wait for.
        """
        jstats = self.sub_handler.stat_jobs(job_ids)
        wait_count = 1
        while is_running(job_ids, jstats):
            self.logger.debug("Waiting '%d' seconds for job IDs '%s'\n" %
                              (wait_count * self.wait_secs, ",".join(map(str, job_ids))))
            time.sleep(self.wait_secs)
            wait_count += 1
            jstats = self.sub_handler.stat_jobs(job_ids)
        self.logger.debug("Finished job IDs '%s' in '%d' seconds\n" %
                          (",".join(map(str, job_ids)), (wait_count - 1) * self.wait_secs))

    def _sub_job(self, shooter_loc, dir_rst_loc, in_loc, out_loc, mdcrd_loc):
        """Fills the job template with the given parameters and submits the
        job, returning the ID assigned to the job.

        Positional arguments:
        shooter_loc -- The location of the "shooter" file
        dir_rst_loc -- The location of the <direction>.rst file to use
        in_loc -- The location of the input file
        out_loc -- The location of the output file
        mdcrd_loc -- The location of the mdcrd file
        Returns:
        The ID of the submitted job
        """
        local_params = self.job_params.copy()
        local_params[TOPO_KEY] = self.topo_loc
        local_params[SHOOTER_KEY] = shooter_loc
        local_params[DIR_RST_KEY] = dir_rst_loc
        local_params[INFILE_KEY] = in_loc
        local_params[OUTFILE_KEY] = out_loc
        local_params[MDCRD_KEY] = mdcrd_loc

        tpl_loc = os.path.join(self.tpl_dir, AMBER_JOB_TPL)
        with open(tpl_loc, 'r') as tpl_file:
            tpl = Template(tpl_file.read())
            result = tpl.safe_substitute(local_params)
        job = TorqueJob(**local_params)
        logger.info("Submitting:\n%s" % result)
        job.contents = result
        return self.sub_handler.submit(job)

    def tgtres(self, *args):
        """Alias for resolving the given path segments against the target
        directory.
        """
        return os.path.join(self.tgt_dir, *args)

    def find_basin_dir(self, rc1, rc2):
        """Determines whether the given reaction coordinates are going toward
        A, B, or neither (inconclusive).

        Positional arguments:
        rc1 -- The first reaction coordinate.
        rc2 -- The second reaction coordinate.
        Returns:
        a, b, or i depending on which basin (if any) matches.
        """
        if self.bp[RC1_LOW_A_KEY] < rc1 < self.bp[RC1_HIGH_A_KEY] \
                and self.bp[RC2_LOW_A_KEY] < rc2 < self.bp[RC2_HIGH_A_KEY]:
            return BRES.A
        elif self.bp[RC1_LOW_B_KEY] < rc1 < self.bp[RC1_HIGH_B_KEY] \
                and self.bp[RC2_LOW_B_KEY] < rc2 < self.bp[RC2_HIGH_B_KEY]:
            return BRES.B
        else:
            return BRES.INC

    def proc_results(self, result, shooter):
        """
        Process the shooter results.  If there are conclusive results, accept
        it and move the shooter to x1 and the post-dt to x2.  Mark the result
        as "accepted."

        result -- The basin calculation result.
        shooter -- The shooter file to potentially move.
        """
        if (result[BASIN_FWD_KEY] == BRES.A and result[BASIN_BACK_KEY] ==
            BRES.B) or (result[BASIN_FWD_KEY] == BRES.B
                        and result[BASIN_BACK_KEY] == BRES.A):
            shutil.copy2(shooter, self.x1_loc)
            shutil.copy2(self.tgtres(POSTDT_RST_NAME), self.x2_loc)
            result[ACC_KEY] = True

    def clean(self, pnum):
        """Moves artifacts from a path's calculation to an output directory
        named for the given path number.

        pnum -- The path number of the finished calculation.
        """
        path_out_dir = self.tgtres(OUT_DIR, "%02d" % pnum)
        if not os.path.exists(path_out_dir):
            os.makedirs(path_out_dir)
        for mvname in GEN_FILES:
            tgt = self.tgtres(mvname)
            try:
                shutil.move(tgt, path_out_dir)
            except Exception, e:
                logger.warn("Could not archive '%s': %s" % (path_out_dir, e))

### CLI ###
DEF_CFG_NAME = 'aimless.ini'

# Keys #
TPL_DIR_KEY = 'tpldir'
TGT_DIR_KEY = 'tgtdir'
TEXT_REPORT_KEY = 'text_report'
CSV_REPORT_KEY = 'csv_report'

# Reports #
DEF_TEXT_REPORT = 'aimless_results.txt'
DEF_CSV_REPORT = 'aimless_results.csv'
TEXT_FMT = 't'
CSV_FMT = 'c'
VALID_FMTS = [TEXT_FMT, CSV_FMT]
DEF_OUT_FMTS = TEXT_FMT

# Config Sections #
MAIN_SEC = 'main'
JOBS_SEC = 'jobs'
BASINS_SEC = 'basins'


class CfgError(Exception):
    pass

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


def write_cfg_tpls(config, params):
    """
    ConfigParser adapter for write_tpl_files.  Fills the templates in the
    configuration's 'tpldir' and writes the results to the configuration's
    'tgtdir'.

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


def run(config, tgt_class=AimlessShooter):
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
    aims = tgt_class(tpl_dir, tgt_dir, topo_file,
                     dict(config.items(JOBS_SEC)), bparams)
    return aims.run_calcs(num_paths)

# Command-line processing and control #


def get(cfg, opt_name, sec_name, def_val):
    """
    Returns the cfg val for the given section and option, returning
    the default value if no option is defined.

    cfg      -- The configuration instance to query.
    opt_name -- The option key.
    sec_name -- The section name.
    def_val  -- The value to use if none are found in the cfg.
    """
    try:
        return cfg.get(opt_name, sec_name)
    except NoOptionError:
        return def_val


def read_config(file_loc):
    """
    Loads and returns the configuration file from the given location.

    Arguments:
    file_loc -- The location of the configuration file.
    Returns:
    A ConfigParser object containing the file's configuration data.
    """
    config = ConfigParser.ConfigParser()
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


def print_reports(config, fmts, pres):
    """
    Produces reports from the given results.

    config -- The configuration instance to query.
    fmts   -- A string where each character represents a report format.
    pres   -- The report results from AimlessShooter.
    """
    # TODO: Consider rotation
    # http://johnebailey.blogspot.com/2012/01/rolling-files-and-directories-with.html
    for fmt in fmts:
        if fmt.lower() == TEXT_FMT:
            txt_file = get(config, MAIN_SEC, TEXT_REPORT_KEY, DEF_TEXT_REPORT)
            with open(txt_file, 'w') as txt_tgt:
                write_text_report(pres, txt_tgt)
        elif fmt.lower() == CSV_FMT:
            csv_file = get(config, MAIN_SEC, CSV_REPORT_KEY, DEF_CSV_REPORT)
            with open(csv_file, 'w') as csv_tgt:
                write_csv_report(pres, csv_tgt)
        else:
            raise CfgError("Unhandled output format '%s'" % fmt)


def main(argv=None):
    """
    Main entry point for the script.  Processes the arguments and config file,
    using the results to run the script, finally producing the specified output
    reports.

    argv -- The CLI arguments to process.
    """
    opts, args = parse_cmdline(argv)
    config = read_config(opts.cfg_file)
    params = fetch_calc_params(config)
    write_cfg_tpls(config, params)
    pres = run(config)

    print_reports(config, opts.out_formats, pres)
    return 0        # success


if __name__ == '__main__':
    status = main()
    sys.exit(status)