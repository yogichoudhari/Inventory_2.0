from .settings import *



DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'inventory101',
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
        "LOCATION": "redis://127.0.0.1:6379/1",
    }
}


REDIS_DB = 0
REDIS_PASSWORD = None

Q_CLUSTER = {
    "name": "hello-django",
    "workers": 8,
    "recycle": 500,
    "timeout": 60,  
    "compress": True,
    "cpu_affinity": 1,
    "save_limit": 250,
    "queue_limit": 500,
    "label": "Django Q",
    "redis": {
        "host": REDIS_HOST,
        "port": REDIS_PORT,
        "db": REDIS_DB,
        "password": REDIS_PASSWORD,
    },
}