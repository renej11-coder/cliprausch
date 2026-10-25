"""Public authorized Twitch candidates, isolated rendering, human review queue.

The ranking snapshot is curated from TwitchTracker, never scraped automatically.
This module receives only a short-lived GitHub job token; no Buffer credential.
"""
import base64
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from .core import timestamp, same_clip, seal
from .services import State
from scripts.upload_transport import GitHubAPI

def reconsider_unknown_drafts(state):
    old_asr=('render_rejected','word_timing_or_confidence_requires_correction','uncertain_asr')
    unknown=[r for r in state.get('rejected',[]) if r.get('reason') in old_asr and
        r.get('subtitle_policy_version',0)<2 and not any(same_clip(r,a) for a in state['attempts'])]
    for row in unknown:
        state['rejected'].remove(row)
        state.setdefault('technical_failures',[]).append(dict(row,reason='retest_after_subtitle_policy_change',previous_reason=row['reason']))
    return bool(unknown)

def expire_queue(state,now):
    expired=[r for r in state['queue'] if (now-timestamp(r['source_created_at'])).total_seconds()>71*3600
        and not any(same_clip(r,a) and a['status']!='verified_public' for a in state['attempts'])]
    for row in expired:
        state['queue'].remove(row)
        state.setdefault('rejected',[]).append({**row,'reason':'source_expired','at':now.isoformat()})
    return bool(expired)

def run(args,timeout=90):
    # No service credentials in download/model/FFmpeg children.
    env={k:v for k,v in os.environ.items() if k in ('PATH','HOME','USERPROFILE','TMP','TEMP','SYSTEMROOT',
        'HF_HOME','HF_HUB_DISABLE_IMPLICIT_TOKEN','LD_LIBRARY_PATH','PYTHONPATH')}
    return subprocess.run(args,env=env,check=True,capture_output=True,text=True,timeout=timeout)

def twitch_url(url):
    return isinstance(url,str) and re.fullmatch(r'https://(?:clips\.twitch\.tv/[A-Za-z0-9_-]+|(?:www\.)?twitch\.tv/[A-Za-z0-9_]+/clip/[A-Za-z0-9_-]+)',url)

def discover(c,now):
    if (now.date()-dt.date.fromisoformat(c['ranking_snapshot'])).days>7:
        print('Cliprausch: ranking snapshot is older than seven days; using the last known list, not claiming current ranks')
    results=[]
    for channel in c['sources']:
        rights=c['rights'].get(channel,{})
        if (rights.get('tiktok') is not True or rights.get('edit') is not True or
            not rights.get('evidence') or timestamp(rights['expires_at'])<=now):continue
        try:
            listing=json.loads(run([sys.executable,'-m','yt_dlp','--no-warnings','--flat-playlist',
                '--playlist-end','5','--dump-single-json','--socket-timeout','15','--retries','1',
                f'https://www.twitch.tv/{channel}/clips?filter=clips&range=24hr']).stdout)
            for entry in listing.get('entries',[])[:5]:
                url=entry.get('webpage_url') or entry.get('url')
                if twitch_url(url):results.append((channel,url))
        except Exception:continue
    return list(dict.fromkeys(results))

def inspect(channel,url,now):
    info=json.loads(run([sys.executable,'-m','yt_dlp','--no-warnings','--no-playlist','--skip-download',
        '--dump-single-json','--socket-timeout','15','--retries','1',url]).stdout)
    creators=info.get('creators') or [info.get('creator')]
    if (str(info.get('channel','')).lower()!=channel or
        channel not in [str(x).lower() for x in creators] or
        'twitch' not in str(info.get('extractor_key','')).lower()):raise ValueError('broadcaster_mismatch')
    created=dt.datetime.fromtimestamp(info['timestamp'],dt.timezone.utc)
    if not 0<=(now-created).total_seconds()<=60*3600 or not 15<=info['duration']<=60:
        raise ValueError('source_age_or_duration')
    slug=url.rsplit('/',1)[-1]
    if not re.fullmatch('[A-Za-z0-9_-]{4,100}',slug):raise ValueError('clip_id_invalid')
    category=(info.get('categories') or [''])[0]
    kind='talk' if category=='Just Chatting' else 'irl' if category in ('IRL','Travel & Outdoors') else 'reaction' if category in ('Talk Shows & Podcasts','Special Events') else 'gaming'
    return {'clip_id':slug,'streamer':channel,'source_url':url,'source_created_at':created.isoformat(),
        'category':kind,'original_category':category,'title':str(info.get('title',''))[:100],
        'views':max(0,int(info.get('view_count') or 0))}

def produce(c,now,discover_only=False):
    token=os.environ.pop('GH_TOKEN','')
    api=GitHubAPI(token);store=State(api,c);state,sha=store.load()
    if reconsider_unknown_drafts(state):sha=store.save(state,sha)
    if expire_queue(state,now):sha=store.save(state,sha)
    if len(state['queue'])>=c['daily_target']*2:
        print('Cliprausch: review buffer full');return 0
    if os.environ.get('GITHUB_EVENT_NAME')=='schedule' and not discover_only:
        from .core import slot_at
        production=dict(c,daily_target=5,slots={'5':c['prepare_slots']})
        slot=slot_at(production,now)
        if not slot or state.get('last_prepare_slot')==slot:return 0
        state['last_prepare_slot']=slot;sha=store.save(state,sha)
    candidates=[]
    for channel,url in discover(c,now):
        try:
            row=inspect(channel,url,now)
            if not any(same_clip(row,r) for r in state['queue']+state['attempts']+state.get('rejected',[])):
                candidates.append(row)
        except Exception:continue
    candidates.sort(key=lambda r:-(r['views']/max(1,(now-timestamp(r['source_created_at'])).total_seconds()/3600)))
    if discover_only:
        print(json.dumps({'account':c['handle'],'candidate_count':len(candidates),
            'candidates':candidates[:20]},ensure_ascii=False,indent=2));return 0
    # One review candidate per run; no blind quality replacements beyond three.
    for row in candidates[:3]:
        out=Path('rendered-cliprausch')/row['clip_id'];out.mkdir(parents=True,exist_ok=True)
        stage='download'
        try:
            run([sys.executable,'-m','yt_dlp','--no-warnings','--no-playlist','--max-filesize','128M',
                '--retries','1','--socket-timeout','20','-f','best[height<=1080]',
                '--merge-output-format','mp4','-o',str(out/'source.%(ext)s'),row['source_url']],timeout=180)
            sources=[p for p in out.glob('source.*') if p.suffix in ('.mp4','.mkv','.webm')]
            if len(sources)!=1:raise ValueError('download_missing')
            stage='render'
            # Model imports and decoding live in a child with a sanitized environment.
            run([sys.executable,'-m','scripts.cliprausch.render_cli',str(sources[0]),str(out)],timeout=900)
            qa=json.loads((out/'qa.json').read_text())
            row.update({k:qa[k] for k in ('width','height','duration','sha256','source_sha256')})
            row.update(caption=f'{row.pop("title")} | {row["streamer"]} #twitchde #clips',
                audio_cleared=False,review={},video_url='',rendered_at=now.isoformat())
            # Draft stays in durable state; video stays in a short-lived Actions artifact.
            # Nothing is publicly hosted before explicit final-media review.
            state['queue'].append(row);store.save(state,sha)
            (out/'candidate.json').write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding='utf-8')
            print('Cliprausch: rendered candidate; review required; no post sent');return 0
        except Exception as error:
            diagnostic={'stage':stage,'type':type(error).__name__,'reason':'technical_failure'}
            if (out/'render-error.json').exists():diagnostic.update(json.loads((out/'render-error.json').read_text()))
            (out/'diagnostic.json').write_text(json.dumps(diagnostic,indent=2),encoding='utf-8')
            quality=diagnostic['reason'] in ('uncertain_asr','word_timing_or_confidence_requires_correction','speech_required','duration_outside_15_60')
            bucket='rejected' if quality else 'technical_failures'
            state.setdefault(bucket,[]).append({**row,'diagnostic':diagnostic,'reason':diagnostic['reason'],
                'subtitle_policy_version':2,'at':now.isoformat()})
            sha=store.save(state,sha)
            print('Cliprausch: candidate '+('rejected' if quality else 'technical failure')+' '+json.dumps(diagnostic))
    print('Cliprausch: no renderable candidate');return 0
