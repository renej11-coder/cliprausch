import datetime as dt
import unittest
import json
import os
import sys
from unittest.mock import patch
from types import SimpleNamespace
from scripts.cliprausch.producer import expire_queue,twitch_url,run,discover,reconsider_unknown_drafts
from test_core import item,NOW

class ProducerTests(unittest.TestCase):
    def test_only_explicit_owner_run_can_override_preparation_cooldown(self):
        from scripts.cliprausch.producer import manual_preparation_requested
        env={'GITHUB_REPOSITORY':'renej11-coder/cliprausch','GITHUB_REF':'refs/heads/main',
            'GITHUB_EVENT_NAME':'workflow_dispatch','GITHUB_ACTOR':'renej11-coder','MODE':'prepare'}
        with patch.dict(os.environ,env):self.assertTrue(manual_preparation_requested())
        for key,value in [('GITHUB_ACTOR','github-actions[bot]'),('GITHUB_EVENT_NAME','schedule'),
                          ('GITHUB_REPOSITORY','renejordan/twitch-clips'),('MODE','publish')]:
            with patch.dict(os.environ,dict(env,**{key:value})):self.assertFalse(manual_preparation_requested())

    def test_stale_full_queue_is_archived_and_space_freed(self):
        state={'queue':[dict(item(),clip_id=str(i),source_created_at='2026-10-20T00:00:00Z') for i in range(8)],'attempts':[]}
        self.assertTrue(expire_queue(state,NOW))
        self.assertEqual(state['queue'],[])
        self.assertEqual(len(state['rejected']),8)
        self.assertFalse(expire_queue(state,NOW))

    def test_unresolved_send_is_preserved_even_after_source_expiry(self):
        row=dict(item(),source_created_at='2026-10-20T00:00:00Z')
        state={'queue':[row],'attempts':[dict(row,status='reserved')]}
        self.assertFalse(expire_queue(state,NOW))
        self.assertEqual(len(state['queue']),1)

    def test_discovery_urls_do_not_accept_external_endpoints_or_flags(self):
        self.assertTrue(twitch_url('https://clips.twitch.tv/GoodClip-id'))
        for url in ('https://evil.test/a','--exec=anything','http://clips.twitch.tv/Test',
                    'https://twitch.tv/a/clip/id?redirect=evil'):
            self.assertFalse(twitch_url(url))

    def test_media_subprocess_receives_neither_service_credential(self):
        with patch.dict(os.environ,{'GH_TOKEN':'FAKE-GITHUB','CLIPRAUSCH_BUFFER_API_KEY':'FAKE-BUFFER'}):
            child=run([sys.executable,'-c',"import os,json;print(json.dumps({k:k in os.environ for k in ['GH_TOKEN','CLIPRAUSCH_BUFFER_API_KEY']}))"])
        self.assertEqual(json.loads(child.stdout),{'GH_TOKEN':False,'CLIPRAUSCH_BUFFER_API_KEY':False})

    def test_old_ranking_uses_explicitly_authorized_cached_sources(self):
        c={'ranking_snapshot':'2026-10-01','sources':['streamer'],
            'rights':{'streamer':{'tiktok':True,'edit':True,'evidence':'user-permission','expires_at':'2027-01-01T00:00:00Z'}}}
        with patch('scripts.cliprausch.producer.run',return_value=SimpleNamespace(stdout=json.dumps({'entries':[
            {'url':'https://clips.twitch.tv/GoodClip'}]}))):
            self.assertEqual(discover(c,NOW),[('streamer','https://clips.twitch.tv/GoodClip')])

    def test_unknown_old_render_failures_can_be_retested_without_releasing_posted_ids(self):
        unknown=dict(item(),reason='render_rejected')
        known=dict(item(),clip_id='KnownBad',source_sha256='e'*64,sha256='f'*64,
            streamer='other',reason='unsafe_content')
        state={'rejected':[unknown,known],'attempts':[]}
        self.assertTrue(reconsider_unknown_drafts(state))
        self.assertEqual(state['rejected'],[known])
        self.assertEqual(state['technical_failures'][0]['clip_id'],'Clip1234')
        current={'rejected':[dict(unknown,subtitle_policy_version=2)],'attempts':[]}
        self.assertFalse(reconsider_unknown_drafts(current))
        state={'rejected':[unknown],'attempts':[dict(item(),status='verified_public')]}
        self.assertFalse(reconsider_unknown_drafts(state))
