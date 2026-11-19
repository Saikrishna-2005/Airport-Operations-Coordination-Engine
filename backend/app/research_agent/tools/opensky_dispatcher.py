"""Local protected OpenSky transport. No automatic budget refill."""
import math
import sqlite3
import time
from datetime import timezone, datetime
from email.utils import parsedate_to_datetime
import httpx
from app.research_agent.config import settings
from app.research_agent.tools.api_quota import ApiQuota

BASE = 'https://opensky-network.org/api/'
TOKEN = 'https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token'

class DispatchError(Exception):
    def __init__(self, code, message, retryable=False):
        super().__init__(message)
        self.code, self.message, self.retryable = code, message, retryable


def request_cost(url, params):
    if url == BASE+'states/all':
        keys = ('lamin','lamax','lomin','lomax')
        if not any(k in params for k in keys): return 'states', 'states/all', 4
        if not all(k in params for k in keys): raise ValueError('Incomplete bounding box')
        a,b,c,d = (params[k] for k in keys)
        if not all(type(x) in (int,float) and math.isfinite(x) for x in (a,b,c,d)) or not (-90<=a<b<=90 and -180<=c<d<=180):
            raise ValueError('Invalid bounding box')
        area=(b-a)*(d-c)
        return 'states','states/all', 1 if area<=25 else 2 if area<=100 else 3 if area<=400 else 4
    if url in {BASE+'flights/'+p for p in ('all','arrival','departure','aircraft')}:
        a,b=params.get('begin'),params.get('end')
        if type(a) is not int or type(b) is not int or not 0<a<b or b-a>(7200 if url.endswith('/all') else 172800): raise ValueError('Invalid interval')
        # Conservative charge for UTC partitions, including both boundary days.
        n=b//86400-a//86400+1
        cost=4 if b-a<86400 and n==1 else 30 if n<=2 else 60*n
        return 'flights',url[len(BASE):],cost
    if url==BASE+'tracks/all':
        t=params.get('time')
        if type(t) is not int or t<0: raise ValueError('Invalid track time')
        # Historical point lookup partition cost is not explicit in provider docs.
        return 'tracks','tracks/all',4 if t==0 else 30
    raise ValueError('Unsupported OpenSky endpoint')


def cooldown_seconds(response):
    delays=[settings.OPENSKY_COOLDOWN_SECONDS]
    for key in ('Retry-After','X-Rate-Limit-Retry-After-Seconds'):
        raw=response.headers.get(key,'')
        try: value=float(raw)
        except ValueError:
            try: value=(parsedate_to_datetime(raw)-datetime.now(timezone.utc)).total_seconds()
            except (ValueError,TypeError,OverflowError): continue
        if math.isfinite(value) and value>0: delays.append(value)
    return max(delays)


def protected_request(client, url, *, params=None, headers=None, data=None):
    if settings.DATA_MODE!='live': raise DispatchError('LIVE_DISABLED','Server live mode is disabled.')
    try:
        category,endpoint,cost = ('auth','token',1) if url==TOKEN else request_cost(url,params or {})
    except ValueError as exc: raise DispatchError('INVALID_REQUEST',str(exc)) from None
    limit=getattr(settings,'OPENSKY_'+category.upper()+'_BUDGET' if category=='auth' else 'OPENSKY_'+category.upper()+'_CREDIT_BUDGET')
    if limit==0: raise DispatchError('BUDGET_EXHAUSTED','Local OpenSky budget is zero.')
    try:
        quota=ApiQuota()
        decision=quota.reserve('opensky',category,endpoint,limit=limit,mode='live',cost=cost,protected=True)
    except (sqlite3.Error,OSError,ValueError,OverflowError): raise DispatchError('QUOTA_UNAVAILABLE','Local OpenSky quota unavailable.') from None
    if not decision.allowed:
        raise DispatchError({'pending_request':'PENDING_REQUEST','cooldown':'RATE_LIMITED','budget_exhausted':'BUDGET_EXHAUSTED'}.get(decision.reason,'QUOTA_UNAVAILABLE'),'Local OpenSky quota blocked request.',decision.reason=='cooldown')
    try:
        if url==TOKEN: response=client.post(url,data=data,headers=headers,follow_redirects=False)
        else: response=client.get(url,params=params,headers=headers,follow_redirects=False)
    except httpx.RequestError:
        raise DispatchError('PENDING_REQUEST','Network outcome unresolved; live requests blocked for this category.') from None
    try:
        quota.finalize('opensky',category,decision.request_id,cooldown_seconds=cooldown_seconds(response) if response.status_code==429 else None)
    except (sqlite3.Error,OSError,ValueError,OverflowError): raise DispatchError('QUOTA_UNAVAILABLE','Could not finalize OpenSky request; category blocked.') from None
    return response


def dispatch(client,url,params):
    from app.research_agent.tools.opensky_auth import global_auth_manager
    if settings.DATA_MODE!='live': raise DispatchError('LIVE_DISABLED','Server live mode is disabled.')
    try: category,_,cost=request_cost(url,params)
    except ValueError as exc: raise DispatchError('INVALID_REQUEST',str(exc)) from None
    limit=getattr(settings,'OPENSKY_'+category.upper()+'_CREDIT_BUDGET')
    if limit<cost: raise DispatchError('BUDGET_EXHAUSTED','Local OpenSky budget insufficient.')
    cid=settings.FLIGHT_CLIENT_ID.strip(); secret=settings.FLIGHT_CLIENT_SECRET.strip()
    if bool(cid)!=bool(secret): raise DispatchError('AUTH_FAILED','Incomplete OpenSky credentials.')
    if category!='states' and not cid: raise DispatchError('AUTH_FAILED','Historical access requires credentials.')
    headers={}
    for attempt in range(2):
        if cid:
            token,error=global_auth_manager.get_token(cid,secret,client,force_refresh=attempt>0 and refresh)
            if error: raise DispatchError(error.code,error.message,error.retryable)
            headers={'Authorization':'Bearer '+token}
        response=protected_request(client,url,params=params,headers=headers)
        status=response.status_code
        if status==200 or (status==404 and category!='states'): return response
        refresh=status==401 and bool(cid)
        if attempt==0 and (refresh or 500<=status<600): continue
        code='RATE_LIMITED' if status==429 else 'AUTH_FAILED' if status in (401,403) else 'PROVIDER_ERROR'
        raise DispatchError(code,f'OpenSky returned HTTP {status}.',status==429 or status>=500)
