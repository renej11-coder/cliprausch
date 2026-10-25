import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts.cliprausch.hosting import approve_and_host
from scripts.cliprausch.core import eligible
from test_core import config,item,NOW

class HostingTests(unittest.TestCase):
    def test_reviewed_artifact_hash_binds_final_caption_and_queue_receipt(self):
        raw=b'reviewed-media';row=item();row['sha256']=hashlib.sha256(raw).hexdigest()
        payload={'reviewed_media_sha256':row['sha256']}
        row['review'].pop('approved_sha256')
        class API:
            def call(self,*args):return {'id':123,'assets':[{'name':'Clip1234-'+row['sha256'][:12]+'.mp4'}]}
        class Store:
            api=API()
            def save(self,state,sha):self.saved=state
        store=Store();state={'queue':[row]}
        old=os.getcwd()
        with tempfile.TemporaryDirectory() as root:
            try:
                os.chdir(root);path=Path('.review-download/Clip1234');path.mkdir(parents=True)
                (path/'final.mp4').write_bytes(raw)
                with patch('scripts.cliprausch.services.Gateway.verify_asset'):
                    approve_and_host(config(),store,state,'oldsha',row,payload,NOW)
                self.assertTrue(eligible(config(),store.saved['queue'][0],NOW))
                self.assertIn('/cliprausch-2026-10/Clip1234-',row['video_url'])
            finally:os.chdir(old)

    def test_unwatched_hash_rejected_before_hosting(self):
        with self.assertRaises(ValueError):approve_and_host(config(),None,{},'sha',item(),{},NOW)
