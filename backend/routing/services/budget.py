import time
from contextvars import ContextVar
from contextlib import contextmanager
from threading import BoundedSemaphore
from routing.providers.base import ProviderError
_deadline = ContextVar('weather_request_deadline',default=None)
_slots = BoundedSemaphore(2)

def remaining_seconds():
    deadline = _deadline.get()
    return max(0,deadline-time.monotonic()) if deadline is not None else 45

def check_deadline():
    if remaining_seconds() <= 0:
        raise ProviderError('provider_timeout','Evaluation exceeded its time limit.',True)

@contextmanager
def admission():
    if not _slots.acquire(blocking=False):
        raise ProviderError('service_busy','Service is busy. Try again shortly.',True)
    token = _deadline.set(time.monotonic()+45)
    try:
        yield
        check_deadline()
    finally:
        _deadline.reset(token)
        _slots.release()
