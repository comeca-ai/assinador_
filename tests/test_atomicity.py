from unittest.mock import patch
import test_platform as platform

# Reuse integration fixtures without inheriting the test suite.
class AtomicityTests(platform.PlatformFixtures):
    def test_finalization_failure_rolls_back_confirmation(self):
        eid,_,tokens=self.available();t=tokens[0];d=self.accept(t)
        with patch('backend.app.final_pdf',side_effect=RuntimeError('simulated failure')):
            with self.assertRaises(RuntimeError):self.confirm(t,d)
        with self.app.state.db.tx() as db:
            self.assertEqual(db.execute('SELECT status FROM envelopes WHERE id=?',(eid,)).fetchone()[0],'SENT')
            self.assertEqual(db.execute('SELECT COUNT(*) FROM artifacts').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM audit_events WHERE event_type="INTENT_CONFIRMED_TEST"').fetchone()[0],0)
        self.assertEqual(self.confirm(t,d).status_code,200)

