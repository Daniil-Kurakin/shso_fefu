from .base import *

DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = ALLOWED_HOSTS or ["localhost", "127.0.0.1", "[::1]"]
