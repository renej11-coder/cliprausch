import unittest
from scripts.cliprausch.automatic import receipt,select_artifact
from scripts.cliprausch.core import eligible,seal,run_one
from test_core import config,item,NOW,Store,Gateway
class AutomaticTests(unittest.TestCase):
    def test_automatic_has_no_fake_human_review(self):
        row=item();q=dict(row,video_codec='h264',audio_codec='aac',full_decode=True,headline=False,subtitle_mode='word_highlight',uncertain_segments=[],uncertain_word_indexes=[])
        q.update(added_caption_tracks=1,subtitle_scan={'policy_version':3,'method':'tesseract_deu_eng_v1',
            'complete':True,'source_sha256':row['source_sha256'],'decision':'word_highlight','detected':False,
            'frames_scanned':30,'planned_frames':30,'added_caption_tracks':1})
        row['review']=receipt(config(),row,q,[{'start':0,'end':1,'text':'Hallo','probability':.95}])
        row['review']['approved_sha256']=seal(row)
        self.assertTrue(eligible(config(),row,NOW));self.assertNotIn('watched_full',row['review'])
        row['caption']='changed';self.assertFalse(eligible(config(),row,NOW))
    def test_failed_or_uncertain_render_rejected(self):
        row=item()
        for qa in ({},dict(row,video_codec='h264',audio_codec='aac',full_decode=False)):
            with self.assertRaises(ValueError):receipt(config(),row,qa,[])
    def test_immediate_respects_budget_and_persists_before_send(self):
        store=Store();gateway=Gateway(store)
        self.assertEqual(run_one(config(),store,gateway,NOW,immediate=True),'pending')
        self.assertEqual(len(store.state['attempts']),1)
        self.assertEqual(run_one(config(),store,gateway,NOW,immediate=True),'pending')
        self.assertEqual(len(store.state['attempts']),1)

    def test_missing_artifact_does_not_block_next_candidate(self):
        first=item();first.update(review={},artifact_run_id='111')
        second=dict(first,clip_id='Other1234',artifact_run_id='222')
        class API:
            def call(self,method,path):
                return {'artifacts':[] if '/111/' in path else [{'name':'cliprausch-review-222','expired':False}]}
        self.assertIs(select_artifact(config(),{'queue':[first,second]},API(),NOW),second)
    def test_expired_artifact_is_skipped(self):
        row=item();row.update(review={},artifact_run_id='111')
        class API:
            def call(self,*args):return {'artifacts':[{'name':'cliprausch-review-111','expired':True}]}
        self.assertIsNone(select_artifact(config(),{'queue':[row]},API(),NOW))

    def test_second_upload_exception_is_limited_to_commissioning(self):
        import datetime as dt
        old=dict(item(),clip_id='First1234',streamer='other',sha256='f'*64,source_sha256='e'*64,
            status='verified_public',slot='old-slot',reserved_at=(NOW-dt.timedelta(minutes=10)).isoformat())
        store=Store();store.state['attempts']=[old]
        class TestGateway(Gateway):
            def create_post(self,*args):
                assert self.store.state['attempts'][-1]['status']=='reserved'
                self.calls+=1;return {'id':'e'*24}
        gate=TestGateway(store)
        self.assertEqual(run_one(config(),store,gate,NOW,immediate=True),'spacing')
        self.assertEqual(run_one(config(),store,gate,NOW,immediate=True,commissioning_test=True),'pending')
        self.assertEqual(gate.calls,1)
        store.state['attempts'][-1]['status']='verified_public'
        self.assertEqual(run_one(config(),store,gate,NOW+dt.timedelta(minutes=1),immediate=True,commissioning_test=True),'spacing')
        self.assertEqual(gate.calls,1)

    def test_buffer_confirmed_correct_channel_and_url_settle_without_false_public_claim(self):
        import datetime as dt
        store=Store();gate=Gateway(store)
        run_one(config(),store,gate,NOW,immediate=True)
        gate.post=lambda post_id:{'id':post_id,'channelId':'a'*24,'status':'sent','sentAt':(NOW+dt.timedelta(seconds=30)).isoformat(),'externalLink':'https://www.tiktok.com/@cliprauschxl/video/1234567890123456789'}
        gate.verify=lambda post:False
        self.assertEqual(run_one(config(),store,gate,NOW+dt.timedelta(minutes=1),immediate=True),'confirmed_sent')
        self.assertFalse(store.state['attempts'][0]['public_verified'])
        self.assertEqual(store.state['queue'],[])
    def test_wrong_profile_link_remains_unsettled(self):
        import datetime as dt
        store=Store();gate=Gateway(store);run_one(config(),store,gate,NOW,immediate=True)
        gate.post=lambda post_id:{'id':post_id,'channelId':'a'*24,'status':'sent','sentAt':NOW.isoformat(),'externalLink':'https://www.tiktok.com/@other/video/1234567890123456789'}
        self.assertEqual(run_one(config(),store,gate,NOW+dt.timedelta(minutes=1),immediate=True),'unverified')
        self.assertEqual(store.state['attempts'][0]['status'],'pending')

    def test_second_commissioning_upload_uses_its_own_slot(self):
        import datetime as dt
        from scripts.cliprausch.core import slot_at
        store=Store();old=dict(item(),clip_id='First1234',streamer='other',sha256='f'*64,source_sha256='e'*64,
            status='confirmed_sent',slot=slot_at(config(),NOW),reserved_at=(NOW-dt.timedelta(minutes=10)).isoformat())
        store.state['attempts']=[old]
        class TestGateway(Gateway):
            def create_post(self,*args):return {'id':'e'*24}
        self.assertEqual(run_one(config(),store,TestGateway(store),NOW,immediate=True,commissioning_test=True),'pending')
        self.assertTrue(store.state['attempts'][-1]['slot'].endswith('/commissioning-second'))
