"""Official Twitch live viewers, cached separately from the upload protocol."""
import json
import math
import os
import re
from urllib.parse import urlencode
from urllib.request import Request,build_opener
from scripts.upload_transport import NoRedirect
from .core import timestamp

def request_json(url,data=None,headers=None):
    if url not in ('https://id.twitch.tv/oauth2/token','https://api.twitch.tv/helix/streams?first=100&language=de&type=live'):
        raise ValueError('ranking_endpoint_invalid')
    req=Request(url,data=data,headers=headers or {})
    with build_opener(NoRedirect()).open(req,timeout=20) as response:raw=response.read(1024*1024+1)
    if len(raw)>1024*1024:raise ValueError('ranking_response_too_large')
    return json.loads(raw)

def refresh(c,state,now,env=None):
    env=os.environ if env is None else env
    client=env.pop('CLIPRAUSCH_TWITCH_CLIENT_ID','');secret=env.pop('CLIPRAUSCH_TWITCH_CLIENT_SECRET','')
    if not c.get('live_ranking_enabled',True) or not client or not secret:
        print('Cliprausch ranking: credentials missing or disabled; keeping cached sources');return False
    try:
        auth=request_json('https://id.twitch.tv/oauth2/token',urlencode({'client_id':client,'client_secret':secret,'grant_type':'client_credentials'}).encode(),{'Content-Type':'application/x-www-form-urlencoded'})
        token=auth['access_token']
        if not isinstance(token,str) or not token:raise ValueError('token_invalid')
        data=request_json('https://api.twitch.tv/helix/streams?first=100&language=de&type=live',headers={'Client-Id':client,'Authorization':'Bearer '+token})
        rows=data['data']
        if not isinstance(rows,list) or len(rows)>100:raise ValueError('ranking_invalid')
        viewers={}
        for row in rows:
            name=row['user_login'];count=row['viewer_count']
            if not re.fullmatch('[a-z0-9_]{3,25}',name) or type(count) is not int or count<0 or row['language']!='de' or row['type']!='live':
                raise ValueError('ranking_invalid')
            if name in c['sources']:viewers[name]=max(viewers.get(name,0),count)
        # Only existing permission-listed sources enter production. New live names do not inherit rights.
        state['live_ranking']={'at':now.isoformat(),'provider':'twitch_helix','viewers':viewers,'streams_observed':len(rows)}
        print('Cliprausch ranking: live viewers refreshed; '+str(len(viewers))+' authorized sources live');return True
    except Exception:
        # Never emit an exception body, request or credentials. A failed refresh cannot erase good state.
        print('Cliprausch ranking: API unavailable; retaining last successful ranking');return False

def priorities(c,state):
    viewers=state.get('live_ranking',{}).get('viewers',{})
    return sorted(c['sources'],key=lambda name:-viewers.get(name,0))

def clip_score(row,state,now):
    velocity=row['views']/max(1,(now-timestamp(row['source_created_at'])).total_seconds()/3600)
    viewers=state.get('live_ranking',{}).get('viewers',{}).get(row['streamer'],0)
    # Up to 3x preference for big live channels; strong clips can still beat weak ones.
    return velocity*(1+min(2,math.log1p(viewers)/5))
