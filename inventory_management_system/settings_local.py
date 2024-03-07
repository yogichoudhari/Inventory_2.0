from .settings import *



DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'inventory',
        'USER':'inventory_admin',
        'PASSWORD':"Physically11",
        'HOST':'localhost',
        'PORT':'5432'
    }
}

DEBUG = True

REDIS_HOST = 'localhost'
REDIS_PORT = 6379

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://localhost:6379/1",
    }
}