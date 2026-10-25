"""GitHub Actions entry point. Never emit service bodies, tokens or tracebacks."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re

from .core import validate_config, run_one, eligible, seal, timestamp
from .services import Gateway, State, RateLimited
from scripts.upload_transport import GitHubAPI

CONFIG=Path('scripts/cliprausch/config.json')

def settings():return validate_config(json.loads(CONFIG.read_text(encoding='utf-8')))

def gateway(c):
    key=os.environ.pop('CLIPRAUSCH_BUFFER_API_KEY','')
    g=Gateway(c,key);g.identity()
    return g

def store(c):return State(GitHubAPI(os.environ.pop('GH_TOKEN','')),c)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['plan','check','publish','publish-now','publish-test','review','approve','prepare','discover','production-plan','ranking','subtitle-check'])
    args=parser.parse_args();c=settings();now=dt.datetime.now(dt.timezone.utc)
    try:
        if args.mode=='plan':
            print(json.dumps({'account':c['handle'],'daily_target':c['daily_target'],
                'timezone':'Europe/Berlin','slots':c['slots'][str(c['daily_target'])],
                'commissioned':c['commissioned'],'source_count':len(c['sources'])},indent=2));return 0
        if args.mode=='subtitle-check':
            from .subtitle_check import check
            check(c,store(c),now);return 0
        if args.mode=='ranking':
            from .ranking import refresh,priorities
            s=store(c);state,sha=s.load()
            live=refresh(c,state,now)
            if live:s.save(state,sha)
            print(json.dumps({'live_refresh':live,'ranking_at':state.get('live_ranking',{}).get('at'),'priority_sources':priorities(c,state)[:15]}));return 0
        if args.mode in ('prepare','discover'):
            from .producer import produce
            return produce(c,now,discover_only=args.mode=='discover')
        if args.mode=='production-plan':
            from .core import slot_at
            s=store(c);state,sha=s.load()
            from .producer import expire_queue
            if expire_queue(state,now):sha=s.save(state,sha)
            production=dict(c,daily_target=5,slots={'5':c['prepare_slots']})
            slot=slot_at(production,now)
            needed=bool(slot and state.get('last_prepare_slot')!=slot and len(state['queue'])<c['daily_target']*2)
            if os.environ.get('GITHUB_OUTPUT'):
                with open(os.environ['GITHUB_OUTPUT'],'a') as output:output.write('needed='+str(needed).lower()+'\n')
            print('Cliprausch production: '+('needed' if needed else 'not_needed'));return 0
        if args.mode=='check':
            g=gateway(c)
            overview=g.overview(now-dt.timedelta(days=1),now+dt.timedelta(days=1))
            print(json.dumps({'account':c['handle'],'channel_id':c['channel_id'],
                'organization_id':c['organization_id'],'ready':overview['ready'],
                'posts_observed':len(overview['posts']),'publishing':False},indent=2));return 0
        s=store(c);state,sha=s.load()
        if args.mode in ('review','approve'):
            payload=json.loads(os.environ.pop('CLIPRAUSCH_REVIEW_JSON',''))
            candidate=next(r for r in state['queue'] if r['clip_id']==payload['clip_id'])
            if payload.get('reject') is True:
                state['queue'].remove(candidate)
                state.setdefault('rejected',[]).append(candidate)
                s.save(state,sha);print('Cliprausch: rejected without publication');return 0
            # Reviewed metadata may change; media fingerprints and source identity may not.
            for field in ('video_url','caption','audio_cleared','category'):
                if field in payload:candidate[field]=payload[field]
            candidate['review']=payload['review']
            if args.mode=='approve':
                from .hosting import approve_and_host
                approve_and_host(c,s,state,sha,candidate,payload,now)
                print('Cliprausch: approved media hosted and queued; no TikTok post sent');return 0
            if not eligible(c,candidate,now):raise ValueError('review_not_valid_or_expired')
            s.save(state,sha);print('Cliprausch: approved without publication');return 0
        if c.get('commissioned') is not True:raise ValueError('account_not_commissioned')
        if os.environ.get('CLIPRAUSCH_ENABLED')!='true':raise ValueError('scheduler_disabled')
        # Only contact Buffer for a due slot or pending reconciliation.
        from .core import slot_at
        pending=any(a['status'] not in ('verified_public','confirmed_sent') for a in state['attempts'])
        if state.get('cooldown_until') and now<timestamp(state['cooldown_until']):
            print('Cliprausch: cooldown');return 0
        if args.mode not in ('publish-now','publish-test') and not pending and slot_at(c,now) is None:
            print('Cliprausch: outside_slot');return 0
        if not pending and not any(eligible(c,r,now) for r in state['queue']):
            print('Cliprausch: empty_or_unapproved');return 0
        if pending and args.mode not in ('publish-now','publish-test'):
            attempt=next(a for a in state['attempts'] if a['status'] not in ('verified_public','confirmed_sent'))
            interval=1200 if (now-timestamp(attempt['reserved_at'])).total_seconds()<3600 else 3600
            if attempt.get('last_checked_at') and (now-timestamp(attempt['last_checked_at'])).total_seconds()<interval:
                print('Cliprausch: reconcile_wait');return 0
        try:result=run_one(c,s,gateway(c),now,immediate=args.mode in ('publish-now','publish-test'),commissioning_test=args.mode=='publish-test')
        except RateLimited as error:
            current,sha=s.load()
            current['cooldown_until']=(now+dt.timedelta(seconds=error.seconds)).isoformat()
            s.save(current,sha);print('Cliprausch: rate limit; durable cooldown saved');return 0
        print('Cliprausch: '+result);return 0
    except Exception as error:
        reason=str(error) if isinstance(error,ValueError) and re.fullmatch('[a-z_]{3,80}',str(error)) else type(error).__name__
        print('STOP Cliprausch: '+reason);return 1

if __name__=='__main__':raise SystemExit(main())
