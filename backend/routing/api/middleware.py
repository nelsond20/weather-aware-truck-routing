from django.http import JsonResponse
from django.core.exceptions import RequestDataTooBig
from django.conf import settings

class DeliveryHeadersMiddleware:
    def __init__(self, get_response):self.get_response = get_response
    def __call__(self, request):
        request.get_host()
        response = self.get_response(request)
        response['X-Frame-Options'] = 'DENY'
        if not settings.DEBUG:
            response['Content-Security-Policy'] = (
                "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                "connect-src 'self' https:; img-src 'self' data: blob: https:; "
                "worker-src 'self'; object-src 'none'; base-uri 'self'; "
                "form-action 'self'; frame-ancestors 'none'"
            )
        return response

class BodyLimitMiddleware:
    def __init__(self,get_response):self.get_response=get_response
    def __call__(self,request):
        try:
            if int(request.META.get('CONTENT_LENGTH') or 0)>2*1024*1024 or len(request.body)>2*1024*1024:
                raise RequestDataTooBig()
        except RequestDataTooBig:
            return JsonResponse({'code':'body_too_large','message':'Request body exceeds 2 MiB.','retryable':False},status=413)
        except ValueError:
            return JsonResponse({'code':'invalid_input','message':'Invalid content length.','retryable':False},status=400)
        return self.get_response(request)
