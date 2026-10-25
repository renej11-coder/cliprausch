import base64
import copy
import json
import unittest
from unittest.mock import patch
from scripts.cliprausch.services import Gateway, State, validate_overview, public_evidence
from test_core import config, item

def snapshot():
    return {'channel':dict(id='a'*24,organizationId='b'*24,name='cliprauschxl',
        externalLink='https://tiktok.com/@cliprauschxl',service='tiktok',timezone='Europe/Berlin',
        scopes=['video.publish'],isDisconnected=False,isLocked=False,isQueuePaused=False),
        'dailyPostingLimits':[dict(channelId='a'*24,isAtLimit=False,limit=10,sent=0,scheduled=0)],
        **{k:{'pageInfo':{'hasNextPage':False},'edges':[]} for k in ('recent','due','pending')}}

class ServicesTests(unittest.TestCase):
    def test_overview_blocks_wrong_account_disconnection_and_partial_history(self):
        self.assertTrue(validate_overview(config(),snapshot())['ready'])
        for target,key,value in [('channel','id','6ad16c0c778b240e2f21aca5'),
                ('channel','name','ufo3103'),('channel','isDisconnected',True)]:
            s=snapshot();s[target][key]=value
            with self.assertRaises(ValueError):validate_overview(config(),s)
        s=snapshot();s['recent']['pageInfo']['hasNextPage']=True
        with self.assertRaises(ValueError):validate_overview(config(),s)

    def test_buffer_send_uses_only_new_channel(self):
        g=Gateway(config(),'fake')
        with patch.object(g,'graphql',return_value={'createPost':{'__typename':'PostActionSuccess',
                'post':{'id':'c'*24}}}) as call:
            g.create_post(item()['video_url'],'caption','asset')
        self.assertEqual(call.call_args.args[1]['input']['channelId'],'a'*24)
        self.assertEqual(call.call_args.args[1]['input']['mode'],'shareNow')

    def test_public_evidence_binds_author_and_video(self):
        vid='7697189362877992225'
        body={'provider_name':'TikTok','type':'video','author_url':'https://www.tiktok.com/@cliprauschxl',
            'html':'<blockquote data-video-id="'+vid+'">'}
        self.assertTrue(public_evidence(config(),vid,body))
        self.assertFalse(public_evidence(config(),vid,dict(body,author_url='https://www.tiktok.com/@ufo3103')))

    def test_state_write_keeps_version_and_separate_branch(self):
        class API:
            def call(self,method,path,body=None):
                self.method,self.path,self.body=method,path,body
                return {'content':{'sha':'next'}}
        api=API();store=State(api,config())
        state={'version':1,'account':'cliprauschxl','channel_id':'a'*24,'queue':[],'attempts':[]}
        self.assertEqual(store.save(state,'previous'),'next')
        self.assertEqual(api.body['sha'],'previous')
        self.assertEqual(api.body['branch'],'cliprausch-state')
        with self.assertRaises(ValueError):store.save(state,'')

    def test_missing_state_does_not_initialize(self):
        class API:
            def call(self,*args):raise ValueError('missing')
        with self.assertRaises(ValueError):State(API(),config()).load()

    def test_recovery_can_read_full_quota_but_new_sends_cannot(self):
        s=snapshot();s['dailyPostingLimits'][0].update(isAtLimit=True,sent=10)
        with self.assertRaises(ValueError):validate_overview(config(),s)
        self.assertTrue(validate_overview(config(),s,for_send=False)['ready'])

if __name__=='__main__':unittest.main()
