from rest_framework.views import exception_handler as drf_handler
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError,ParseError
from routing.providers.base import ProviderError

def codes(value):
    if isinstance(value,dict):return [c for item in value.values() for c in codes(item)]
    if isinstance(value,list):return [c for item in value for c in codes(item)]
    return [getattr(value,'code',None)]

def exception_handler(exc,context):
    if isinstance(exc,ProviderError):
        status=400 if exc.code in ('sampling_limit_exceeded','invalid_base_time') else 502 if exc.code=='provider_contract_invalid' else 503
        return Response({'code':exc.code,'message':exc.message,'retryable':exc.retryable},status=status)
    if isinstance(exc,(ValidationError,ParseError)):
        found=codes(getattr(exc,'detail',None))
        code='departure_in_past' if 'departure_in_past' in found else 'invalid_base_time' if 'invalid_base_time' in found else 'invalid_input'
        return Response({'code':code,'message':'Departure is in the past.' if code=='departure_in_past' else 'Check the request fields.','retryable':False},status=400)
    response=drf_handler(exc,context)
    if response is not None:response.data={'code':'invalid_input','message':'Request could not be processed.','retryable':False}
    return response
