"""Bounded self-renewing GitHub clock, adapted from the working UFO clock.
Only dispatches this repository's pipeline; never receives a Buffer credential.
"""
import argparse
import datetime as dt
import os
import time
from .core import eligible,timestamp,BERLIN
from .scheduling import due_slot,preparation_due
from .services import State
from scripts.upload_transport import GitHubAPI,ServiceError,request_json,GITHUB_URL

ACTIVE={'queued','in_progress','waiting','pending','requested'}
SETTLED={'verified_public','confirmed_sent'}
class PublicReadOnly:
    def call(self,method,path,body=None):
        if method!='GET' or body is not None:raise ServiceError('clock_read_only')
        return request_json(GITHUB_URL+path)

def plan(c,state,runs,now):
    if any(r.get('head_branch')=='main' and r.get('status') in ACTIVE for r in runs):return 'active_pipeline'
    if state.get('cooldown_until') and now<timestamp(state['cooldown_until']):return 'send_cooldown'
    pending=[a for a in state['attempts'] if a.get('status') not in SETTLED]
    if pending:
        if len(pending)!=1:raise ValueError('multiple_unresolved')
        attempt=pending[0];age=(now-timestamp(attempt['reserved_at'])).total_seconds()
        interval=1200 if age<3600 else 3600
        if attempt.get('last_checked_at') and (now-timestamp(attempt['last_checked_at'])).total_seconds()<interval:
            return 'reconciliation_backoff'
        return 'dispatch_publish'
    waiting='waiting_for_slot_or_stock_cooldown'
    if due_slot(c,state,now) and any(eligible(c,r,now) for r in state['queue']):
        moments=[max(timestamp(a['reserved_at']),timestamp(a.get('sent_at',a['reserved_at']))) for a in state['attempts']]
        if sum((now-t).total_seconds()<86400 or t.astimezone(BERLIN).date()==now.astimezone(BERLIN).date() for t in moments)>=c['daily_target']:
            waiting='daily_limit'
        elif moments and (now-max(moments)).total_seconds()<c['min_spacing_minutes']*60:waiting='spacing'
        else:return 'dispatch_publish'
    # Let the existing publisher host newly rendered artifacts even before a posting slot.
    raw=[r for r in state['queue'] if not eligible(c,r,now) and r.get('artifact_run_id')]
    checked=state.get('last_host_check_at')
    if raw and (not checked or (now-timestamp(checked)).total_seconds()>=1200):return 'dispatch_publish'
    if preparation_due(c,state,now):return 'dispatch_prepare'
    return waiting

def tick(api,c,now,dispatch=True):
    state,_=State(api,c).load();runs=[]
    for status in sorted(ACTIVE):
        response=api.call('GET','/actions/workflows/cliprausch.yml/runs?branch=main&status='+status+'&per_page=100')
        if not isinstance(response.get('workflow_runs'),list):raise ValueError('invalid_clock_runs')
        if response.get('total_count',len(response['workflow_runs']))>100:raise ValueError('clock_runs_incomplete')
        runs.extend(response['workflow_runs'])
    result=plan(c,state,runs,now)
    if dispatch and result.startswith('dispatch_'):
        api.call('POST','/actions/workflows/cliprausch.yml/dispatches',{'ref':'main','inputs':{'mode':result.removeprefix('dispatch_')}})
    return result

def main():
    from .cli import settings
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',action='store_true');args=parser.parse_args()
    token=os.environ.pop('GH_TOKEN','')
    try:
        minutes=int(os.environ.pop('CLIPRAUSCH_CLOCK_MINUTES','300'))
        if minutes not in (5,300):raise ValueError('invalid_clock_duration')
        if args.run and (os.getenv('GITHUB_REPOSITORY')!='renej11-coder/cliprausch' or os.getenv('GITHUB_REF')!='refs/heads/main' or not token):
            raise ValueError('unapproved_clock_context')
        api=GitHubAPI(token) if token else PublicReadOnly();c=settings()
        deadline=time.monotonic()+minutes*60;previous=None
        while True:
            now=dt.datetime.now(dt.timezone.utc)
            try:result=tick(api,c,now,dispatch=args.run)
            except ServiceError as error:
                if str(error) in ('github_http_401','github_http_403'):raise
                result='retry_later'
            if result!=previous or result.startswith('dispatch_'):
                print(now.isoformat()+' Cliprausch clock: '+result,flush=True);previous=result
            if not args.run:return 0
            remaining=deadline-time.monotonic()
            if remaining<=0:break
            time.sleep(min(120,remaining))
        api.call('POST','/actions/workflows/cliprausch_clock.yml/dispatches',{'ref':'main','inputs':{'duration_minutes':'300'}})
        print('Cliprausch clock: successor_dispatch_accepted',flush=True);return 0
    except Exception as error:
        print('STOP Cliprausch clock: '+type(error).__name__,flush=True);return 1

if __name__=='__main__':raise SystemExit(main())
