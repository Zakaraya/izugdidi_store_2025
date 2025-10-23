from .base import *  # noqa
DEBUG = True
ALLOWED_HOSTS = ["*"]
CACHES["default"]["KEY_PREFIX"] = "local"

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
