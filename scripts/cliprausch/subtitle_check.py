"""Regression-render an already posted artifact; never creates a TikTok post."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys
from .media import render
from .producer import run,twitch_url
from .core import timestamp

def check(c,store,now):
    state,sha=store.load()
    files=list(Path('.review-download').rglob('candidate.json'))
    if len(files)!=1:raise ValueError('regression_artifact_ambiguous')
    artifact=files[0].parent;row=json.loads(files[0].read_text())
    attempt=next(a for a in state['attempts'] if a['clip_id']==row['clip_id'] and a['sha256']==row['sha256'])
    if hashlib.sha256((artifact/'final.mp4').read_bytes()).hexdigest()!=attempt['sha256']:
        raise ValueError('regression_artifact_hash_mismatch')
    if not twitch_url(row['source_url']):raise ValueError('source_url_invalid')
    out=Path('rendered-cliprausch')/row['clip_id'];out.mkdir(parents=True,exist_ok=True)
    run([sys.executable,'-m','yt_dlp','--no-warnings','--no-playlist','--max-filesize','128M',
        '--retries','1','--socket-timeout','20','-f','best[height<=1080]','--merge-output-format','mp4',
        '-o',str(out/'source.%(ext)s'),row['source_url']],timeout=180)
    sources=[p for p in out.glob('source.*') if p.suffix in ('.mp4','.mkv','.webm')]
    if len(sources)!=1 or hashlib.sha256(sources[0].read_bytes()).hexdigest()!=attempt['source_sha256']:
        raise ValueError('regression_source_hash_mismatch')
    qa=render(sources[0],out,words=json.loads((artifact/'transcript.json').read_text()))
    if qa['subtitle_mode']!='source_preserved' or qa['added_caption_tracks']!=0:
        raise ValueError('regression_existing_subtitle_not_detected')
    report={'clip_id':row['clip_id'],'at':now.isoformat(),'subtitle_mode':qa['subtitle_mode'],
        'added_caption_tracks':qa['added_caption_tracks'],'source_sha256':qa['source_sha256'],
        'final_sha256':qa['sha256'],'full_decode':qa['full_decode'],'subtitle_scan':qa['subtitle_scan']}
    state.setdefault('subtitle_checks',[]).append(report)
    state['subtitle_checks']=state['subtitle_checks'][-5:]
    store.save(state,sha)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    print('Cliprausch: existing captions preserved; zero added tracks; no TikTok post created')
