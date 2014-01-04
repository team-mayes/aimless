import filecmp
import os
import shutil
import tempfile
import unittest
from aimless import init_loc
from aimless.init_loc import DEF_SKEL_LOC


class TestInit(unittest.TestCase):
    "Tests that we properly copy the skel files to the dest."

    def setUp(self):
        pass

    def test_no_args(self):
        with self.assertRaises(SystemExit) as cm:
            init_loc.main([])
        self.assertEqual(2, cm.exception.code)

    def test_tmp_dest(self):
        tgt_dir = tempfile.mkdtemp()
        try:
            init_loc.main([tgt_dir])
            dcmp = filecmp.dircmp(DEF_SKEL_LOC, tgt_dir)
            self._err_on_diffs(dcmp)
        finally:
            shutil.rmtree(tgt_dir)

    def _err_on_diffs(self, dcmp):
        """Error on any diffs in the given directory comparison.
        Calls subdirs recursively."""

        if dcmp.diff_files:
            for name in dcmp.diff_files:
                print("diff_file %s found in %s and %s" % (name, dcmp.left,
                  dcmp.right))
                self.fail("Differences!")

        for sub_dcmp in dcmp.subdirs.values():
            self._err_on_diffs(sub_dcmp)

