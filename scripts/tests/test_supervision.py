"""Resource bounds and descendant cleanup; not OS-sandbox tests."""
from pathlib import Path
import os
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from seedlib.processes import supervise
from run_candidate import run

class SupervisionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)

    def command(self,code,**kwargs):
        return supervise([sys.executable,'-c',code],cwd=self.root,timeout=kwargs.pop('timeout',3),**kwargs)

    def test_stdout_stderr_and_exit_status(self):
        result=self.command('import sys; print("out"); print("err",file=sys.stderr)')
        self.assertEqual(result.status,'PASS');self.assertIn(b'out',result.stdout);self.assertIn(b'err',result.stderr)

    def test_nonzero_is_failure(self):
        self.assertEqual(self.command('raise SystemExit(3)').status,'FAIL')

    def test_output_capture_is_bounded_while_running(self):
        result=self.command('import sys; sys.stdout.write("x"*1000000); sys.stdout.flush()',max_output_bytes=4096)
        self.assertEqual(result.reason,'OUTPUT_LIMIT')
        self.assertLessEqual(len(result.stdout)+len(result.stderr),4096)

    def test_bounded_input_output_exchange(self):
        result=self.command('import sys; print(sys.stdin.read())',stdin=b'hello')
        self.assertEqual(result.status,'PASS');self.assertIn(b'hello',result.stdout)

    def test_timeout_is_explicit(self):
        result=self.command('import time; time.sleep(10)',timeout=.2)
        self.assertEqual(result.reason,'TIMEOUT')
        self.assertLess(result.duration_seconds,3)

    def test_stop_is_polled_during_command(self):
        stop=self.root/'STOP'
        timer=threading.Timer(.2,lambda:stop.touch());timer.start();self.addCleanup(timer.join)
        result=self.command('import time; time.sleep(10)',stop_file=stop)
        self.assertEqual(result.status,'STOPPED')

    def test_preexisting_stop_prevents_start(self):
        stop=self.root/'STOP';stop.touch()
        result=self.command('from pathlib import Path; Path("ran").touch()',stop_file=stop)
        self.assertEqual(result.status,'STOPPED');self.assertFalse((self.root/'ran').exists())

    def test_missing_executable_is_blocked(self):
        result=supervise(['definitely-missing-executable-seed'],cwd=self.root,timeout=1)
        self.assertEqual(result.status,'BLOCKED')

    @unittest.skipUnless(os.name=='posix','POSIX process-session guarantee')
    def test_candidate_timeout_kills_confirmed_child(self):
        child='from pathlib import Path; import time; Path("started").touch(); time.sleep(1.2); Path("escaped").touch()'
        parent='import subprocess,sys,time; subprocess.Popen([sys.executable,"-S","-c",'+repr(child)+']); time.sleep(10)'
        cfg={'kind':'external','argv':['{python}','-S','-c',parent],'timeout_seconds':.8}
        rows=run(self.root,[{'id':'x','input':'synthetic'}],cfg,True)
        self.assertTrue((self.root/'started').exists(),'Child must actually start for this regression to be meaningful')
        self.assertEqual(rows[0]['status'],'ERROR');self.assertEqual(rows[0]['error_code'],'TIMEOUT')
        time.sleep(.9)
        self.assertFalse((self.root/'escaped').exists())

    @unittest.skipUnless(os.name=='posix','POSIX process-session guarantee')
    def test_finished_parent_does_not_leave_child(self):
        child='from pathlib import Path; import time; Path("started").touch(); time.sleep(1); Path("escaped").touch()'
        parent='import subprocess,sys,time; from pathlib import Path; subprocess.Popen([sys.executable,"-S","-c",'+repr(child)+']);\nwhile not Path("started").exists(): time.sleep(.01)'
        result=self.command(parent)
        self.assertEqual(result.status,'PASS');self.assertTrue((self.root/'started').exists())
        time.sleep(1.1);self.assertFalse((self.root/'escaped').exists())
