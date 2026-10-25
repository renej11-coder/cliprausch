"""Explicit approval: bind watched media hash, host immutable bytes, save receipt."""
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlencode
from urllib.request import Request,build_opener
from scripts.upload_transport import NoRedirect,ServiceError
from .core import eligible,seal

def approve_and_host(c,store,state,sha,row,payload,now):
    if not re.fullmatch('[A-Za-z0-9_-]{4,100}',row['clip_id']):raise ValueError('clip_id_invalid')
    if payload.get('reviewed_media_sha256')!=row['sha256']:raise ValueError('reviewed_media_hash_required')
    files=list(Path('.review-download').rglob('final.mp4'))
    files=[p for p in files if p.parent.name==row['clip_id']]
    if len(files)!=1:raise ValueError('review_artifact_missing_or_ambiguous')
    raw=files[0].read_bytes()
    if len(raw)>128*1024*1024 or hashlib.sha256(raw).hexdigest()!=row['sha256']:
        raise ValueError('review_artifact_hash_mismatch')
    tag=f'cliprausch-{now:%Y-%m}'
    name=row['clip_id']+'-'+row['sha256'][:12]+'.mp4'
    row['video_url']='https://github.com/renej11-coder/cliprausch/releases/download/'+tag+'/'+name
    row['review']['approved_sha256']=seal(row)
    if not eligible(c,row,now):raise ValueError('review_not_valid_or_expired')
    api=store.api
    try:release=api.call('GET','/releases/tags/'+tag)
    except ServiceError as error:
        if str(error)!='github_http_404':raise
        release=api.call('POST','/releases',{'tag_name':tag,'target_commitish':'main',
            'name':'Cliprausch reviewed media '+now.strftime('%Y-%m'),'draft':False,'prerelease':False})
    if type(release.get('id')) is not int:raise ValueError('release_identity_invalid')
    if any(a.get('name')==name for a in release.get('assets',[])):
        # A lost approval response is resolved by hashing existing immutable bytes.
        from .services import Gateway
        g=object.__new__(Gateway);g.config=c;g.verify_asset(row)
    else:
        url='https://uploads.github.com/repos/renej11-coder/cliprausch/releases/'+str(release['id'])+'/assets?'+urlencode({'name':name})
        request=Request(url,data=raw,method='POST',headers={'Authorization':'Bearer '+api._token,
            'Content-Type':'video/mp4','Accept':'application/vnd.github+json'})
        with build_opener(NoRedirect()).open(request,timeout=120) as response:
            result=json.loads(response.read(2*1024*1024))
        if result.get('name')!=name or result.get('browser_download_url')!=row['video_url']:
            raise ValueError('asset_upload_unconfirmed')
    store.save(state,sha)
