"""Account-neutral transport extracted from the working Buffer uploader."""
import base64
import json
import re
from html.parser import HTMLParser
from urllib.error import HTTPError
from urllib.parse import urlencode,urlsplit
from urllib.request import HTTPRedirectHandler,Request,build_opener
BUFFER_URL='https://api.buffer.com'
GITHUB_URL='https://api.github.com/repos/renej11-coder/cliprausch'
CHANNEL_ID='CHANNEL_PLACEHOLDER'
ORGANIZATION_ID='ORG_PLACEHOLDER'
MAX_BYTES=2*1024*1024

POST_FIELDS='id status text channelId sentAt dueAt createdAt externalLink\n  assets { source ... on VideoAsset { video { title } } }'
OVERVIEW='query TikTok14WorkerOverview($since:DateTime!, $until:DateTime!) {\n  channel(input:{id:"CHANNEL_PLACEHOLDER"}) {\n    id name service organizationId externalLink scopes\n    isDisconnected isLocked isQueuePaused timezone\n  }\n  account { organizations { id limits { scheduledPosts } } }\n  dailyPostingLimits(input:{channelIds:["CHANNEL_PLACEHOLDER"]}) {\n    channelId isAtLimit limit scheduled sent\n  }\n  recent:posts(first:100,input:{organizationId:"ORG_PLACEHOLDER",\n    filter:{channelIds:["CHANNEL_PLACEHOLDER"],createdAt:{start:$since},\n            status:[sent,scheduled,sending,error]}}) {\n    edges { node { id status text channelId sentAt dueAt createdAt externalLink\n  assets { source ... on VideoAsset { video { title } } } } } pageInfo { hasNextPage }\n  }\n  due:posts(first:100,input:{organizationId:"ORG_PLACEHOLDER",\n    filter:{channelIds:["CHANNEL_PLACEHOLDER"],dueAt:{start:$since,end:$until},\n            status:[sent,scheduled,sending,error]}}) {\n    edges { node { id status text channelId sentAt dueAt createdAt externalLink\n  assets { source ... on VideoAsset { video { title } } } } } pageInfo { hasNextPage }\n  }\n  pending:posts(first:100,input:{organizationId:"ORG_PLACEHOLDER",\n    filter:{channelIds:["CHANNEL_PLACEHOLDER"],status:[scheduled,sending]}}) {\n    edges { node { id status text channelId sentAt dueAt createdAt externalLink\n  assets { source ... on VideoAsset { video { title } } } } } pageInfo { hasNextPage }\n  }\n}'

class ServiceError(Exception):
    """Only fixed internal reason codes belong in this exception, never bodies."""

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def request_json(url, token=None, method='GET', payload=None):
    parsed = urlsplit(url)
    github = url.startswith(GITHUB_URL + '/')
    buffer = url == BUFFER_URL
    public_tiktok = (parsed.scheme == 'https' and parsed.netloc == 'www.tiktok.com'
                     and parsed.path == '/oembed')
    if not (github or buffer or public_tiktok) or (token and public_tiktok):
        raise ServiceError('unapproved_endpoint')
    headers = {'User-Agent':'TikTok14/1.0', 'Accept':'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    if github:
        headers['X-GitHub-Api-Version'] = '2026-03-10'
    raw = None
    if payload is not None:
        raw = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    request = Request(url, data=raw, headers=headers, method=method)
    try:
        with build_opener(NoRedirect()).open(request, timeout=25) as response:
            if getattr(response,'status',200)==204:
                return {}
            body = response.read(MAX_BYTES+1)
    except HTTPError as error:
        service = 'github' if github else 'buffer' if buffer else 'tiktok'
        raise ServiceError(service + '_http_' + str(error.code)) from None
    except Exception:
        raise ServiceError('transport_error') from None
    if len(body) > MAX_BYTES:
        raise ServiceError('response_too_large')
    try:
        data = json.loads(body)
    except (ValueError, UnicodeError):
        raise ServiceError('invalid_json') from None
    if not isinstance(data, dict):
        raise ServiceError('invalid_response_shape')
    return data

class PublicVideoData(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.active=False
        self.blocks=[]
        self.parts=[]

    def handle_starttag(self,tag,attrs):
        if tag=='script' and dict(attrs).get('id')=='__UNIVERSAL_DATA_FOR_REHYDRATION__':
            self.active=True
            self.parts=[]

    def handle_data(self,data):
        if self.active:self.parts.append(data)

    def handle_endtag(self,tag):
        if tag=='script' and self.active:
            self.blocks.append(''.join(self.parts))
            self.active=False

class GitHubAPI:
    def __init__(self, token):
        if not token:
            raise ServiceError('github_credential_missing')
        self._token = token

    def call(self, method, path, body=None):
        if not path.startswith('/') or path.startswith('//') or '..' in path or '\\' in path:
            raise ServiceError('invalid_github_path')
        return request_json(GITHUB_URL+path, self._token, method, body)
class BufferGateway:
    def __init__(self,key):
        if not key:raise ServiceError('buffer_credential_missing')
        self._key=key
    def post(self,post_id):
        if not re.fullmatch('[a-f0-9]{24}',post_id):raise ServiceError('invalid_post_id')
        data=self.graphql('query Read($id:PostId!){post(input:{id:$id}){'+POST_FIELDS+'}}',{'id':post_id})
        if not isinstance(data.get('post'),dict):raise ServiceError('buffer_post_missing')
        return data['post']
