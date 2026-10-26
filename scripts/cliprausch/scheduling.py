"""Delay-tolerant daily slots and stock replenishment shared by pipeline and clock."""
import datetime as dt
from .core import BERLIN,timestamp

def due_slot(c,state,now):
    if now.tzinfo is None:raise ValueError('timezone_required')
    local=now.astimezone(BERLIN);day=local.date().isoformat()
    used={a.get('slot') for a in state.get('attempts',[])}
    for clock in c['slots'][str(c['daily_target'])]:
        slot=day+'/'+clock
        if slot not in used and local.time().replace(tzinfo=None)>=dt.time.fromisoformat(clock):return slot
    return None

def preparation_due(c,state,now):
    local=now.astimezone(BERLIN)
    if not 8<=local.hour<=23 or len(state['queue'])>=c['daily_target']*2:return False
    previous=state.get('last_prepare_at')
    return not previous or (now-timestamp(previous)).total_seconds()>=1800
