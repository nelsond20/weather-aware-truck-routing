"""Serve the existing Vite build alongside the API on a WSGI host."""
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.views.decorators.http import require_safe


@require_safe
def index(request):
    try:
        response = FileResponse((settings.FRONTEND_DIST / 'index.html').open('rb'), content_type='text/html')
    except FileNotFoundError:
        raise Http404('Build the frontend before deployment.')
    response['Cache-Control'] = 'no-cache'
    return response


@require_safe
def asset(request, filename):
    if '\x00' in filename or len(filename.encode('utf-8')) > 255:
        raise Http404()
    root = (settings.FRONTEND_DIST / 'assets').resolve()
    file = (root / filename).resolve()
    content_type = {'.js': 'text/javascript', '.css': 'text/css'}.get(Path(filename).suffix)
    if file.parent != root or content_type is None:
        raise Http404()
    try:
        response = FileResponse(file.open('rb'), content_type=content_type)
    except (FileNotFoundError, IsADirectoryError):
        raise Http404()
    response['Cache-Control'] = 'public, max-age=31536000, immutable'
    return response
