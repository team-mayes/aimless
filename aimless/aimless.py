import logging
import os
import random
from shlex import shlex
import shutil
from string import Template
import sys
import time
import datetime
import math
from common import STATES
from torque import TorqueJob, TorqueSubmissionHandler

# Constants #
DEF_WAIT_SECS = 10
TSTAMP_FMT = '%Y-%m-%d %H:%M:%S'
FLOAT_FMT = " % 11.7f"

# Config Sections #
MAIN_SEC = 'main'
JOBS_SEC = 'jobs'

# Shooter Resources #
XONE_RST = "x1.rst"
XTWO_RST = "x2.rst"
SHOOTER_RST = "shooter.rst"
FWD_RST_NAME = "forward.rst"
BACK_RST_NAME = "backward.rst"
AMBER_JOB_TPL = 'amber_job.tpl'
OUT_DIR = 'output'

# Directional Input Files #
BACK_IN_NAME = "inbackward.in"
FWD_IN_NAME = "inforward.in"
DT_IN_NAME = "indt.in"
STARTER_IN_NAME = "instarter.in"

# Directional Output Files #
BACK_OUT_NAME = "inbackward.out"
FWD_OUT_NAME = "inforward.out"
DT_OUT_NAME = "indt.out"
STARTER_OUT_NAME = "instarter.out"

# MDCRD files
BACK_MDCRD_NAME = "inbackward.out"
FWD_MDCRD_NAME = "inforward.out"
DT_MDCRD_NAME = "indt.out"
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
MDCRD_KEY = 'mdcrd'

logger = logging.getLogger("aimless")

# Exceptions #
class TemplateError(Exception):
    pass


class EnvError(Exception):
    pass

# Logic #

def calc_params(total_steps):
    """
    Returns a dict with calculated values based on the given number of total
    steps.
    """
    results = {TOTAL_STEPS_KEY: total_steps}
    results[BW_STEPS_KEY] = total_steps / 2
    results[FW_STEPS_KEY] = total_steps / 2
    results[DT_STEPS_KEY] = total_steps / 100
    results[BW_OUT_KEY] = results[BW_STEPS_KEY] - 1
    results[FW_OUT_KEY] = results[FW_STEPS_KEY] - 1
    results[DT_OUT_KEY] = results[DT_STEPS_KEY] - 1
    return results


TPL_LIST = [
    ("cons.tpl", "cons.rst",
     "force constants are zero - this is just to get final bond lengths"),
    ("instarter.tpl", STARTER_IN_NAME,
     "generate the velocities for this shooting point"),
    ("indt.tpl", DT_IN_NAME, "TODO: What is this?  Cut-and-paste fwd desc"),
    ("inforward.tpl", FWD_IN_NAME, "forward portion of the trajectory"),
    ("inbackward.tpl", BACK_IN_NAME, "backward portion of the trajectory"),
]

# TODO: Move write_tpl_files and init_dir to AimlessShooter
def write_tpl_files(tpl_dir, tgt_dir, params):
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
    shutil.copy2(coords_loc, os.path.join(tgt_dir, XONE_RST))
    shutil.copy2(coords_loc, os.path.join(tgt_dir, XTWO_RST))


def is_running(keys, tgt):
    """Returns whether any jobs are running.
    """
    for tkey in keys:
        if tkey in tgt:
            stat = tgt[tkey]
            if stat.job_state != STATES.COMPLETED:
                return True
            else:
                logger.info("Job %s complete" % tkey)
    return False

class AimlessShooter(object):
    """
    Encapsulates the process of running and analyzing compute jobs related
    to the Aimless Shooting modeling technique.
    """

    def __init__(self, tpl_dir, tgt_dir, topo_loc, job_params,
                 sub_handler=TorqueSubmissionHandler(), out=sys.stdout,
                 wait_secs=DEF_WAIT_SECS):
        self.tgt_dir = tgt_dir
        self.tpl_dir = tpl_dir
        self.topo_loc = topo_loc
        self.job_params = job_params
        self.sub_handler = sub_handler
        self.out = out
        self.wait_secs = wait_secs

    def run_dt(self):
        self.out.write('running dt\n')
        start_id = self._sub_job(os.path.join(self.tgt_dir, FWD_RST_NAME),
                                 os.path.join(self.tgt_dir, FWD_IN_NAME),
                                 os.path.join(self.tgt_dir, STARTER_IN_NAME),
                                 os.path.join(self.tgt_dir, STARTER_OUT_NAME),
                                 os.path.join(self.tgt_dir, STARTER_MDCRD_NAME),
        )
        self._wait_on_jobs([start_id])

    def run_starter(self, pnum, shooter):
        self.out.write('running starter... generating velocities\n')
        start_id = self._sub_job(shooter, os.path.join(self.tgt_dir, FWD_IN_NAME),
                                 os.path.join(self.tgt_dir, STARTER_IN_NAME),
                                 os.path.join(self.tgt_dir, STARTER_OUT_NAME),
                                 os.path.join(self.tgt_dir, STARTER_MDCRD_NAME),
        )
        self._wait_on_jobs([start_id])
        self.path_backup(FWD_RST_NAME, pnum)

    def run_calcs(self, num_paths):
        for pnum in range(1, num_paths + 1):
            if random.randint(0, 1):
                shooter = os.path.join(self.tgt_dir, XONE_RST)
            else:
                shooter = os.path.join(self.tgt_dir, XTWO_RST)
            self.out.write("Using '%s'\n" % shooter)
            shutil.copy2(shooter, os.path.join(self.tgt_dir, SHOOTER_RST))
            self.run_starter(pnum, shooter)
            self.rev_vel()

    def path_backup(self, src_file, pnum):
        """
        Creates a backup of 'src_file' in the output directory for 'pnum'.
        """
        path_out_dir = os.path.join(self.tgt_dir, OUT_DIR, str(pnum))
        if not os.path.exists(path_out_dir):
            os.makedirs(path_out_dir)

        shutil.copy2(os.path.join(self.tgt_dir, src_file), path_out_dir)

    def rev_vel(self):
        self.out.write('reversing velocities\n')
        fwd_loc = os.path.join(self.tgt_dir, FWD_RST_NAME)
        back_loc = os.path.join(self.tgt_dir, BACK_RST_NAME)
        with open(fwd_loc) as fwd_file:
            fwd_lines = [line.rstrip('\n') for line in fwd_file]
        with open(back_loc, 'w') as back_file:
            back_file.write(fwd_lines[0].split()[0])
            back_file.write(" Made by %s at %s\n" % (os.path.basename(__file__),
                                                      datetime.datetime.now().
                                                      strftime(TSTAMP_FMT)))
            back_file.write(fwd_lines[1] + os.linesep)
            # TODO: Use number of lines to figure out
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

            # TODO: Port the rest of revvels.x

    def _wait_on_jobs(self, job_ids):
        jstats = self.sub_handler.stat_jobs(job_ids)
        wait_count = 1
        while is_running(job_ids, jstats):
            self.out.write("Waiting '%d' seconds for job IDs '%s'\n" %
                           (wait_count * self.wait_secs, ",".join(map(str, job_ids))))
            time.sleep(self.wait_secs)
            wait_count += 1
            jstats = self.sub_handler.stat_jobs(job_ids)
        self.out.write("Finished job IDs '%s' in '%d' seconds\n" %
                       (",".join(map(str, job_ids)), (wait_count - 1) * self.wait_secs))

    def _sub_job(self, shooter_loc, dir_rst_loc, in_loc, out_loc, mdcrd_loc):
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
