# src/config/settings/local.py
from .base import *

DEBUG = True
# локальные медиа на файловой системе:
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# from .base import *  # noqa
# DEBUG = True
# ALLOWED_HOSTS = ["*"]
# CACHES["default"]["KEY_PREFIX"] = "local"
#
# EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
# SECURE_SSL_REDIRECT = False
# SESSION_COOKIE_SECURE = False
# CSRF_COOKIE_SECURE = False
