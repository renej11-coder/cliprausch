import unittest
from unittest.mock import patch
from scripts.cliprausch.ranking import refresh,priorities,clip_score
from test_core import NOW
class RankingTests(unittest.TestCase):
    def config(self):return {'sources':['small','big','offline'],'live_ranking_enabled':True}
    def test_live_viewers_prioritized_and_unknown_sources_excluded(self):
        state={};env={'CLIPRAUSCH_TWITCH_CLIENT_ID':'fake-id','CLIPRAUSCH_TWITCH_CLIENT_SECRET':'fake-secret'}
        rows=[{'user_login':n,'viewer_count':v,'language':'de','type':'live'} for n,v in [('small',100),('big',20000),('unknown',50000)]]
        with patch('scripts.cliprausch.ranking.request_json',side_effect=[{'access_token':'fake-token'},{'data':rows}]):
            self.assertTrue(refresh(self.config(),state,NOW,env))
        self.assertEqual(priorities(self.config(),state),['big','small','offline'])
        self.assertNotIn('fake-secret',str(state));self.assertEqual(env,{})
    def test_api_failure_keeps_last_good_ranking(self):
        state={'live_ranking':{'viewers':{'big':20000},'at':NOW.isoformat()}}
        env={'CLIPRAUSCH_TWITCH_CLIENT_ID':'fake','CLIPRAUSCH_TWITCH_CLIENT_SECRET':'fake'}
        with patch('scripts.cliprausch.ranking.request_json',side_effect=TimeoutError):
            self.assertFalse(refresh(self.config(),state,NOW,env))
        self.assertEqual(priorities(self.config(),state)[0],'big')
    def test_missing_credentials_keeps_snapshot(self):
        self.assertFalse(refresh(self.config(),{},NOW,{}))
        self.assertEqual(priorities(self.config(),{}),self.config()['sources'])
    def test_big_streamer_bonus_does_not_override_clip_popularity_completely(self):
        state={'live_ranking':{'viewers':{'big':20000,'small':100}}}
        a={'streamer':'big','views':100,'source_created_at':NOW.isoformat()}
        b=dict(a,streamer='small')
        self.assertGreater(clip_score(a,state,NOW),clip_score(b,state,NOW))
        self.assertGreater(clip_score(dict(b,views=10000),state,NOW),clip_score(a,state,NOW))
    def test_invalid_response_does_not_replace_cache(self):
        state={'live_ranking':{'viewers':{'big':20}}};old=str(state)
        env={'CLIPRAUSCH_TWITCH_CLIENT_ID':'fake','CLIPRAUSCH_TWITCH_CLIENT_SECRET':'fake'}
        with patch('scripts.cliprausch.ranking.request_json',side_effect=[{'access_token':'fake'},{'data':[{'user_login':'evil/path','viewer_count':20}]}]):
            self.assertFalse(refresh(self.config(),state,NOW,env))
        self.assertEqual(str(state),old)
