"""Offline policy and once-only sending. All state writes precede network sends."""
import datetime as dt
import hashlib
import json
import re
from zoneinfo import ZoneInfo

UTC=dt.timezone.utc
BERLIN=ZoneInfo('Europe/Berlin')
OLD_CHANNEL='6ad16c0c778b240e2f21aca5'

def timestamp(value):
    value=dt.datetime.fromisoformat(value.replace('Z','+00:00'))
    if value.tzinfo is None: raise ValueError('timezone_required')
    return value.astimezone(UTC)

def validate_config(c, live=False):
    if (c['handle'].lower()=='ufo3103' or not re.fullmatch(r'[a-z0-9_.]{3,24}',c['handle'])
        or c.get('channel_id')==OLD_CHANNEL or c.get('state_branch')!='cliprausch-state'):
        raise ValueError('independent_identity_required')
    if type(c['daily_target']) is not int or c['daily_target'] not in (3,4,5):
        raise ValueError('daily_target_3_to_5')
    for n in (3,4,5):
        slots=c['slots'][str(n)]
        if len(slots)!=n or slots!=sorted(set(slots)): raise ValueError('invalid_slots')
        for s in slots: dt.time.fromisoformat(s)
    if not 10<=c['slot_grace_minutes']<=60 or not 120<=c['min_spacing_minutes']<=240:
        raise ValueError('invalid_timing')
    if len(c['sources'])!=50 or len(set(c['sources']))!=50 or any(
        not re.fullmatch('[a-z0-9_]{3,25}',name) for name in c['sources']):
        raise ValueError('invalid_ranking_snapshot')
    if live and (c.get('commissioned') is not True or any(
        not re.fullmatch('[a-f0-9]{24}',c.get(key,'')) for key in ('channel_id','organization_id'))):
        raise ValueError('new_account_not_commissioned')
    return c

def slot_at(c, now):
    if now.tzinfo is None: raise ValueError('timezone_required')
    local=now.astimezone(BERLIN)
    for clock in c['slots'][str(c['daily_target'])]:
        slot=dt.datetime.combine(local.date(),dt.time.fromisoformat(clock),BERLIN)
        if 0<=(local-slot).total_seconds()<c['slot_grace_minutes']*60:
            return local.date().isoformat()+'/'+clock
    return None

def seal(row):
    # Bind every content field including caption, timing, URL, and both hashes.
    content={k:v for k,v in row.items() if k!='review'}
    return hashlib.sha256(json.dumps(content,sort_keys=True,ensure_ascii=False,
        separators=(',',':')).encode()).hexdigest()

def eligible(c,row,now):
    try:
        rights=c['rights'][row['streamer']]
        if not (isinstance(rights['evidence'],str) and len(rights['evidence'])>=8 and
            all(rights.get(k) is True for k in ('tiktok','edit')) and
            timestamp(rights['expires_at'])>now): return False
        review=row['review']
        automatic=(review.get('kind')=='automatic_render_v1' and review.get('media_sha256')==row.get('sha256') and
            review.get('source_sha256')==row.get('source_sha256') and review.get('full_decode') is True and
            review.get('subtitles_valid') is True and review.get('rights_basis')==rights['evidence'])
        if not (automatic or (review.get('by') and all(review.get(k) is True for k in
            ('watched_full','subtitles_checked','audio_checked','frame_checked','rights_checked','content_checked')) and
            review.get('approved_sha256')==seal(row))): return False
        if review.get('approved_sha256')!=seal(row):return False
        if not all(re.fullmatch('[a-f0-9]{64}',row[k]) for k in ('sha256','source_sha256')):return False
        if not re.fullmatch('[A-Za-z0-9_-]{4,100}',row['clip_id']):return False
        if not re.fullmatch(r'https://github.com/renej11-coder/cliprausch/releases/download/cliprausch-\d{4}-\d{2}/[A-Za-z0-9_-]+\.mp4',row['video_url']):return False
        return (0<=(now-timestamp(row['source_created_at'])).total_seconds()<=71*3600 and
            type(row['duration']) in (int,float) and 15<=row['duration']<=60 and
            row['width']==1080 and row['height']==1920 and
            row.get('category') in c['content_categories'] and
            row.get('audio_cleared') is True and isinstance(row['caption'],str) and
            1<=len(row['caption'])<=2200)
    except (KeyError,ValueError,TypeError): return False

def same_clip(a,b):
    return any(a.get(k) and a.get(k)==b.get(k) for k in
        ('clip_id','sha256','source_sha256')) or (a.get('streamer')==b.get('streamer') and
        a.get('source_created_at') and b.get('source_created_at') and
        abs((timestamp(a['source_created_at'])-timestamp(b['source_created_at'])).total_seconds())<=120)

def run_one(c,store,gateway,now,immediate=False,commissioning_test=False):
    validate_config(c,live=True)
    state,sha=store.load()
    if state.get('account')!=c['handle'] or state.get('version')!=1 or not all(
        isinstance(state.get(k),list) for k in ('queue','attempts')):raise ValueError('invalid_state')
    if state.get('channel_id')!=c['channel_id']:raise ValueError('state_channel_mismatch')
    if state.get('cooldown_until') and now<timestamp(state['cooldown_until']):return 'cooldown'
    unresolved=[a for a in state['attempts'] if a['status']!='verified_public']
    if unresolved:
        if len(unresolved)!=1:raise ValueError('multiple_unresolved')
        attempt=unresolved[0]
        if attempt.get('last_checked_at') and not immediate:
            age=(now-timestamp(attempt['reserved_at'])).total_seconds()
            interval=1200 if age<3600 else 3600
            if (now-timestamp(attempt['last_checked_at'])).total_seconds()<interval:return 'reconcile_wait'
        attempt['last_checked_at']=now.isoformat();sha=store.save(state,sha)
        if not attempt.get('buffer_post_id'):
            found=gateway.recover(attempt)
            if len(found)!=1:return 'unresolved'
            attempt['buffer_post_id']=found[0]['id']; sha=store.save(state,sha)
        post=gateway.post(attempt['buffer_post_id'])
        if post.get('channelId')!=c['channel_id'] or post.get('id')!=attempt['buffer_post_id']:
            raise ValueError('post_account_mismatch')
        if post.get('status') in ('sending','scheduled'):return 'pending'
        if post.get('status')!='sent':return 'unresolved'
        if not gateway.verify(post):return 'unverified'
        sent=timestamp(post['sentAt'])
        if not timestamp(attempt['reserved_at'])<=sent<=now+dt.timedelta(minutes=5):
            raise ValueError('invalid_sent_time')
        if sent>timestamp(attempt['source_created_at'])+dt.timedelta(hours=72):
            raise ValueError('late_publication_requires_review')
        attempt.update(status='verified_public',sent_at=post['sentAt'],tiktok_url=post['externalLink'])
        state['queue']=[r for r in state['queue'] if not same_clip(r,attempt)]
        store.save(state,sha);return 'verified_public'
    slot=slot_at(c,now)
    if immediate and slot is None:slot=now.astimezone(BERLIN).date().isoformat()+'/manual'
    if slot is None:return 'outside_slot'
    if any(a['slot']==slot for a in state['attempts']):return 'slot_complete'
    test_exception=commissioning_test and len(state['attempts'])==1 and state['attempts'][0]['status']=='verified_public'
    moments=[max(timestamp(a['reserved_at']),timestamp(a.get('sent_at',a['reserved_at']))) for a in state['attempts']]
    if any(t>now for t in moments):raise ValueError('future_attempt')
    if sum((now-t).total_seconds()<86400 or t.astimezone(BERLIN).date()==now.astimezone(BERLIN).date()
           for t in moments)>=c['daily_target']:return 'daily_limit'
    if moments and (now-max(moments)).total_seconds()<c['min_spacing_minutes']*60 and not test_exception:return 'spacing'
    candidates=[r for r in state['queue'] if eligible(c,r,now) and
        not any(same_clip(r,a) for a in state['attempts'])]
    if not candidates:return 'empty_or_unapproved'
    # Prefer another broadcaster, preserving editorial queue priority otherwise.
    last=state['attempts'][-1].get('streamer') if state['attempts'] else None
    candidates.sort(key=lambda r:r['streamer']==last)
    row=candidates[0]
    snapshot=gateway.overview(now-dt.timedelta(days=1),now+dt.timedelta(days=1))
    if snapshot.get('ready') is not True:raise ValueError('channel_not_ready')
    if any(p['status']!='sent' for p in snapshot['posts']):raise ValueError('other_post_unresolved')
    title='cliprausch-'+row['clip_id']+'-'+row['sha256'][:12]+'.mp4'
    if any(title==asset.get('video',{}).get('title') for p in snapshot['posts']
           for asset in p.get('assets',[])):raise ValueError('duplicate_remote_asset')
    remote=[timestamp(p['sentAt']) for p in snapshot['posts']]
    # Conservative: manual/foreign posts also consume capacity; double counting is safe.
    known={a.get('tiktok_url') for a in state['attempts']}
    foreign=[timestamp(p['sentAt']) for p in snapshot['posts'] if p.get('externalLink') not in known]
    if len([t for t in foreign if (now-t).total_seconds()<86400])+len([t for t in moments if (now-t).total_seconds()<86400])>=c['daily_target']:
        return 'daily_limit'
    if remote and (now-max(remote)).total_seconds()<c['min_spacing_minutes']*60 and not test_exception:return 'spacing'
    gateway.verify_asset(row)
    attempt={**row,'status':'reserved','slot':slot,'reserved_at':now.isoformat(),'asset_title':title}
    state['attempts'].append(attempt);sha=store.save(state,sha)
    # All errors keep reservation. Never retry create, including 429 or lost responses.
    result=gateway.create_post(row['video_url'],row['caption'],title)
    attempt.update(status='pending',buffer_post_id=result['id'])
    store.save(state,sha);return 'pending'
