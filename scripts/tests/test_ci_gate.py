from pathlib import Path
import itertools
import os
import re
import subprocess
import unittest
ROOT=Path(__file__).resolve().parents[2]

class RequiredGateTests(unittest.TestCase):
    @unittest.skipUnless(os.name=='posix','Shell gate is configured on Linux')
    def test_all_upstream_state_combinations(self):
        text=(ROOT/'.github/workflows/seed-ci.yml').read_text()
        command=re.search(r'run: (test "\$CHECKS_RESULT".*)',text).group(1)
        states=('success','failure','cancelled','skipped')
        for checks,mcp,scope in itertools.product(states,repeat=3):
            with self.subTest(checks=checks,mcp=mcp,scope=scope):
                r=subprocess.run(['bash','-c',command],env={**os.environ,'CHECKS_RESULT':checks,'MCP_RESULT':mcp,'SCOPE_RESULT':scope},capture_output=True)
                self.assertEqual(r.returncode==0,checks==mcp==scope=='success')
