"""Single-worker admission; shared proxy limits required for production."""
import logging
import time
from collections import deque
from threading import Lock
from rest_framework.response import Response
_lock=Lock()
_entries={}
LIMITS={'evaluate':10,'corridor':5,'geocode':30}
logger = logging.getLogger(__name__)

def reset_limits():
    with _lock:_entries.clear()

def throttle(request,kind):
    # Never trust a freely supplied X-Forwarded-For.
    key=(request.META.get('REMOTE_ADDR','unknown'),kind)
    now=time.monotonic()
    with _lock:
        for expired in [k for k,v in _entries.items() if not v or v[-1] <= now-60]:_entries.pop(expired,None)
        if key not in _entries and len(_entries)>=10000:
            logger.warning('operation_rejected source=internal_budget limiter=client_tracking_capacity operation=%s code=service_busy',kind)
            return Response({'code':'service_busy','message':'Service is busy.','retryable':True},status=503)
        queue=_entries.setdefault(key,deque())
        while queue and queue[0]<=now-60:queue.popleft()
        if len(queue)>=LIMITS[kind]:
            logger.warning('operation_rejected source=internal_budget limiter=client_request_rate operation=%s code=rate_limited status=429',kind)
            return Response({'code':'rate_limited','message':'Too many requests. Try again shortly.','retryable':True},status=429,headers={'Retry-After':str(max(1,int(60-(now-queue[0]))+1))})
        queue.append(now)
