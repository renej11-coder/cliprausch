import datetime as dt
import unittest
from scripts.cliprausch.producer import expire_queue,twitch_url
from test_core import item,NOW

class ProducerTests(unittest.TestCase):
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
