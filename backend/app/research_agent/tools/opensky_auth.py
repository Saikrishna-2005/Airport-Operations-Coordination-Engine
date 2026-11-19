"""Cached OAuth2 credentials using protected transport."""
import threading
import time
import math
from app.research_agent.schemas import ErrorInfo
from app.research_agent.tools.opensky_dispatcher import TOKEN as OPENSKY_TOKEN_URL, protected_request, DispatchError

class OpenSkyAuthManager:
    def __init__(self):
        self._lock=threading.Lock()
        self._cached=None
    def clear(self):
        with self._lock: self._cached=None
    def get_token(self,client_id,client_secret,client,*,force_refresh=False):
        with self._lock:
            if not force_refresh and self._cached and self._cached[0]==(client_id,client_secret) and time.monotonic()<self._cached[2]-60:
                return self._cached[1],None
            self._cached=None
            try:
                response=protected_request(client,OPENSKY_TOKEN_URL,data={'grant_type':'client_credentials','client_id':client_id,'client_secret':client_secret},headers={'Content-Type':'application/x-www-form-urlencoded'})
                if response.status_code!=200:
                    status=response.status_code
                    raise DispatchError('RATE_LIMITED' if status==429 else 'AUTH_FAILED',f'OpenSky token endpoint returned HTTP {status}.',status==429)
                payload=response.json(); token=payload['access_token']; expires=float(payload.get('expires_in',1800))
                if not isinstance(token,str) or not token or not math.isfinite(expires) or expires<=0: raise ValueError()
                self._cached=((client_id,client_secret),token,time.monotonic()+expires)
                return token,None
            except DispatchError as exc:
                return None,ErrorInfo(tool='flight_tool',code=exc.code,message=exc.message,retryable=exc.retryable)
            except (ValueError,TypeError,KeyError,AttributeError,OverflowError):
                return None,ErrorInfo(tool='flight_tool',code='INVALID_PAYLOAD',message='Malformed OpenSky token response.',retryable=False)

global_auth_manager=OpenSkyAuthManager()
