#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_aimless
----------------------------------

Tests for `aimless` module.
"""
import os
import tempfile

import unittest

from aimless.aimless import (calc_params, TOTAL_STEPS_KEY, BW_STEPS_KEY,
                             FW_STEPS_KEY, DT_STEPS_KEY, BW_OUT_KEY,
                             FW_OUT_KEY, DT_OUT_KEY, write_tpl_files, TPL_LIST)
from aimless.main import (CFG_DEFAULTS, TPL_DIR_KEY, TGT_DIR_KEY)

TS_VAL = 1000
FWBW_VAL = TS_VAL / 2
DT_VAL = TS_VAL / 100
FWBW_OUT_VAL = FWBW_VAL - 1
DT_OUT_VAL = DT_VAL - 1


class TestCalc(unittest.TestCase):
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
    def setUp(self):
        self.directory_name = tempfile.mkdtemp()
        self.params = calc_params(TS_VAL)

    def test_defaults(self):
        tgt_dir = CFG_DEFAULTS[TGT_DIR_KEY]
        self.del_tgts(tgt_dir)
        try:
            write_tpl_files(CFG_DEFAULTS[TPL_DIR_KEY], tgt_dir, self.params)
            self.check_tgts(tgt_dir)
        finally:
            self.del_tgts(tgt_dir)

    def check_tgts(self, tgt_dir):
        for tpl_name, tgt_name, tpl_desc in TPL_LIST:
            self.assertTrue(os.path.exists(os.path.join(tgt_dir, tgt_name)))

    def del_tgts(self, tgt_dir):
        for tpl_name, tgt_name, tpl_desc in TPL_LIST:
            os.remove(os.path.join(tgt_dir, tgt_name))
            self.assertFalse(os.path.exists(os.path.join(tgt_dir, tgt_name)))

    def tearDown(self):
        os.removedirs(self.directory_name)


if __name__ == '__main__':
    unittest.main()