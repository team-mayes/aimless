#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_aimless
----------------------------------

Tests for `aimless` module.
"""
import StringIO
import difflib
import filecmp
import io
import os
import shutil
import tempfile
from mock import MagicMock

import unittest

from aimless.aimless import (calc_params, TOTAL_STEPS_KEY, BW_STEPS_KEY,
                             FW_STEPS_KEY, DT_STEPS_KEY, BW_OUT_KEY,
                             FW_OUT_KEY, DT_OUT_KEY, write_tpl_files,
                             TPL_LIST, AimlessShooter, init_dir, FWD_RST_NAME, OUT_DIR, BACK_RST_NAME, FWD_CONS_NAME, BACK_CONS_NAME, DT_CONS_NAME, RC1_LOW_A_KEY, RC1_HIGH_A_KEY, RC2_HIGH_A_KEY, RC2_LOW_A_KEY, RC1_LOW_B_KEY, RC1_HIGH_B_KEY, RC2_LOW_B_KEY, RC2_HIGH_B_KEY, BASIN_FWD_KEY, BASIN_BACK_KEY, BRES, ACC_KEY, write_text_report, write_csv_report)
from aimless.common import STATES
from aimless.main import (TGT_DIR_KEY)

# Test Constants #
from aimless.torque import JobStatus

TEST_ID = 11
TEST_ID2 = 22
TEST_ID3 = 33
TEST_ID4 = 44
TEST_ID5 = 55
TEST_ID6 = 66
TEST_ID7 = 77
TEST_ID8 = 88
TEST_ID9 = 99
TEST_ID10 = 100
TEST_ID11 = 110
TEST_ID12 = 120
TS_VAL = 1000
FWBW_VAL = TS_VAL / 2
DT_VAL = TS_VAL / 100
FWBW_OUT_VAL = FWBW_VAL - 1
DT_OUT_VAL = DT_VAL - 1
TPL_RESULT_DIR = os.path.join(os.path.dirname(__file__), 'tpl_result')
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'test_data')
INPUT_DIR = os.path.join(os.path.dirname(__file__), 'input')
TPL_DIR = os.path.join(os.path.dirname(__file__), os.pardir, 'aimless', 'skel',
                       'tpl')
TGT_DIR_VAL = "test/tgt/dir"
SHOOTER_LOC_VAL = "test_shooter.rst"
DIR_RST_LOC = "test_dir.rst"
IN_LOC = 'test_in'
OUT_LOC = 'test_out'
MDCRD_LOC = 'test_mdcrd'
AMBER_REF_NAME = 'amber_job.result'
COORDS_LOC = os.path.join(INPUT_DIR, 'test_coords.rst')
TOPO_LOC = os.path.join(INPUT_DIR, 'test_topo.rst')
BASIN_VALS = {RC1_LOW_A_KEY: TEST_ID, RC1_HIGH_A_KEY: TEST_ID2,
              RC2_LOW_A_KEY: TEST_ID3, RC2_HIGH_A_KEY: TEST_ID4,
              RC1_LOW_B_KEY: TEST_ID5, RC1_HIGH_B_KEY: TEST_ID6,
              RC2_LOW_B_KEY: TEST_ID7, RC2_HIGH_B_KEY: TEST_ID8}


def file_cmp(new_tgt, ref_tgt):
    if not filecmp.cmp(new_tgt, ref_tgt):
        with open(new_tgt, 'r') as new_file, open(ref_tgt, 'r') \
            as ref_file:
            diff = difflib.context_diff(new_file.readlines(),
                                        ref_file.readlines())
            delta = ''.join(diff)
            print delta
            return False
    else:
        return True


def cmp_not_first(new_tgt, ref_tgt, test_class):
    with open(ref_tgt) as ref_file:
        ref_lines = [line.rstrip('\n') for line in ref_file]
    with open(new_tgt) as new_file:
        new_lines = [line.rstrip('\n') for line in new_file]

    if len(ref_lines) != len(new_lines):
        print "Lines differ: ref: %d, new %d" % (len(ref_lines), len(new_lines))

    for lnum in range(1, len(ref_lines)):
        test_class.assertEqual(ref_lines[lnum], new_lines[lnum],
                               "Diff: %s vs. %s" %
                               (ref_lines[lnum], new_lines[lnum]))


# Tests #
class TestCalc(unittest.TestCase):
    "Calc tests"

    def test_calc(self):
        results = calc_params(TS_VAL)
        self.assertEqual(TS_VAL, results[TOTAL_STEPS_KEY])
        self.assertEqual(FWBW_VAL, results[BW_STEPS_KEY])
        self.assertEqual(FWBW_VAL, results[FW_STEPS_KEY])
        self.assertEqual(DT_VAL, results[DT_STEPS_KEY])
        self.assertEqual(FWBW_OUT_VAL, results[BW_OUT_KEY])
        self.assertEqual(FWBW_OUT_VAL, results[FW_OUT_KEY])
        self.assertEqual(DT_OUT_VAL, results[DT_OUT_KEY])


class TestWriteTpls(unittest.TestCase):
    """
    Validates template filling and writing.
    """

    def setUp(self):
        self.params = calc_params(TS_VAL)

    def test_tmp_tgt(self):
        "Use a temp directory as the target."
        tgt_dir = tempfile.mkdtemp()
        self._del_tgts(tgt_dir)
        try:
            write_tpl_files(TPL_DIR, tgt_dir, self.params)
            self._check_tgts(tgt_dir)
        finally:
            self._del_tgts(tgt_dir)
            os.removedirs(tgt_dir)

    def _check_tgts(self, tgt_dir):
        "Compares the files in the target dir with reference files."
        for tpl_name, tgt_name, tpl_desc in TPL_LIST:
            new_tgt = os.path.join(tgt_dir, tgt_name)
            self.assertTrue(os.path.exists(new_tgt))
            ref_tgt = os.path.join(TPL_RESULT_DIR, tgt_name)
            if not file_cmp(new_tgt, ref_tgt):
                self.fail(new_tgt + " did not match.")

    def _del_tgts(self, tgt_dir):
        "Deletes the target files in the target directory."
        for tpl_name, tgt_name, tpl_desc in TPL_LIST:
            tgt_tpl = os.path.join(tgt_dir, tgt_name)
            if os.path.exists(tgt_tpl):
                os.remove(tgt_tpl)
            self.assertFalse(os.path.exists(tgt_tpl))


class TestAimlessShooter(unittest.TestCase):
    """
    Check behavior of the AimlessShooter class.
    """

    def setUp(self):
        self.tgt_dir = tempfile.mkdtemp()
        self.out = StringIO.StringIO()
        self.handler = MagicMock()
        self.aimless = AimlessShooter(TPL_DIR, self.tgt_dir,
                                      TOPO_LOC, dict(), BASIN_VALS,
                                      sub_handler=self.handler,
                                      out=self.out, wait_secs=.001)
        self.fwd_name = os.path.join(self.tgt_dir, FWD_RST_NAME)

    def test_sub(self):
        self.aimless.topo_loc = 'test_topo.file'
        self.aimless._sub_job(SHOOTER_LOC_VAL, DIR_RST_LOC, IN_LOC, OUT_LOC,
                              MDCRD_LOC)
        self.assertEqual(len(self.handler.method_calls), 1)
        job = self.handler.method_calls[0][1][0]
        with open(os.path.join(TPL_RESULT_DIR, AMBER_REF_NAME)) as ref_file:
            ref_contents = ref_file.read()
            self.assertEqual(ref_contents, job.contents)

    def test_wait(self):
        stat = JobStatus(job_state=STATES.QUEUED)
        self.handler.stat_jobs.side_effect = [{TEST_ID: stat}, {}]
        self.aimless._wait_on_jobs([TEST_ID, TEST_ID2])
        self.assertEqual(2, self.handler.stat_jobs.call_count)

    def test_wait_complete(self):
        stat = JobStatus(job_state=STATES.COMPLETED)
        self.handler.stat_jobs.side_effect = [{TEST_ID: stat}]
        self.aimless._wait_on_jobs([TEST_ID, TEST_ID2])
        self.assertEqual(1, self.handler.stat_jobs.call_count)

    def test_calcs_single_path(self):
        init_dir(self.tgt_dir, COORDS_LOC)
        self.handler.submit.side_effect = [TEST_ID, TEST_ID2, TEST_ID3, TEST_ID4]
        stat = JobStatus(job_state=STATES.QUEUED)
        statc = JobStatus(job_state=STATES.COMPLETED)
        self.handler.stat_jobs.side_effect = [{TEST_ID: stat}, {}, {TEST_ID2: stat},
                                              {TEST_ID2: statc},
                                              {TEST_ID3: statc, TEST_ID4: statc}]
        self._write_test_files(self.tgt_dir)
        self.aimless.run_calcs(1)
        self.assertEqual(5, self.handler.stat_jobs.call_count)
        self._chk_bak(1)
        self.assertTrue(os.path.exists(os.path.join(self.tgt_dir, BACK_RST_NAME)))

    # TODO: If we get further on real data, consider a shim to re-init test files per path.
    # def test_calcs_three_paths(self):
    #     init_dir(self.tgt_dir, COORDS_LOC)
    #     self.handler.submit.side_effect = [TEST_ID, TEST_ID2, TEST_ID3, TEST_ID4,
    #                                        TEST_ID5, TEST_ID6, TEST_ID7, TEST_ID8,
    #                                        TEST_ID9, TEST_ID10, TEST_ID11, TEST_ID12, ]
    #     stat = JobStatus(job_state=STATES.QUEUED)
    #     statc = JobStatus(job_state=STATES.COMPLETED)
    #     self.handler.stat_jobs.side_effect = [{TEST_ID: stat}, {},
    #                                           {TEST_ID2: stat}, {TEST_ID2: stat}, {},
    #         {}, {TEST_ID5: stat}, {}, {TEST_ID6: statc}, {},
    #                                           {TEST_ID9: statc}, {TEST_ID10: statc}, {}, ]
    #     self._write_test_files(self.tgt_dir)
    #     self.aimless.run_calcs(3)
    #     self.assertEqual(13, self.handler.stat_jobs.call_count)
    #     for pnum in range(1, 4):
    #         self._chk_bak(pnum)

    def _write_test_files(self, tgt_dir):
        shutil.copy2(os.path.join(TEST_DATA_DIR, "even_forward.rst"),
                     self.fwd_name)
        ofdir = os.path.join(TEST_DATA_DIR, "out")
        for cpname in os.listdir(ofdir):
            shutil.copy2(os.path.join(ofdir, cpname), os.path.join(
                tgt_dir, cpname))

    def _chk_bak(self, pnum):
        path_out_dir = os.path.join(self.tgt_dir, OUT_DIR, str(pnum))
        self.assertTrue(os.path.exists(os.path.join(path_out_dir, FWD_RST_NAME)))

    def tearDown(self):
        shutil.rmtree(self.tgt_dir)


class TestReverse(unittest.TestCase):
    """
    Verify results for AimlessShooter.rev_vel
    """

    def setUp(self):
        self.tgt_dir = tempfile.mkdtemp()
        self.out = StringIO.StringIO()
        self.handler = MagicMock()
        self.aimless = AimlessShooter(TPL_DIR, self.tgt_dir,
                                      TOPO_LOC, {}, {},
                                      sub_handler=self.handler,
                                      out=self.out, wait_secs=.001)
        self.fwd_name = os.path.join(self.tgt_dir, FWD_RST_NAME)
        self.back_name = os.path.join(self.tgt_dir, BACK_RST_NAME)

    def test_even(self):
        ref_name = os.path.join(TEST_DATA_DIR, "even_backward.rst")
        shutil.copy2(os.path.join(TEST_DATA_DIR, "even_forward.rst"), self.fwd_name)
        self.aimless.rev_vel()
        cmp_not_first(self.back_name, ref_name, self)

    def test_even(self):
        ref_name = os.path.join(TEST_DATA_DIR, "odd_backward.rst")
        shutil.copy2(os.path.join(TEST_DATA_DIR, "odd_forward.rst"), self.fwd_name)
        self.aimless.rev_vel()
        cmp_not_first(self.back_name, ref_name, self)

    def test_small_even(self):
        ref_name = os.path.join(TEST_DATA_DIR, "even_small_back.rst")
        shutil.copy2(os.path.join(TEST_DATA_DIR, "even_small_fwd.rst"), self.fwd_name)
        self.aimless.rev_vel()
        cmp_not_first(self.back_name, ref_name, self)

    def tearDown(self):
        shutil.rmtree(self.tgt_dir)


tpres = {}
tpres[1] = {BASIN_FWD_KEY: BRES.A, BASIN_BACK_KEY: BRES.B, ACC_KEY: True}
tpres[2] = {BASIN_FWD_KEY: BRES.INC, BASIN_BACK_KEY: BRES.B}
tpres[3] = {BASIN_FWD_KEY: BRES.A, BASIN_BACK_KEY: BRES.A}


class TestReports(unittest.TestCase):
    def test_text(self):
        tgt = StringIO.StringIO()
        write_text_report(tpres, tgt)
        with open(os.path.join(TEST_DATA_DIR, "test_report.txt")) as ref_rep:
            self.assertEqual(ref_rep.read(), tgt.getvalue())

    def test_text(self):
        tgt = StringIO.StringIO()
        write_csv_report(tpres, tgt, linesep='\n')
        with open(os.path.join(TEST_DATA_DIR, "test_report.csv")) as ref_rep:
            self.assertEqual(ref_rep.read(), tgt.getvalue())

# Default Runner #
if __name__ == '__main__':
    unittest.main()