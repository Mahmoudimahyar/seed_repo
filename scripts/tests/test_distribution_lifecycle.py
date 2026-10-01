"""Release and skill retirement must hold across complete, unmocked lifecycles."""
from pathlib import Path
import json
import shutil
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import seed
from package_release import package
from seedlib.common import dump

ROOT=Path(__file__).resolve().parents[2]


def template_fixture(destination):
    # Use the reviewed distribution inventory, not a developer's local files. Works
    # in an initialized downstream project without copying private application docs.
    policy=json.loads((ROOT/'quality/export-policy.json').read_text())
    for name in policy['files']:
        target=destination/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,target)
    state=json.loads((destination/'seed.json').read_text())
    state.update(kind='template',project=None,phase='discovery',capabilities={key:False for key in seed.CAPABILITIES})
    (destination/'seed.json').write_text(dump(state))
    shutil.copyfile(destination/'quality/template-checks.json',destination/'quality/seed-checks.json')


class DistributionLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'repo';self.root.mkdir()
        template_fixture(self.root)
        self.out=Path(self.temp.name)/'release'

    def write(self,relative,text):
        path=self.root/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)

    def test_full_validate_package_extract_omits_runtime(self):
        self.write('.seed-local/private-runtime.txt','synthetic private material')
        self.assertEqual(seed.validate(self.root,public=True),[])
        result=package(self.root,self.out)
        with zipfile.ZipFile(result['path']) as archive:
            self.assertFalse(any('.seed-local' in name for name in archive.namelist()))
            archive.extractall(Path(self.temp.name)/'fresh')
        self.assertEqual(seed.validate(Path(self.temp.name)/'fresh/seed-repo',public=True),[])

    def test_local_client_configs_block_public_export_without_echo(self):
        for name in ('.codex/config.toml','.mcp.json','.cursor/mcp.json','.claude/settings.local.json','CLAUDE.local.md'):
            with self.subTest(name=name):
                self.write(name,'synthetic-private-do-not-echo')
                problems=seed.validate(self.root,public=True)
                self.assertTrue(problems);self.assertNotIn('synthetic-private-do-not-echo','\n'.join(problems))
                with self.assertRaises(ValueError):package(self.root,self.out)
                (self.root/name).unlink()
        self.assertFalse(self.out.exists())

    def test_unexpected_distribution_addition_is_not_exported(self):
        self.write('unreviewed-notes.md','Notes are not automatically suitable for public distribution.')
        with self.assertRaisesRegex(ValueError,'Unreviewed distribution'):
            package(self.root,self.out)

    def test_explicit_review_can_admit_a_new_safe_file(self):
        self.write('reviewed-notes.md','A reviewed and intentionally public maintainer document.')
        policy=json.loads((self.root/'quality/export-policy.json').read_text());policy['files'].append('reviewed-notes.md')
        self.write('quality/export-policy.json',dump(policy))
        with zipfile.ZipFile(package(self.root,self.out)['path']) as archive:
            self.assertIn('seed-repo/reviewed-notes.md',archive.namelist())

    def test_unsafe_allowlist_cannot_admit_local_config(self):
        policy=json.loads((self.root/'quality/export-policy.json').read_text());policy['files'].append('.codex/config.toml')
        self.write('quality/export-policy.json',dump(policy));self.write('.codex/config.toml','synthetic local data')
        with self.assertRaises(ValueError):package(self.root,self.out)

    def test_retirement_removes_only_generated_unchanged_skill(self):
        shutil.rmtree(self.root/'.agents/skills/seed-debug')
        plan=seed.skill_plan(self.root)
        self.assertIn('.claude/skills/seed-debug/SKILL.md',seed.skill_retirements(self.root,plan))
        self.assertTrue(any('Retired skill' in issue for issue in seed.validate(self.root)))
        self.write('.claude/skills/seed-debug/local-note.txt','Manual material must be preserved.')
        seed.apply_skills(self.root,plan)
        self.assertFalse((self.root/'.claude/skills/seed-debug/SKILL.md').exists())
        self.assertTrue((self.root/'.claude/skills/seed-debug/local-note.txt').exists())
        self.assertEqual(seed.skill_retirements(self.root,seed.skill_plan(self.root)),[])

    def test_edited_retired_skill_is_never_deleted(self):
        shutil.rmtree(self.root/'.agents/skills/seed-debug')
        path=self.root/'.claude/skills/seed-debug/SKILL.md';path.write_text(path.read_text()+'\nLocal deliberate edit.\n')
        with self.assertRaisesRegex(ValueError,'Manually changed'):seed.skill_plan(self.root)
        self.assertTrue(path.exists())

    def test_untracked_orphan_is_not_silently_left_discoverable(self):
        self.write('.claude/skills/seed-orphan/SKILL.md','---\nname: seed-orphan\ndescription: A local custom copy.\n---\n')
        with self.assertRaisesRegex(ValueError,'orphan'):seed.skill_plan(self.root)
        self.assertTrue((self.root/'.claude/skills/seed-orphan/SKILL.md').exists())

    def test_rename_retires_old_and_creates_new(self):
        old=self.root/'.agents/skills/seed-debug';new=self.root/'.agents/skills/seed-diagnostics';old.rename(new)
        path=new/'SKILL.md';path.write_text(path.read_text().replace('name: seed-debug','name: seed-diagnostics'))
        seed.apply_skills(self.root,seed.skill_plan(self.root))
        self.assertFalse((self.root/'.claude/skills/seed-debug/SKILL.md').exists())
        self.assertTrue((self.root/'.claude/skills/seed-diagnostics/SKILL.md').exists())

    def test_preview_does_not_retire_files(self):
        shutil.rmtree(self.root/'.agents/skills/seed-debug');seed.skill_plan(self.root)
        self.assertTrue((self.root/'.claude/skills/seed-debug/SKILL.md').exists())
