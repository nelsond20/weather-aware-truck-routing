import os
os.environ.setdefault('DJANGO_SECRET_KEY','local-test-key-no-real-credentials')
from .settings import *
ALLOWED_HOSTS = ['testserver','localhost','127.0.0.1']
