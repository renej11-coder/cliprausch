"""Reuse TikTok14's Buffer protocol without its account-specific globals."""
import base64
import datetime as dt
import hashlib
import json
import re
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, build_opener

from scripts import upload_transport as legacy
from .core import timestamp, validate_config

class RateLimited(Exception):
    def __init__(self,seconds): self.seconds=max(60,min(2592000,int(seconds)))

def public_evidence(c,video_id,body):
    return (body.get('provider_name')=='TikTok' and body.get('type')=='video' and
        body.get('author_url')=='https://www.tiktok.com/@'+c['handle'] and
        re.search(r'data-video-id=[\"\x27]'+re.escape(video_id)+r'[\"\x27]',str(body.get('html',''))) is not None)

def validate_overview(c,data,for_send=True):
    ch=data['channel']
    expected={'id':c['channel_id'],'organizationId':c['organization_id'],
        'name':c['handle'],'service':'tiktok','timezone':'Europe/Berlin'}
    if any(ch.get(k)!=v for k,v in expected.items()):raise ValueError('channel_identity_mismatch')
    if ch.get('externalLink') not in ('https://tiktok.com/@'+c['handle'],'https://www.tiktok.com/@'+c['handle']):
        raise ValueError('channel_url_mismatch')
    if for_send and any(ch.get(k) is not False for k in ('isDisconnected','isLocked','isQueuePaused')):
        raise ValueError('channel_not_ready')
    if for_send and 'video.publish' not in ch.get('scopes',[]):raise ValueError('publishing_scope_missing')
    limits=data['dailyPostingLimits']
    if len(limits)!=1 or limits[0]['channelId']!=c['channel_id']:raise ValueError('quota_identity_mismatch')
    daily=limits[0]
    if any(type(daily.get(k)) is not int or daily[k]<0 for k in ('limit','sent','scheduled')):
        raise ValueError('quota_invalid')
    if for_send and (daily.get('isAtLimit') is not False or daily['sent']+daily['scheduled']>=daily['limit']):
        raise ValueError('daily_platform_limit')
    posts={}
    for section in ('recent','due','pending'):
        page=data[section]
        if page['pageInfo']['hasNextPage'] is not False:raise ValueError('history_incomplete')
        for edge in page['edges']:
            p=edge['node']
            if p.get('channelId')!=c['channel_id'] or not re.fullmatch('[a-f0-9]{24}',str(p.get('id',''))):
                raise ValueError('post_identity_mismatch')
            if p['id'] in posts and posts[p['id']]!=p:raise ValueError('inconsistent_snapshot')
            posts[p['id']]=p
    return {'ready':True,'posts':list(posts.values())}

class Gateway(legacy.BufferGateway):
    def __init__(self,c,key):
        validate_config(c)
        if not re.fullmatch('[a-f0-9]{24}',c.get('channel_id','')):raise ValueError('channel_required')
        super().__init__(key);self.config=c

    def identity(self):
        query='''query Identity {channel(input:{id:"CHANNEL"}){
          id name service organizationId externalLink scopes
          isDisconnected isLocked isQueuePaused timezone }}'''.replace('CHANNEL',self.config['channel_id'])
        ch=self.graphql(query)['channel']
        if (ch.get('id')!=self.config['channel_id'] or ch.get('name')!=self.config['handle'] or
            ch.get('service')!='tiktok' or not re.fullmatch('[a-f0-9]{24}',str(ch.get('organizationId','')))):
            raise ValueError('channel_identity_mismatch')
        if self.config.get('organization_id') and ch['organizationId']!=self.config['organization_id']:
            raise ValueError('organization_mismatch')
        self.config['organization_id']=ch['organizationId']
        return ch

    def graphql(self,query,variables=None):
        # Same endpoint, JSON and mutation shape as the working uploader.
        # Separate transport preserves Retry-After and never follows bearer redirects.
        request=Request(legacy.BUFFER_URL,data=json.dumps({'query':query,'variables':variables or {}}).encode(),
            headers={'Authorization':'Bearer '+self._key,'Content-Type':'application/json'},method='POST')
        try:
            with build_opener(legacy.NoRedirect()).open(request,timeout=25) as response:
                raw=response.read(legacy.MAX_BYTES+1)
        except HTTPError as error:
            if error.code==429:
                try:seconds=int(error.headers.get('Retry-After','3600'))
                except (ValueError,TypeError):seconds=3600
                raise RateLimited(seconds) from None
            raise legacy.ServiceError('buffer_http_'+str(error.code)) from None
        except Exception:raise legacy.ServiceError('buffer_transport_error') from None
        if len(raw)>legacy.MAX_BYTES:raise ValueError('response_too_large')
        body=json.loads(raw)
        if body.get('errors') or not isinstance(body.get('data'),dict):raise ValueError('buffer_graphql_error')
        return body['data']

    def overview(self,since,until,for_send=True):
        query=legacy.OVERVIEW.replace(legacy.CHANNEL_ID,self.config['channel_id']).replace(
            legacy.ORGANIZATION_ID,self.config['organization_id'])
        data=self.graphql(query,{'since':since.isoformat(),'until':until.isoformat()})
        return validate_overview(self.config,data,for_send)

    def create_post(self,video_url,caption,asset_title):
        validate_config(self.config,live=True)
        data=self.graphql('''mutation Send($input:CreatePostInput!) {
          createPost(input:$input) { __typename ... on PostActionSuccess {
            post { id status externalLink sentAt }
          } }
        }''',{'input':{'channelId':self.config['channel_id'],'text':caption,
            'mode':'shareNow','schedulingType':'automatic','saveToDraft':False,
            'metadata':{'tiktok':{'isAiGenerated':False}},
            'assets':[{'video':{'url':video_url,'metadata':{'title':asset_title,'thumbnailOffset':0}}}]}})
        result=data.get('createPost',{})
        if result.get('__typename')!='PostActionSuccess':raise ValueError('create_unresolved')
        post=result.get('post',{})
        if not re.fullmatch('[a-f0-9]{24}',str(post.get('id',''))):raise ValueError('create_unresolved')
        return post

    def recover(self,attempt):
        reserved=timestamp(attempt['reserved_at'])
        data=self.overview(reserved-dt.timedelta(minutes=5),dt.datetime.now(dt.timezone.utc)+dt.timedelta(days=1),for_send=False)
        return [p for p in data['posts'] if -5<=(timestamp(p['createdAt'])-reserved).total_seconds()<=600 and
            any(a.get('video',{}).get('title')==attempt['asset_title'] for a in p.get('assets',[]))]

    def verify(self,post):
        url=post.get('externalLink','')
        match=re.fullmatch(r'https://(?:www\.)?tiktok\.com/@'+re.escape(self.config['handle'])+r'/video/([0-9]{10,30})',url)
        if not match:return False
        try:
            body=legacy.request_json('https://www.tiktok.com/oembed?'+urlencode({'url':url}))
            if public_evidence(self.config,match[1],body):return True
        except legacy.ServiceError:pass
        # Parameterized version of the existing exact public-page verification.
        try:
            req=Request(url,headers={'User-Agent':'Cliprausch/1.0'})
            with build_opener(legacy.NoRedirect()).open(req,timeout=25) as response:
                raw=response.read(legacy.MAX_BYTES+1)
            if len(raw)>legacy.MAX_BYTES:return False
            parser=legacy.PublicVideoData();parser.feed(raw.decode())
            if len(parser.blocks)!=1:return False
            detail=json.loads(parser.blocks[0])['__DEFAULT_SCOPE__']['webapp.video-detail']
            item=detail['itemInfo']['itemStruct'];author=item['author'];video=item['video']
            return (type(detail['statusCode']) is int and detail['statusCode']==0 and
                item['id']==match[1] and video['id']==match[1] and type(video['duration']) is int and video['duration']>0 and
                author['uniqueId']==self.config['handle'] and all(x is False for x in
                (item.get('privateItem'),item.get('secret'),author.get('privateAccount'),author.get('secret'))))
        except Exception:return False

    def verify_asset(self,row):
        # Only reviewed files on this repository's dedicated release prefix.
        if not re.fullmatch(r'https://github.com/renej11-coder/cliprausch/releases/download/cliprausch-\d{4}-\d{2}/[A-Za-z0-9_-]+\.mp4',row['video_url']):
            raise ValueError('asset_url_invalid')
        # GitHub assets redirect to signed CDN URLs. No credential accompanies this request.
        digest=hashlib.sha256();total=0
        with __import__('urllib.request',fromlist=['urlopen']).urlopen(row['video_url'],timeout=30) as response:
            while chunk:=response.read(1024*1024):
                total+=len(chunk)
                if total>128*1024*1024:raise ValueError('media_too_large')
                digest.update(chunk)
        if digest.hexdigest()!=row['sha256']:raise ValueError('hosted_media_hash_mismatch')

class State:
    def __init__(self,github,c):self.api,self.config=github,c
    def validate(self,data):
        if (data.get('version')!=1 or data.get('account')!=self.config['handle'] or
            data.get('channel_id')!=self.config['channel_id'] or
            any(not isinstance(data.get(k),list) for k in ('queue','attempts'))):
            raise ValueError('state_identity_or_schema_invalid')
        return data
    def load(self):
        raw=self.api.call('GET','/contents/state.json?ref=cliprausch-state')
        if raw['encoding']!='base64':raise ValueError('state_encoding_invalid')
        return self.validate(json.loads(base64.b64decode(raw['content']))),raw['sha']
    def save(self,data,sha):
        self.validate(data)
        if not sha:raise ValueError('state_version_required')
        encoded=base64.b64encode(json.dumps(data,ensure_ascii=False,indent=2).encode()).decode()
        if len(encoded)>900000:raise ValueError('state_compaction_required')
        result=self.api.call('PUT','/contents/state.json',{'branch':'cliprausch-state',
            'message':'Cliprausch: persist separate state','sha':sha,'content':encoded})
        return result['content']['sha']
