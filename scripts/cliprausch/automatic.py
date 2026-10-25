"""Automatic technical QA and immutable hosting; never claims a human watched."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
from .core import eligible,timestamp
from .media import validate_words

def receipt(c,row,qa,words):
    if not (qa.get('full_decode') is True and qa.get('headline') is False and
        qa.get('subtitle_mode')=='word_highlight' and qa.get('video_codec')=='h264' and qa.get('audio_codec')=='aac' and
        all(qa.get(k)==row.get(k) for k in ('sha256','source_sha256','width','height','duration'))):
        raise ValueError('automatic_render_evidence_invalid')
    validate_words([{k:v for k,v in w.items() if k!='probability'} for w in words],row['duration'])
    if qa.get('uncertain_segments') or len(qa.get('uncertain_word_indexes',[]))/len(words)>.25:
        raise ValueError('automatic_subtitle_confidence_low')
    return {'kind':'automatic_render_v1','media_sha256':row['sha256'],'source_sha256':row['source_sha256'],
        'full_decode':True,'subtitles_valid':True,'rights_basis':c['rights'][row['streamer']]['evidence'],
        'note':'Technical checks only; rights rely on the account owner declaration; ASR can contain mistakes.'}

def main():
    import argparse
    from .cli import settings,store
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['plan','host']);args=parser.parse_args()
    c=settings();s=store(c);state,sha=s.load();now=dt.datetime.now(dt.timezone.utc)
    from .producer import expire_queue
    if expire_queue(state,now):sha=s.save(state,sha)
    if args.mode=='plan':
        row=None
        for candidate in state['queue']:
            if eligible(c,candidate,now):continue
            run_id=str(candidate.get('artifact_run_id') or os.environ.get('ARTIFACT_RUN_ID',''))
            if not run_id.isdigit():continue
            try:
                data=s.api.call('GET','/actions/runs/'+run_id+'/artifacts?per_page=100')
            except Exception:continue
            if any(a.get('name')=='cliprausch-review-'+run_id and not a.get('expired',True) for a in data.get('artifacts',[])):
                row=candidate;break
        outputs={'needed':str(bool(row)).lower(),'artifact_run_id':str(row.get('artifact_run_id') or os.environ.get('ARTIFACT_RUN_ID','')) if row else ''}
        if os.environ.get('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'],'a') as output:
                for k,v in outputs.items():
                    if k=='artifact_run_id' and v and not v.isdigit():raise ValueError('artifact_identity_invalid')
                    output.write(k+'='+v+'\n')
        print('Cliprausch: automatic hosting '+outputs['needed']);return
    from .hosting import approve_and_host
    for row in list(state['queue']):
        if eligible(c,row,now):continue
        files=[p for p in Path('.review-download').rglob('final.mp4') if p.parent.name==row['clip_id']]
        if len(files)!=1:continue
        path=files[0]
        if hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:raise ValueError('automatic_media_hash_mismatch')
        qa=json.loads((path.parent/'qa.json').read_text());words=json.loads((path.parent/'transcript.json').read_text())
        try:row['review']=receipt(c,row,qa,words)
        except ValueError as error:
            row['reason']=str(error);state['queue'].remove(row);state.setdefault('rejected',[]).append(row)
            sha=s.save(state,sha);print('Cliprausch: automatic quality rejection');continue
        # The owner expressly authorized unattended reuse; this is an attestation, not an independent licence audit.
        row['audio_cleared']=True
        approve_and_host(c,s,state,sha,row,{'reviewed_media_sha256':row['sha256']},now)
        print('Cliprausch: automatic QA passed; immutable media ready');return

if __name__=='__main__':main()
