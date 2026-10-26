import datetime as dt
import unittest
from scripts.cliprausch.scheduling import due_slot,preparation_due
from scripts.cliprausch.clock import plan
from test_core import config,item,Store,NOW
class SchedulingTests(unittest.TestCase):
    def test_delayed_start_does_not_drop_todays_due_slot(self):
        now=dt.datetime(2026,10,26,12,16,tzinfo=dt.timezone.utc)
        self.assertEqual(due_slot(config(),{'attempts':[]},now),'2026-10-26/12:17')
    def test_consumed_slots_and_previous_day_are_not_reused(self):
        now=dt.datetime(2026,10,26,12,16,tzinfo=dt.timezone.utc)
        state={'attempts':[{'slot':'2026-10-26/12:17'}]}
        self.assertIsNone(due_slot(config(),state,now))
        self.assertIsNone(due_slot(config(),state,now.replace(hour=7)))
    def test_empty_stock_prepares_outside_old_narrow_windows(self):
        now=dt.datetime(2026,10,26,12,16,tzinfo=dt.timezone.utc)
        self.assertTrue(preparation_due(config(),{'queue':[]},now))
        self.assertFalse(preparation_due(config(),{'queue':[],'last_prepare_at':now.isoformat()},now))
    def test_clock_dispatches_ready_clip_and_never_duplicates_active_jobs(self):
        state=Store().state
        self.assertEqual(plan(config(),state,[],NOW),'dispatch_publish')
        self.assertEqual(plan(config(),state,[{'head_branch':'main','status':'in_progress'}],NOW),'active_pipeline')
    def test_clock_replenishes_empty_stock_and_respects_reconcile_backoff(self):
        state=Store().state;state['queue']=[]
        self.assertEqual(plan(config(),state,[],NOW),'dispatch_prepare')
        state['attempts']=[dict(item(),status='pending',reserved_at=NOW.isoformat(),last_checked_at=NOW.isoformat())]
        self.assertEqual(plan(config(),state,[],NOW),'reconciliation_backoff')

    def test_four_delayed_opportunities_send_once_each_with_spacing(self):
        from scripts.cliprausch.core import run_one,seal
        from test_core import Gateway
        state=Store();state.state['queue']=[]
        for index in range(4):
            row=item();row.update(clip_id='ClipTest'+str(index),sha256='a'*63+str(index),source_sha256='b'*63+str(index),
                source_created_at=f'2026-10-26T0{index}:00:00Z')
            row['review']['approved_sha256']=seal(row);state.state['queue'].append(row)
        class Gate(Gateway):
            def create_post(self,*args):
                assert self.store.state['attempts'][-1]['status']=='reserved'
                self.calls+=1;return {'id':str(self.calls)*24}
            def verify(self,post):return True
        gate=Gate(state)
        start=dt.datetime(2026,10,26,15,0,tzinfo=dt.timezone.utc)
        for index in range(4):
            now=start+dt.timedelta(minutes=151*index)
            self.assertEqual(run_one(config(),state,gate,now),'pending')
            gate.post=lambda ident,now=now:{'id':ident,'channelId':'a'*24,'status':'sent',
                'sentAt':(now+dt.timedelta(seconds=30)).isoformat(),'externalLink':'https://tiktok.com/@cliprauschxl/video/'+str(1234567890123456780+gate.calls)}
            self.assertEqual(run_one(config(),state,gate,now+dt.timedelta(minutes=1),immediate=True),'verified_public')
        self.assertEqual(gate.calls,4)
        self.assertEqual(len({a['slot'] for a in state.state['attempts']}),4)
        self.assertEqual(state.state['queue'],[])

    def test_missing_completed_artifact_is_cleared_and_clock_can_prepare(self):
        from scripts.cliprausch.automatic import discard_missing_artifacts
        state=Store().state;state['queue']=[dict(item(),review={},artifact_run_id='123')]
        class API:
            def call(self,method,path):return {'artifacts':[]} if '/artifacts?' in path else {'status':'completed'}
        self.assertEqual(plan(config(),state,[],NOW),'dispatch_publish')
        self.assertTrue(discard_missing_artifacts(config(),state,API(),NOW))
        self.assertEqual(plan(config(),state,[],NOW),'dispatch_prepare')
        self.assertEqual(state['technical_failures'][0]['reason'],'artifact_unavailable_after_run_completed')
    def test_temporarily_unavailable_artifacts_do_not_starve_preparation(self):
        state=Store().state;state['queue']=[dict(item(),review={},artifact_run_id='123')]
        state['last_host_check_at']=NOW.isoformat()
        self.assertEqual(plan(config(),state,[],NOW),'dispatch_prepare')
