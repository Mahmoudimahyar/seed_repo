"""Behavioral tests for the optional local decision planner; no live human approvals."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from seedlib.common import dump, sha
from seedlib.planning import PlanningStore, check_graph


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.time = datetime(2026, 9, 20, tzinfo=timezone.utc)
        self.store = PlanningStore(self.root, clock=lambda: self.time)
        self.map = {
            'schema_version': 1, 'id': 'organizer',
            'destination': 'Specify a local document organizer without adding a SaaS.',
            'scope': 'Resolve privacy and parser decisions for the first CLI slice.',
            'constraints': ['Do not send documents to external services.'],
            'exclusions': ['A marketing website is not requested.'],
            'fog': [{'id': 'collaboration', 'description': 'Future collaboration needs are not yet precise.'}],
            'max_parallel_claims': 1,
        }
        self.store.create(self.map)
        self.write('policy.md', 'Synthetic policy fixture: local read-only planning only. No production authority.')
        self.write('facts.md', 'Synthetic source evidence: local parsing is feasible for the approved samples.')
        self.write('human.md', 'Synthetic human decision fixture. This is not a real authenticated approval.')

    def write(self, path, content):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')

    def ticket(self, name='privacy', depends=(), resolver='interview'):
        return {
            'id': name, 'question': 'May any approved input documents leave the local device?',
            'resolver': resolver, 'priority': 1,
            'priority_reason': 'Privacy determines which parser options are eligible.',
            'depends_on': [{'ticket_id': item, 'allowed_outcomes': ['accepted']} for item in depends],
            'required_evidence': ['facts.md'],
            'evidence_requirements': ['A documented user choice based on the current evidence.'],
            'authority': {'mode': 'human_required', 'owner': 'maintainer', 'policy_ref': 'policy.md'},
            'workflow_contract': None,
            'budgets': {'max_minutes': 10, 'max_cost_usd': 0},
        }

    def add(self, doc=None):
        doc = doc or self.ticket()
        return self.store.add('organizer', doc)

    def record(self, name, outcome='accepted', **updates):
        value = {
            'id': name + '.answer.v1', 'workflow_id': name,
            'recorded_at': self.time.isoformat(),
            'decision': 'Keep the approved documents local; the source supports this decision.',
            'evidence_refs': ['facts.md'], 'policy_version': 'fixture-v1',
            'policy_sha256': sha((self.root/'policy.md').read_bytes()),
            'scope': self.map['scope'],
            'authority': {'kind': 'human_approval', 'actor': 'maintainer', 'evidence_reference': 'human.md'},
            'exception': False, 'expires_at': None, 'outcome': outcome,
            'observed_result_reference': None, 'supersedes': None,
        }
        value.update(updates)
        path = 'answers/' + name + '.json'
        self.write(path, dump(value))
        return path

    def resolve(self, name='privacy', outcome='accepted', **kwargs):
        current = self.store.get('organizer', name)
        claim = self.store.claim('organizer', name, 'run-fixture', current['revision'], ttl_seconds=120)
        return self.store.resolve('organizer', name, self.record(name, outcome),
                                  current['revision'], claim['token'], **kwargs)

    def status(self, name):
        return self.store.get('organizer', name)['effective_state']

    def test_new_map_is_not_implementation_authority(self):
        report = self.store.handoff('organizer')
        self.assertIn('not authorization', report['boundary'])
        self.assertEqual(report['destination'], self.map['destination'])

    def test_duplicate_map_rejected(self):
        with self.assertRaises(ValueError): self.store.create(self.map)

    def test_map_schema_rejects_unknown_permission_override(self):
        candidate = deepcopy(self.map); candidate['id'] = 'unsafe'; candidate['auto_authorize'] = True
        with self.assertRaises(ValueError): self.store.create(candidate)

    def test_duplicate_ticket_rejected(self):
        self.add()
        with self.assertRaises(ValueError): self.add()

    def test_missing_dependency_rejected(self):
        with self.assertRaises(ValueError): self.add(self.ticket('parser', ['missing']))

    def test_cycles_are_rejected(self):
        a = self.ticket('a', ['b']); b = self.ticket('b', ['a'])
        with self.assertRaises(ValueError): check_graph([a,b])

    def test_self_dependency_rejected(self):
        with self.assertRaises(ValueError): self.add(self.ticket('self', ['self']))

    def test_unknown_ticket_fields_rejected(self):
        doc = self.ticket(); doc['argv'] = ['echo', 'not a command task']
        with self.assertRaises(ValueError): self.add(doc)

    def test_negative_budget_rejected(self):
        doc = self.ticket(); doc['budgets']['max_cost_usd'] = -1
        with self.assertRaises(ValueError): self.add(doc)

    def test_missing_required_evidence_blocks_resolver(self):
        doc = self.ticket(); doc['required_evidence'] = ['missing.md']; self.add(doc)
        self.assertEqual(self.status('privacy'), 'blocked')

    def test_human_question_is_awaiting_human_not_guessed(self):
        self.add()
        self.assertEqual(self.status('privacy'), 'awaiting-human')

    def test_autonomous_source_lookup_is_eligible(self):
        doc = self.ticket(resolver='source_lookup'); doc['authority']['mode'] = 'delegated'; self.add(doc)
        self.assertEqual(self.status('privacy'), 'open')

    def test_claim_does_not_approve_question(self):
        self.add(); self.store.claim('organizer','privacy','run-one',1)
        self.assertEqual(self.status('privacy'), 'exploring')
        self.assertIsNone(self.store.get('organizer','privacy')['resolution'])

    def test_dependency_remains_precise_but_blocked(self):
        self.add(); self.add(self.ticket('parser', ['privacy']))
        self.assertEqual(self.status('parser'), 'blocked')
        self.assertEqual(len(self.store.handoff('organizer')['fog']), 1)

    def test_accepted_dependency_unblocks(self):
        self.add(); self.add(self.ticket('parser',['privacy'])); self.resolve()
        self.assertEqual(self.status('parser'), 'awaiting-human')

    def test_rejected_is_not_accepted(self):
        self.add(); self.add(self.ticket('parser',['privacy'])); self.resolve(outcome='rejected')
        self.assertEqual(self.status('parser'), 'blocked')

    def test_explicit_rejected_outcome_can_satisfy(self):
        self.add(); doc=self.ticket('parser',['privacy']); doc['depends_on'][0]['allowed_outcomes']=['rejected']
        self.add(doc); self.resolve(outcome='rejected')
        self.assertEqual(self.status('parser'), 'awaiting-human')

    def test_excluded_is_never_dependency_success(self):
        self.add(); self.add(self.ticket('parser',['privacy'])); self.resolve(terminal='out-of-scope')
        self.assertEqual(self.status('privacy'), 'out-of-scope')
        self.assertEqual(self.status('parser'), 'blocked')

    def test_superseded_is_not_success(self):
        self.add(); self.add(self.ticket('replacement')); self.add(self.ticket('parser',['privacy']))
        self.resolve(terminal='superseded', replacement='replacement')
        self.assertEqual(self.status('parser'), 'blocked')

    def test_supersession_requires_valid_replacement(self):
        self.add()
        with self.assertRaises(ValueError): self.resolve(terminal='superseded', replacement='missing')

    def test_supersession_cycle_is_rejected(self):
        self.add(); self.add(self.ticket('replacement'))
        self.resolve(terminal='superseded', replacement='replacement')
        with self.assertRaises(ValueError):
            self.resolve('replacement', terminal='superseded', replacement='privacy')

    def test_resolution_must_reference_existing_decision_schema(self):
        self.add(); claim=self.store.claim('organizer','privacy','run-one',1); self.write('bad.json','{}')
        with self.assertRaises(ValueError): self.store.resolve('organizer','privacy','bad.json',1,claim['token'])

    def test_proposed_answer_is_not_a_resolution(self):
        self.add()
        with self.assertRaises(ValueError): self.resolve(outcome='proposed')

    def test_wrong_scope_rejected(self):
        self.add(); c=self.store.claim('organizer','privacy','run-one',1)
        path=self.record('privacy', scope='An entirely different scope')
        with self.assertRaises(ValueError): self.store.resolve('organizer','privacy',path,1,c['token'])

    def test_agent_cannot_record_policy_answer_to_nondelegated_question(self):
        self.add(); c=self.store.claim('organizer','privacy','run-one',1)
        path=self.record('privacy', authority={'kind':'policy','actor':'run-one','evidence_reference':'policy.md'})
        with self.assertRaises(ValueError): self.store.resolve('organizer','privacy',path,1,c['token'])

    def test_wrong_human_owner_rejected(self):
        self.add(); c=self.store.claim('organizer','privacy','run-one',1)
        path=self.record('privacy', authority={'kind':'human_approval','actor':'someone-else','evidence_reference':'human.md'})
        with self.assertRaises(ValueError): self.store.resolve('organizer','privacy',path,1,c['token'])

    def test_wrong_policy_hash_rejected(self):
        self.add(); c=self.store.claim('organizer','privacy','run-one',1)
        path=self.record('privacy', policy_sha256='0'*64)
        with self.assertRaises(ValueError): self.store.resolve('organizer','privacy',path,1,c['token'])

    def test_expired_exception_rejected(self):
        self.add(); c=self.store.claim('organizer','privacy','run-one',1)
        path=self.record('privacy', exception=True, expires_at=(self.time-timedelta(seconds=1)).isoformat())
        with self.assertRaises(ValueError): self.store.resolve('organizer','privacy',path,1,c['token'])

    def test_time_expiry_invalidates_accepted_answer(self):
        self.add(); c=self.store.claim('organizer','privacy','run-one',1)
        path=self.record('privacy', exception=True, expires_at=(self.time+timedelta(minutes=5)).isoformat())
        self.store.resolve('organizer','privacy',path,1,c['token'])
        self.time += timedelta(minutes=6)
        self.assertEqual(self.status('privacy'),'stale')

    def test_source_change_invalidates_resolution(self):
        self.add(); self.resolve(); self.write('facts.md','The approved evidence changed materially.')
        self.assertEqual(self.status('privacy'),'stale')

    def test_source_revert_restores_exact_snapshot_but_revisions_do_not(self):
        old=(self.root/'facts.md').read_text(); self.add(); self.resolve()
        self.write('facts.md','Different evidence'); self.assertEqual(self.status('privacy'),'stale')
        self.write('facts.md',old); self.assertEqual(self.status('privacy'),'resolved')

    def test_policy_change_invalidates_resolution(self):
        self.add(); self.resolve(); self.write('policy.md','Changed policy forbids the previous action.')
        self.assertEqual(self.status('privacy'),'stale')

    def test_decision_record_change_invalidates_resolution(self):
        self.add(); self.resolve(); self.write('answers/privacy.json','{}')
        self.assertEqual(self.status('privacy'),'stale')

    def test_revised_prerequisite_marks_transitive_dependents_stale(self):
        self.add(); self.add(self.ticket('parser',['privacy'])); self.add(self.ticket('build',['parser']))
        self.resolve(); self.resolve('parser'); self.resolve('build')
        doc=self.ticket(); doc['question']='Must documents also support a remote confidential deployment?'
        self.store.revise('organizer',doc,2)
        self.assertEqual(self.status('parser'),'stale'); self.assertEqual(self.status('build'),'stale')

    def test_unrelated_ticket_addition_does_not_stale_resolution(self):
        self.add(); self.resolve(); self.add(self.ticket('unrelated'))
        self.assertEqual(self.status('privacy'),'resolved')

    def test_map_scope_change_stales_resolution(self):
        self.add(); self.resolve(); spec=deepcopy(self.map); spec['scope']='A different release scope with hosted processing.'
        self.store.revise_map(spec,1)
        self.assertEqual(self.status('privacy'),'stale')

    def test_ticket_revision_conflict_rejected(self):
        self.add(); self.store.revise('organizer',self.ticket(),1)
        with self.assertRaises(ValueError): self.store.revise('organizer',self.ticket(),1)

    def test_open_claim_prevents_unowned_revision(self):
        self.add(); self.store.claim('organizer','privacy','run-one',1)
        with self.assertRaises(ValueError): self.store.revise('organizer',self.ticket(),1)

    def test_history_preserves_prior_answer_when_reopened(self):
        self.add(); self.resolve(); self.store.revise('organizer',self.ticket(),2)
        events=self.store.history('organizer','privacy')
        self.assertTrue(any(e['event']=='resolved' for e in events))
        self.assertEqual(self.status('privacy'),'awaiting-human')

    def test_two_local_thread_claims_are_serialized(self):
        self.add()
        def claim(owner):
            try:
                return self.store.claim('organizer','privacy',owner,1)['token']
            except ValueError:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(claim,['run-a','run-b']))
        self.assertEqual(sum(x is not None for x in results),1)

    def test_capacity_blocks_parallel_unrelated_work(self):
        self.add(); self.add(self.ticket('other')); self.store.claim('organizer','privacy','run-one',1)
        with self.assertRaises(ValueError): self.store.claim('organizer','other','run-two',1)

    def test_expired_claim_can_be_reclaimed_and_old_token_fails(self):
        self.add(); old=self.store.claim('organizer','privacy','run-one',1,ttl_seconds=5)
        self.time += timedelta(seconds=6)
        self.store.claim('organizer','privacy','run-two',1)
        with self.assertRaises(ValueError): self.store.release('organizer','privacy',old['token'])

    def test_live_claim_renewal(self):
        self.add(); c=self.store.claim('organizer','privacy','run-one',1,ttl_seconds=5)
        self.time += timedelta(seconds=4)
        self.store.renew('organizer','privacy',c['token'],ttl_seconds=10)
        self.time += timedelta(seconds=4)
        with self.assertRaises(ValueError): self.store.claim('organizer','privacy','run-two',1)

    def test_stop_blocks_claim_and_resolution_but_allows_release(self):
        self.add(); c=self.store.claim('organizer','privacy','run-one',1)
        self.write('.seed-local/STOP','')
        with self.assertRaises(ValueError): self.store.resolve('organizer','privacy',self.record('privacy'),1,c['token'])
        self.store.release('organizer','privacy',c['token'])
        with self.assertRaises(ValueError): self.store.claim('organizer','privacy','run-two',1)

    def test_secret_evidence_is_not_read(self):
        doc=self.ticket(); doc['required_evidence']=['.env']
        self.write('.env','a value that must not be exposed')
        with self.assertRaises(ValueError): self.add(doc)

    def test_path_traversal_rejected(self):
        doc=self.ticket(); doc['required_evidence']=['../outside']
        with self.assertRaises(ValueError): self.add(doc)

    @unittest.skipUnless(os.name=='posix','POSIX symlink fixture')
    def test_symlink_evidence_rejected(self):
        (self.root/'linked.md').symlink_to(self.root/'facts.md')
        doc=self.ticket(); doc['required_evidence']=['linked.md']
        with self.assertRaises(ValueError): self.add(doc)

    def test_missing_multiple_plan_selection_requires_explicit_choice(self):
        second=deepcopy(self.map);second['id']='second';self.store.create(second)
        with self.assertRaises(ValueError): self.store.handoff()
        self.store.select('organizer')
        self.assertEqual(self.store.handoff()['map_id'],'organizer')

    def test_explicit_selection_cannot_be_overridden_by_newer_map(self):
        self.store.select('organizer');second=deepcopy(self.map);second['id']='newer';self.store.create(second)
        self.assertEqual(self.store.handoff()['map_id'],'organizer')

    def test_handoff_does_not_replay_all_sources_or_tokens(self):
        self.add(); c=self.store.claim('organizer','privacy','run-one',1)
        text=dump(self.store.handoff('organizer','privacy'))
        self.assertNotIn(c['token'],text)
        self.assertNotIn('Synthetic source evidence:',text)
        self.assertIn('policy.md',text)

    def test_handoff_reports_truncation(self):
        for i in range(4): self.add(self.ticket('item-'+str(i)))
        handoff=self.store.handoff('organizer',limit=2)
        self.assertTrue(handoff['truncated']);self.assertLessEqual(len(handoff['frontier']),2)

    def test_handoff_flags_omitted_prerequisites(self):
        for name in ('a','b','c'):
            self.add(self.ticket(name)); self.resolve(name)
        self.add(self.ticket('join',['a','b','c']))
        result=self.store.handoff('organizer','join',limit=2)
        self.assertEqual(len(result['prerequisites']),2)
        self.assertTrue(result['truncated'])

    def test_handoff_flags_omitted_evidence_requirements(self):
        doc=self.ticket()
        doc['evidence_requirements']=['A distinct evidence requirement numbered '+str(i) for i in range(9)]
        self.add(doc)
        result=self.store.handoff('organizer','privacy')
        self.assertTrue(result['active_ticket']['truncated'])
        self.assertTrue(result['truncated'])

    def test_requirements_snapshot_changes_only_for_relevant_decisions(self):
        self.add(); self.resolve()
        req=[{'ticket_id':'privacy','allowed_outcomes':['accepted']}]
        old=self.store.requirements_snapshot('organizer',req)
        self.add(self.ticket('unrelated'))
        self.assertEqual(old,self.store.requirements_snapshot('organizer',req))
        self.write('facts.md','Changed evidence')
        with self.assertRaises(ValueError): self.store.requirements_snapshot('organizer',req)

    def test_snapshot_rejects_unsatisfied_outcome(self):
        self.add();self.resolve(outcome='rejected')
        with self.assertRaises(ValueError):
            self.store.requirements_snapshot('organizer',[{'ticket_id':'privacy','allowed_outcomes':['accepted']}])

    def test_export_is_read_only_and_contains_history_not_claims(self):
        self.add(); self.resolve(); self.store.revise('organizer',self.ticket(),2)
        self.store.claim('organizer','privacy','run-one',3)
        result=self.store.export('organizer')
        self.assertIn('events',result);self.assertNotIn('token',dump(result))
        self.assertEqual(result['backend'],'seed-local-snapshot')

    def test_import_snapshot_preserves_freshness_and_rejects_overwrite(self):
        self.add();self.resolve();snap=self.store.export('organizer')
        with tempfile.TemporaryDirectory() as folder:
            other=Path(folder)
            for p in ('policy.md','facts.md','human.md','answers/privacy.json'):
                dst=other/p;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes((self.root/p).read_bytes())
            store=PlanningStore(other,clock=lambda:self.time);store.import_snapshot(snap)
            self.assertEqual(store.get('organizer','privacy')['effective_state'],'resolved')
            with self.assertRaises(ValueError):store.import_snapshot(snap)

    def test_import_without_matching_sources_is_stale(self):
        self.add();self.resolve();snap=self.store.export('organizer')
        with tempfile.TemporaryDirectory() as folder:
            store=PlanningStore(Path(folder),clock=lambda:self.time);store.import_snapshot(snap)
            self.assertEqual(store.get('organizer','privacy')['effective_state'],'stale')

    def test_import_never_restores_claim_or_auto_selects_among_multiple_maps(self):
        self.add();self.store.claim('organizer','privacy','run-one',1);snap=self.store.export('organizer')
        with tempfile.TemporaryDirectory() as folder:
            store=PlanningStore(Path(folder),clock=lambda:self.time);store.import_snapshot(snap)
            self.assertIsNone(store.get('organizer','privacy')['claim'])

    def test_import_rejects_unknown_or_invalid_snapshot(self):
        snap=self.store.export('organizer');snap['auto_authorize']=True
        with tempfile.TemporaryDirectory() as folder, self.assertRaises(ValueError):
            PlanningStore(Path(folder)).import_snapshot(snap)

    def test_import_rejects_incomplete_resolution_fingerprint(self):
        self.add(); self.resolve(); snapshot=self.store.export('organizer')
        snapshot['tickets'][0]['resolution']['files'].pop('policy.md')
        with tempfile.TemporaryDirectory() as folder, self.assertRaises(ValueError):
            PlanningStore(Path(folder)).import_snapshot(snapshot)

    def test_import_rejects_supersession_cycle(self):
        self.add(); self.add(self.ticket('replacement'))
        self.resolve(terminal='superseded',replacement='replacement')
        snapshot=self.store.export('organizer')
        first=next(row for row in snapshot['tickets'] if row['document']['id']=='privacy')
        second=next(row for row in snapshot['tickets'] if row['document']['id']=='replacement')
        second.update(state='superseded',replacement='privacy',resolution=deepcopy(first['resolution']))
        with tempfile.TemporaryDirectory() as folder, self.assertRaises(ValueError):
            PlanningStore(Path(folder)).import_snapshot(snapshot)

    def test_import_rejects_duplicate_fog_identifiers(self):
        snapshot=self.store.export('organizer')
        snapshot['map']['document']['fog'].append({'id':'collaboration','description':'Another unresolved topic with a conflicting identifier.'})
        with tempfile.TemporaryDirectory() as folder, self.assertRaises(ValueError):
            PlanningStore(Path(folder)).import_snapshot(snapshot)

    def test_schema_exposes_no_code_execution_tool(self):
        doc=self.ticket(resolver='prototype');self.add(doc)
        self.assertEqual(self.status('privacy'),'blocked')
        self.assertFalse((self.root/'src').exists())


if __name__=='__main__': unittest.main()
