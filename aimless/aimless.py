import os
from string import Template

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
TPL_DIR_KEY = 'tpldir'
TGT_DIR_KEY = 'tgtdir'
MAIN_SEC = 'main'

class TemplateError(Exception): pass
class EnvError(Exception): pass

def calc_params(raw):
    results = raw.copy()
    results[BW_STEPS_KEY] = results[TOTAL_STEPS_KEY] / 2
    results[FW_STEPS_KEY] = results[TOTAL_STEPS_KEY] / 2
    results[DT_STEPS_KEY] = results[TOTAL_STEPS_KEY] / 100
    results[BW_OUT_KEY] = results[BW_STEPS_KEY] - 1
    results[FW_OUT_KEY] = results[FW_STEPS_KEY] - 1
    results[DT_OUT_KEY] = results[DT_STEPS_KEY] - 1
    return results

tpl_idx = [
    ("cons.tpl", "cons.rst",
     "force constants are zero - this is just to get final bond lengths"),
    ("instarter.tpl", "instarter.in",
     "generate the velocities for this shooting point"),
    ("indt.tpl", "indt.in", "TODO: What is this?  Cut-and-paste fwd desc"),
    ("inforward.tpl", "inforward.in", "forward portion of the trajectory"),
    ("inbackward.tpl", "inbackward.in", "backward portion of the trajectory"),
]

def write_tpl_files(tpl_dir, tgt_dir, params):
    for tpl_name, tgt_name, tpl_desc in tpl_idx:
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