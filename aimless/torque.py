from common import (SubmissionError, StatusError, OutputParsingError,
    AutoRepr, enum, StructEq, STATES, to_datetime, scalarize)
from datetime import datetime, timedelta
import logging
from subprocess import PIPE, Popen
import xml.etree.ElementTree as et
import re

DEF_NAME = 'nameless_job'
DEF_TGT = '/dev/null'
DEF_NODES = 1
DEF_QUEUE = 'batch'
DEF_WALLTIME = '999:00:00'

TSTATES = enum(COMPLETED='C', EXITING='E', HELD='H', QUEUED='Q', RUNNING='R',
      MOVED='T', WAITING='W', SUSPENDED='S')

class TorqueSubmissionError(SubmissionError): pass
class TorqueStatusError(StatusError): pass

logger = logging.getLogger("torque")

def parse_id(raw_str):
    "Parses the numeric ID from a string of the form id.host"
    split_str = raw_str.split(".")
    if len(split_str) == 2:
        try:
            return int(split_str[0])
        except ValueError as e:
            raise OutputParsingError("Job ID value %s is not an int: %s" % (split_str[0], e))
    else:
        raise OutputParsingError("Could not properly split output %s" % raw_str)

class TorqueJob(StructEq, AutoRepr):
    "Represents a job to run.  Includes reasonable control defaults."
    
    def __init__(self, **kwargs):
        self.contents=None
        self.name=DEF_NAME
        self.stdout=DEF_TGT
        self.stderr=DEF_TGT
        self.numnodes=DEF_NODES
        self.numcpus=None
        self.queue=DEF_QUEUE
        self.walltime=DEF_WALLTIME
        self.sub_id=None
        self.created=None
        self.updated=None
        self.mail=None
        for key in self.__dict__:
            if key in kwargs:
                setattr(self, key, scalarize(kwargs[key]))

class JobStatus(StructEq, AutoRepr):
    attr_keys = {'Job_Name' : 'name', 'Job_Owner' : 'owner', 'job_state' : 
                  'job_state', 'queue' : 'queue', 'ctime' : 'ctime',
                  'qtime': 'qtime', 'Job_Id': 'job_id', 'start_time': 
                  'start_time', 'exec_host' : 'exec_host'}
    time_attrs = ['ctime', 'qtime', 'created', 'updated', 'start_time']
    
    def __init__(self, **kwargs):
        for key in self.attrs():
            if key in kwargs:
                setattr(self, key, self._cast(key, kwargs[key]))
            else:
                setattr(self, key, None)

    def attrs(self):
        "Returns the attributes available for JobStatus instances."
        attr_list = self.attr_keys.values()
        attr_list.append('sub_id')
        attr_list.append('created')
        attr_list.append('updated')
        attr_list.append('version')
        attr_list.append('remaining')        
        return attr_list

    def remaining_delta(self):
        "Creates a timedelta instance from the remaining seconds field."
        if self.remaining:
            return timedelta(seconds=self.remaining)
        else:
            return timedelta()
        
    def start_delta(self, now=datetime.now()):
        """Creates a timedelta instance from the difference between now and 
        the start_time field.
        
        now -- The end timestamp to calculate against (default: now).
        """
        if self.start_time:
            return now - self.start_time
        else:
            return timedelta()
    
    def _cast(self, name, val):
        if name in self.time_attrs:
            return to_datetime(val)
        else:
            return val
            
    @classmethod
    def from_xml(cls, xml_element):
        "Job status instance filled from the -x option on qstat"
        jattrs = {}
        for item in xml_element.iter():
            if item.tag == 'Job_Id':
                jattrs['job_id'] = parse_id(item.text)
            elif item.tag == 'Walltime':
                jattrs['remaining'] = int(item.findtext('Remaining', default=0))
            elif item.tag in cls.attr_keys.keys():
                tgt_key = cls.attr_keys[item.tag]
                if item.tag.endswith('time'):
                    jattrs[tgt_key] = datetime.fromtimestamp(float(item.text))
                elif tgt_key == 'job_state':
                    tstate = TSTATES.reverse_mapping[item.text]
                    jattrs[tgt_key] = getattr(STATES, str(tstate))
                else:
                    jattrs[tgt_key] = item.text
        return cls(**jattrs)
    
    @classmethod
    def from_dict(cls, src_dict):
        "Job status instance filled from the given dict"
        local_dict = dict(src_dict)
        return cls(**local_dict)
    
    @classmethod
    def from_job(cls, job):
        "Job status instance filled from the given TorqueJob"
        return cls(sub_id = job.sub_id, created=job.created, updated=job.updated, 
              name=job.name)

def pipe_cmd(cmd):
    """Executes the given command in a subprocess.  Creates pipes
    for stdin, stdout, and stderr.
    
    Arguments:
    cmd -- The command to run in a subprocess.     
    """
    return Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)

def fix_torque_name(name):
    """Makes sure the given name complies with qsub's requirements: A name 
    that is no longer than 15 characters, does not start with a digit, and
    does not contain spaces."""
    if not name:
        return DEF_NAME
    name = re.sub(r"\s+", '-', name)
    if name[0].isdigit():
        name = "d" + name
    if len(name) > 15:
        name = name[:14]
    return name

class TorqueSubmissionHandler(object):
    def __init__(self, pipe_cmd=pipe_cmd):
        self.pipe_cmd = pipe_cmd
    
    "Creates, executes, and extracts the job ID from a queue submission."
    def create_submit_cmd(self, job):
        "Assembles a qsub command based on the job's parameters."
        cmd = ["qsub", "-V"]
        cmd += ["-N", fix_torque_name(job.name)]
        cmd += ["-o", job.stdout]
        cmd += ["-e", job.stderr]
        cmd += ["-q", job.queue]
        cmd += ["-l", 'walltime=%s' % job.walltime]
        cmd += ["-l", 'nodes=%s' % job.numnodes]
        if job.numcpus:
            cmd += ["-l", 'ppn=%s' % job.numcpus]
        if job.mail:
            cmd += ["-m", 'a']
            cmd += ["-M", job.mail]
        return cmd
    
    def run(self, cmd):
        "Creates a handle to a subprocess running the given command"
        return self.pipe_cmd(cmd)
    
    def submit(self, job):
        "Submits the given job, returning the numeric job ID."
        proc = self.run(self.create_submit_cmd(job))
        out, err = proc.communicate(job.contents)
        if len(out) == 0:
            raise TorqueSubmissionError("No output for %s with contents %s.  Errors: %s" % (job.name, job.contents, err))
        logger.debug("Output from job %s: %s" % (job.name, out))
        return parse_id(out)
    
    def stat_jobs(self, ids=None):
        """Runs a qstat and collects the results in a dict mapped by ID for 
        the given job IDs (or all jobs if ids is None)"""
        if ids == None:
            proc = self.run(["qstat", "-x"])
        else:
            strids = map(str, ids)
            proc = self.run(["qstat", "-x"] + strids)
        out, err = proc.communicate()
        logger.debug("Stat: " + out)
        if len(err) > 0:
            logger.debug("Error output for stat on IDs %s: %s" 
                  % (",".join(strids), err))
        jobs_by_id = {}
        if len(out) == 0:
            return jobs_by_id
        # When multiple entries are requested, each comes in a "Data" block 
        # without a root node
        entries = et.fromstring('<top>' + out + '</top>')
        for entry in entries.findall("./Data"):
            statln = JobStatus.from_xml(entry)
            jobs_by_id[statln.job_id] = statln
        return jobs_by_id

class JobWatcher(object):
    def __init__(self, repo, handler):
        self.repo = repo
        self.handler = handler
    
    def submit_saved(self):
        saved = self.repo.get_saved_jobs()
        if saved and logger.isEnabledFor(logging.DEBUG):
            logger.debug("Found %d saved jobs to submit: %s" % (len(saved), 
                  ",".join(job.name for job in saved)))
        for job in saved:
            jid = self.handler.submit(job)
            jstat = JobStatus.from_job(job)
            jstat.job_id = jid
            jstat.job_state = STATES.SUBMITTED
            # If this is a initial save, the status should be at v1
            jstat.version = 1
            # TODO: Consider cancelling job and marking FAILED when the update fails
            self.repo.update_statuses([jstat])

    def update_incomplete(self):
        stats = self.repo.get_active_statuses()
        if not stats:
            return
        nstats = self.handler.stat_jobs(stat.job_id for stat in stats)
        for orig_stat in stats:
            nstat = nstats.get(orig_stat.job_id, None)
            if nstat:
                # TODO: Consider adding an update gate that only updates
                # when state changes or n calls (or time, or whatever) have happened
                orig_stat.job_state = nstat.job_state
                orig_stat.owner = nstat.owner
                orig_stat.ctime = nstat.ctime
                orig_stat.qtime = nstat.qtime
            else:
                logger.debug("No entry found for ID %s, marking complete" % orig_stat.job_id)
                orig_stat.job_state = STATES.COMPLETED
        # TODO: Handle update exceptions?
        self.repo.update_statuses(stats)
