import copy
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from milestone_monitor.state import apply_snapshot
from milestone_monitor import ContractError

DRIFT = json.loads((Path(__file__).parents[1] / 'examples/drift.json').read_text())

class StateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / 'state.sqlite3'

    def apply(self, snapshot):
        return apply_snapshot(self.db, snapshot)

    def counts(self):
        with sqlite3.connect(self.db) as db:
            return db.execute('SELECT transition, count(*) FROM history GROUP BY transition').fetchall()

    def test_open_then_repeat_suppresses_history(self):
        first = self.apply(DRIFT)
        self.assertEqual(['opened'] * 4, [x['transition'] for x in first['transitions']])
        again = self.apply(DRIFT)
        self.assertEqual(['unchanged'] * 4, [x['transition'] for x in again['transitions']])
        self.assertEqual([('opened', 4)], self.counts())
        self.assertEqual(0, again['notification_count'])

    def test_changed_snapshot_retains_identity(self):
        self.apply(DRIFT)
        changed = copy.deepcopy(DRIFT)
        changed['as_of'] = '2026-09-27T12:00:00+05:30'
        changed['tracker'][1]['due_at'] = '2026-10-09T12:00:00+05:30'
        result = self.apply(changed)
        self.assertIn('changed', [x['transition'] for x in result['transitions']])
        self.assertIn(('changed', 2), self.counts())  # stale age also changed

    def test_resolution_and_reopen(self):
        self.apply(DRIFT)
        aligned = copy.deepcopy(DRIFT)
        aligned['as_of'] = '2026-09-27T12:00:00+05:30'
        aligned['tracker'] = copy.deepcopy(aligned['plan'])
        result = self.apply(aligned)
        self.assertEqual(['resolved'] * 4, [x['transition'] for x in result['transitions']])
        later = copy.deepcopy(DRIFT)
        later['as_of'] = '2026-09-28T12:00:00+05:30'
        self.assertEqual(['reopened'] * 4, [x['transition'] for x in self.apply(later)['transitions']])
        self.assertIn(('reopened', 4), self.counts())

    def test_invalid_input_does_not_mutate(self):
        self.apply(DRIFT)
        bad = copy.deepcopy(DRIFT)
        bad['tracker'][0]['due_at'] = 'not-a-time'
        with self.assertRaises(ContractError): self.apply(bad)
        self.assertEqual([('opened', 4)], self.counts())

    def test_older_snapshot_does_not_mutate(self):
        later = copy.deepcopy(DRIFT)
        later['as_of'] = '2026-09-27T12:00:00+05:30'
        self.apply(later)
        changed = copy.deepcopy(DRIFT)
        changed['as_of'] = '2026-09-26T11:00:00+05:30'
        with self.assertRaises(ValueError): self.apply(changed)
        self.assertEqual([('opened', 4)], self.counts())

    def test_other_project_state_is_isolated(self):
        self.apply(DRIFT)
        second = copy.deepcopy(DRIFT)
        second['project_id'] = 'other-project'
        self.apply(second)
        self.assertEqual([('opened', 8)], self.counts())

if __name__ == '__main__': unittest.main()
