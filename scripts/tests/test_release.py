from pathlib import Path
from unittest.mock import patch
import hashlib
import json
import os
import sys
import tempfile
import unittest
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from package_release import package

class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)/'repo';self.root.mkdir()
        (self.root/'VERSION').write_text('0.2.0-rc.1')
        (self.root/'seed.json').write_text(json.dumps({'kind':'template','distribution_version':'0.2.0-rc.1'}))
        (self.root/'.gitignore').write_text('private/\n')
        self.out=Path(self.temp.name)/'release'
        (self.root/'quality').mkdir()
        (self.root/'quality/export-policy.json').write_text(json.dumps({'schema_version':1,'files':['VERSION','seed.json','.gitignore','quality/export-policy.json']}))
    def export(self):
        with patch('package_release.validate',return_value=[]):return package(self.root,self.out)
    def test_exports_hidden_files_and_checksums(self):
        r=self.export();p=Path(r['path']);self.assertEqual(r['sha256'],hashlib.sha256(p.read_bytes()).hexdigest())
        with zipfile.ZipFile(p) as z:
            self.assertIn('seed-repo/.gitignore',z.namelist())
            lines=z.read('seed-repo/MANIFEST.sha256').decode().splitlines()
            for line in lines:
                digest,path=line.split('  ',1);self.assertEqual(digest,hashlib.sha256(z.read('seed-repo/'+path)).hexdigest())
    def test_duplicate_export_refused(self):
        self.export()
        with self.assertRaises(ValueError):self.export()
    def test_version_mismatch_refused(self):
        (self.root/'VERSION').write_text('9.9.9')
        with self.assertRaises(ValueError):self.export()
    def test_initialized_application_not_exported(self):
        (self.root/'seed.json').write_text(json.dumps({'kind':'project'}))
        with self.assertRaises(ValueError):self.export()
    def test_secret_filename_rejected(self):
        (self.root/'.env').write_text('secret')
        with self.assertRaises(ValueError):self.export()
    def test_font_or_third_party_archive_not_exported(self):
        (self.root/'font.ttf').write_bytes(b'not a font')
        with self.assertRaises(ValueError):self.export()
    def test_private_and_local_logs_excluded(self):
        for d in ('private','.seed-local','.seed-ci-artifacts'):
            (self.root/d).mkdir();(self.root/d/'secret.txt').write_text('private data')
        with zipfile.ZipFile(self.export()['path']) as z:
            self.assertFalse(any('secret.txt' in p for p in z.namelist()))
    def test_validation_failure_stops_export(self):
        with patch('package_release.validate',return_value=['broken']):
            with self.assertRaises(ValueError):package(self.root,self.out)
    @unittest.skipUnless(os.name=='posix','POSIX symlink test')
    def test_symlink_refused(self):
        (self.root/'pointer.md').symlink_to(self.root/'VERSION')
        with self.assertRaises(ValueError):self.export()
