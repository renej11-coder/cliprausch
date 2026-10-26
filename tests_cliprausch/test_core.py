import copy
import datetime as dt
import json
import unittest
from pathlib import Path
from scripts.cliprausch.core import slot_at, validate_config, eligible, run_one, seal

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 10, 25, 11, 20, tzinfo=UTC)

def config():
    c = json.loads((Path(__file__).resolve().parents[1]/'scripts/cliprausch/config.json').read_text())
    c.update(channel_id='a'*24, organization_id='b'*24, commissioned=True)
    c['rights'] = {'streamer': {'evidence':'signed-permission-2026-10',
        'expires_at':'2027-01-01T00:00:00Z', 'tiktok':True, 'edit':True, 'audio':True}}
    return c

def item():
    row = dict(clip_id='Clip1234', streamer='streamer', source_sha256='c'*64,
        sha256='d'*64, source_created_at='2026-10-25T09:00:00Z',
        video_url='https://github.com/renej11-coder/cliprausch/releases/download/cliprausch-2026-10/Clip1234.mp4',
        caption='Was ein Clutch! Quelle: streamer #gaming #twitchde',
        duration=24, width=1080, height=1920, category='talk', audio_cleared=True)
    row['review'] = dict(by='editor', watched_full=True, subtitles_checked=True,
        audio_checked=True, frame_checked=True, rights_checked=True, content_checked=True, approved_sha256=seal(row))
    return row

class Store:
    def __init__(self): self.state={'version':1,'account':'cliprauschxl','channel_id':'a'*24,'queue':[item()],'attempts':[]}
    def load(self): return copy.deepcopy(self.state), 'sha'
    def save(self, state, sha): self.state=copy.deepcopy(state); return 'sha'

class Gateway:
    def __init__(self, store, lost=False): self.store=store; self.calls=0; self.lost=lost
    def overview(self, *args): return {'posts':[], 'ready':True}
    def verify_asset(self,row): pass
    def create_post(self, *args):
        assert self.store.state['attempts'][0]['status']=='reserved'
        self.calls+=1
        if self.lost: raise TimeoutError()
        return {'id':'e'*24}
    def recover(self, attempt): return []
    def post(self, post_id): return {'id':post_id,'channelId':'a'*24,'status':'sending'}

class CoreTests(unittest.TestCase):
    def test_slots_follow_berlin_dst_without_catchup(self):
        c=config()
        self.assertEqual(slot_at(c, NOW), '2026-10-25/12:17')
        self.assertEqual(slot_at(c, dt.datetime(2026,7,1,10,20,tzinfo=UTC)), '2026-07-01/12:17')
        self.assertIsNone(slot_at(c, NOW+dt.timedelta(hours=1)))
    def test_legacy_channel_and_handle_blocked(self):
        for change in ({'channel_id':'6ad16c0c778b240e2f21aca5'}, {'handle':'ufo3103'}):
            with self.assertRaises(ValueError): validate_config(dict(config(), **change), live=True)
    def test_uncommissioned_account_blocked(self):
        with self.assertRaises(ValueError): validate_config(dict(config(), commissioned=False), live=True)
    def test_missing_rights_and_changed_caption_rejected(self):
        c=config(); self.assertTrue(eligible(c,item(),NOW))
        self.assertFalse(eligible(dict(c,rights={}),item(),NOW))
        self.assertFalse(eligible(c,dict(item(),caption='Changed'),NOW))
        self.assertFalse(eligible(c,dict(item(),sha256='f'*64),NOW))
    def test_lost_create_response_never_resends(self):
        store=Store(); gate=Gateway(store,lost=True)
        with self.assertRaises(TimeoutError): run_one(config(),store,gate,NOW)
        self.assertEqual(run_one(config(),store,gate,NOW+dt.timedelta(minutes=20)), 'unresolved')
        self.assertEqual(gate.calls,1)
    def test_persisted_reservation_and_repeated_slot(self):
        store=Store(); gate=Gateway(store)
        self.assertEqual(run_one(config(),store,gate,NOW),'pending')
        self.assertEqual(run_one(config(),store,gate,NOW),'pending')
        self.assertEqual(gate.calls,1)
    def test_duplicate_source_hash_never_sent(self):
        store=Store(); gate=Gateway(store)
        store.state['attempts']=[dict(item(),status='verified_public',slot='old',
            reserved_at='2026-10-24T08:00:00Z')]
        self.assertEqual(run_one(config(),store,gate,NOW),'empty_or_unapproved')
        self.assertEqual(gate.calls,0)
    def test_rolling_budget_and_spacing(self):
        for count, ago, expected in [(4,3,'daily_limit'), (1,1,'spacing')]:
            store=Store(); gate=Gateway(store)
            store.state['attempts']=[dict(status='verified_public',clip_id=str(i),slot='old',
                reserved_at=(NOW-dt.timedelta(hours=ago)).isoformat()) for i in range(count)]
            self.assertEqual(run_one(config(),store,gate,NOW),expected)
            self.assertEqual(gate.calls,0)

    def test_explicit_manual_test_bypasses_spacing_once_and_keeps_budget(self):
        class TestGateway(Gateway):
            def create_post(self,*args):self.calls+=1;return {'id':'e'*24}
        store=Store();gate=TestGateway(store)
        store.state['attempts']=[dict(status='confirmed_sent',clip_id='previous',slot='old',
            reserved_at=(NOW-dt.timedelta(minutes=5)).isoformat())]
        self.assertEqual(run_one(config(),store,gate,NOW),'spacing')
        self.assertEqual(run_one(config(),store,gate,NOW,immediate=True,manual_test_id='123456'),'pending')
        store.state['attempts'][-1]['status']='confirmed_sent'
        self.assertEqual(run_one(config(),store,gate,NOW,immediate=True,manual_test_id='123456'),'slot_complete')
        self.assertEqual(gate.calls,1)
        store.state['attempts'].extend([dict(status='confirmed_sent',slot='other',reserved_at=NOW.isoformat())]*3)
        self.assertEqual(run_one(config(),store,gate,NOW,immediate=True,manual_test_id='654321'),'daily_limit')
        with self.assertRaises(ValueError):run_one(config(),store,gate,NOW,manual_test_id='bad')

    def test_extra_manual_qa_post_does_not_expand_automatic_daily_target(self):
        class TestGateway(Gateway):
            def create_post(self,*args):self.calls+=1;return {'id':'e'*24}
        store=Store();gate=TestGateway(store)
        store.state['attempts']=[dict(status='confirmed_sent',clip_id='old'+str(i),slot='old'+str(i),
            reserved_at=(NOW-dt.timedelta(hours=4)).isoformat()) for i in range(4)]
        self.assertEqual(run_one(config(),store,gate,NOW),'daily_limit')
        self.assertEqual(run_one(config(),store,gate,NOW,immediate=True,manual_test_id='7654321'),'pending')
        self.assertEqual(gate.calls,1)

    def test_account_state_mismatch_stops_before_send(self):
        store=Store(); gate=Gateway(store);store.state['channel_id']='f'*24
        with self.assertRaises(ValueError):run_one(config(),store,gate,NOW)
        self.assertEqual(gate.calls,0)

    def test_cooldown_stops_all_network_requests(self):
        store=Store(); gate=Gateway(store)
        store.state['cooldown_until']='2026-10-26T00:00:00Z'
        self.assertEqual(run_one(config(),store,gate,NOW),'cooldown')
        self.assertEqual(gate.calls,0)

    def test_cas_conflict_prevents_send(self):
        class Conflict(Store):
            def save(self,state,sha):raise ValueError('conflict')
        store=Conflict();gate=Gateway(store)
        with self.assertRaises(ValueError):run_one(config(),store,gate,NOW)
        self.assertEqual(gate.calls,0)

    def test_public_reconciliation_removes_queue_and_keeps_fingerprint(self):
        store=Store();gate=Gateway(store)
        run_one(config(),store,gate,NOW)
        gate.post=lambda post_id:dict(id=post_id,channelId='a'*24,status='sent',
            sentAt='2026-10-25T11:21:00Z',externalLink='https://www.tiktok.com/@cliprauschxl/video/7697189362877992225')
        gate.verify=lambda post:True
        self.assertEqual(run_one(config(),store,gate,NOW+dt.timedelta(minutes=20)),'verified_public')
        self.assertEqual(store.state['queue'],[])
        self.assertEqual(store.state['attempts'][0]['source_sha256'],'c'*64)
        self.assertEqual(gate.calls,1)

if __name__=='__main__': unittest.main()
