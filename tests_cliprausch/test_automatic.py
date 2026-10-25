import unittest
from scripts.cliprausch.automatic import receipt
from scripts.cliprausch.core import eligible,seal,run_one
from test_core import config,item,NOW,Store,Gateway
class AutomaticTests(unittest.TestCase):
    def test_automatic_has_no_fake_human_review(self):
        row=item();q=dict(row,video_codec='h264',audio_codec='aac',full_decode=True,headline=False,subtitle_mode='word_highlight',uncertain_segments=[],uncertain_word_indexes=[])
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
