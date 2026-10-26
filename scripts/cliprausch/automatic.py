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
        qa.get('subtitle_mode') in ('word_highlight','source_preserved') and qa.get('video_codec')=='h264' and qa.get('audio_codec')=='aac' and
        all(qa.get(k)==row.get(k) for k in ('sha256','source_sha256','width','height','duration'))):
        raise ValueError('automatic_render_evidence_invalid')
    scan=qa.get('subtitle_scan',{})
    if not (scan.get('policy_version')==4 and scan.get('complete') is True and
        scan.get('source_sha256')==row['source_sha256'] and scan.get('method')=='tesseract_deu_eng_v1' and
        scan.get('decision')==qa['subtitle_mode'] and type(scan.get('detected')) is bool and
        qa.get('added_caption_tracks')==scan.get('added_caption_tracks')==int(not scan['detected']) and
        scan['decision']==('source_preserved' if scan['detected'] else 'word_highlight') and
        scan.get('frames_scanned',0)>0 and (scan['detected'] or scan['frames_scanned']==scan.get('planned_frames'))):
        raise ValueError('subtitle_scan_evidence_required')
    validate_words([{k:v for k,v in w.items() if k!='probability'} for w in words],row['duration'])
    if qa.get('uncertain_segments') or len(qa.get('uncertain_word_indexes',[]))/len(words)>.25:
        raise ValueError('automatic_subtitle_confidence_low')
    return {'subtitle_policy_version':4,'subtitle_mode':qa['subtitle_mode'],'kind':'automatic_render_v1','media_sha256':row['sha256'],'source_sha256':row['source_sha256'],
        'full_decode':True,'subtitles_valid':True,'rights_basis':c['rights'][row['streamer']]['evidence'],
        'note':'Technical checks only; rights rely on the account owner declaration; ASR can contain mistakes.'}

def select_artifact(c,state,api,now,fallback=''):
    for candidate in state['queue']:
        if eligible(c,candidate,now):continue
        run_id=str(candidate.get('artifact_run_id') or fallback)
        if not run_id.isdigit():continue
        try:data=api.call('GET','/actions/runs/'+run_id+'/artifacts?per_page=100')
        except Exception:continue
        if any(a.get('name')=='cliprausch-review-'+run_id and not a.get('expired',True) for a in data.get('artifacts',[])):
            return candidate
    return None

def discard_missing_artifacts(c,state,api,now):
    changed=False
    protected={a['clip_id'] for a in state['attempts'] if a['status'] not in ('verified_public','confirmed_sent')}
    for row in list(state['queue']):
        if row['clip_id'] in protected or eligible(c,row,now):continue
        run_id=str(row.get('artifact_run_id',''))
        if not run_id.isdigit():continue
        try:
            data=api.call('GET','/actions/runs/'+run_id+'/artifacts?per_page=100')
            present=any(a.get('name')=='cliprausch-review-'+run_id and not a.get('expired',True) for a in data.get('artifacts',[]))
            if present or api.call('GET','/actions/runs/'+run_id).get('status')!='completed':continue
        except Exception:continue
        state['queue'].remove(row)
        state.setdefault('technical_failures',[]).append(dict(row,reason='artifact_unavailable_after_run_completed',at=now.isoformat()))
        changed=True
    return changed

def main():
    import argparse
    from .cli import settings,store
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['plan','host']);args=parser.parse_args()
    c=settings();s=store(c);state,sha=s.load();now=dt.datetime.now(dt.timezone.utc)
    from .producer import expire_queue
    if expire_queue(state,now):sha=s.save(state,sha)
    if args.mode=='plan':
        discard_missing_artifacts(c,state,s.api,now)
        state['last_host_check_at']=now.isoformat();sha=s.save(state,sha)
        row=select_artifact(c,state,s.api,now,os.environ.get('ARTIFACT_RUN_ID',''))
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
