import os
import random
from shlex import shlex
import shutil
from string import Template
import sys
import time
from torque import TorqueJob, TorqueSubmissionHandler

# Constants #
WAIT_SECS = 10

# Config Sections #
MAIN_SEC = 'main'
JOBS_SEC = 'jobs'

# Shooter Files #
XONE_RST = "x1.rst"
XTWO_RST = "x2.rst"
SHOOTER_RST = "shooter.rst"
AMBER_JOB_TPL = 'amber_job.tpl'

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


class TemplateError(Exception):
    pass


class EnvError(Exception):
    pass


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


def any_key(keys, tgt):
    for tkey in keys:
        if tkey in tgt:
            return True
    return False


class AimlessShooter(object):
    """
    Encapsulates the process of running and analyzing compute jobs related
    to the Aimless Shooting modeling technique.
    """
    def __init__(self, tgt_dir, tpl_dir, topo_loc, job_params,
                 sub_handler=TorqueSubmissionHandler(), out=sys.stdout):
        self.tgt_dir = tgt_dir
        self.tpl_dir = tpl_dir
        self.topo_loc = topo_loc
        self.job_params = job_params
        self.sub_handler = sub_handler
        self.out = out

    def run_calcs(self, num_paths):
        for pnum in range(1, num_paths + 1):
            if random.randint(0, 1):
                shooter = os.path.join(self.tgt_dir, XONE_RST)
            else:
                shooter = os.path.join(self.tgt_dir, XTWO_RST)
            self.out.write("Using '%s'" % shooter)
            shutil.copy2(shooter, os.path.join(self.tgt_dir, SHOOTER_RST))
            self.out.write("running starter... generating velocities")
            start_id = self._sub_job(shooter, os.path.join(self.tgt_dir, FWD_IN_NAME),
                                     os.path.join(self.tgt_dir, STARTER_IN_NAME),
                                     os.path.join(self.tgt_dir, STARTER_OUT_NAME))
            self._wait_on_jobs([start_id])

    def _wait_on_jobs(self, job_ids):
        jstats = self.sub_handler.stat_jobs(job_ids)
        wait_count = 1
        while any_key(job_ids, jstats):
            self.out.write("Waiting '%d' seconds for job IDs '%s'" %
                           (wait_count * WAIT_SECS, ",".join(job_ids)))
            time.sleep(WAIT_SECS)
            wait_count += 1
            jstats = self.sub_handler.stat_jobs(job_ids)
        self.out.write("Finished job IDs '%s' in '%d' seconds" %
                       (",".join(job_ids), wait_count * WAIT_SECS))

    def _sub_job(self, shooter_loc, dir_rst_loc, in_loc, out_loc):
        local_params = self.job_params.copy()
        local_params[TOPO_KEY] = self.topo_loc
        local_params[SHOOTER_KEY] = shooter_loc
        local_params[DIR_RST_KEY] = dir_rst_loc
        local_params[INFILE_KEY] = in_loc
        local_params[OUTFILE_KEY] = out_loc

        tpl_loc = os.path.join(self.tpl_dir, AMBER_JOB_TPL)
        with open(tpl_loc, 'r') as tpl_file:
            tpl = Template(tpl_file.read())
            result = tpl.safe_substitute(local_params)
        job = TorqueJob(**local_params)
        job.contents = result
        return self.sub_handler.submit(job)
