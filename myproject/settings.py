
from pathlib import Path
import os
from dotenv import load_dotenv 
load_dotenv()  

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'django-insecure-w$lf-el7#p$%u9)bm%tnk3f8(d#x-weog&^r%xz-krd=3(#vk2'

DEBUG = True

ALLOWED_HOSTS = ['*','loclhost','152.42.231.103','www.aiha.live','aiha.live']

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    "authorization",
    "content-type",
    "x-requested-with",
    "accept",
    "origin",
    "user-agent",
    "x-csrftoken",
    "accept-encoding",
]

CSRF_TRUSTED_ORIGINS = [
    "https://prescription.aiha.live",
     "https://*.aiha.live",

]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')





SHARED_APPS = [ 
    'channels',
    'daphne', 
    'django_tenants', 
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',   
    'corsheaders',
    'django.contrib.contenttypes',  
    'django.contrib.sessions',     
    'django.contrib.messages',     
    'django.contrib.staticfiles',  
    'django_crontab',               
    'django_celery_beat',   
    'django_extensions',   
    'django.contrib.humanize',   
    'django.contrib.sites',
    'django.contrib.auth',   
    'django.contrib.admin',  
    'accounts',
    'clients',   
     

]

TENANT_APPS = [  
   'prescription',
   'finance',
   'messaging',
   'payment_gateway',
   'symptom_checker',
   'other_services',
   'appointments',
   'chat',
   'store',
   'payment',
   'basket',
   'orders',
    'mptt',
    
]


INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]

SITE_ID = 1

TENANT_MODEL = "clients.Client"  
TENANT_DOMAIN_MODEL = "clients.Domain"  
DATABASE_ROUTERS = ("django_tenants.routers.TenantSyncRouter",)
PUBLIC_SCHEMA_NAME = 'public'

AUTH_USER_MODEL = 'accounts.CustomUser' 



AUTHENTICATION_BACKENDS = [
    'accounts.backends.TenantAuthenticationBackend',  # Custom tenant-aware backend
    'django.contrib.auth.backends.ModelBackend',  # Default Django backend
]


REST_FRAMEWORK = {
       'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}


MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',

    'django_tenants.middleware.TenantMiddleware',  # 👈 must come early

    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.locale.LocaleMiddleware',
     'clients.middleware.CustomGeneralPurposeMiddleWare',
    # 'clients.middleware.TrackUserActivityMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]




CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}



ROOT_URLCONF = 'myproject.urls'

TEMPLATES = [
    {
       'BACKEND': 'django.template.backends.django.DjangoTemplates',
       'DIRS': [os.path.join(BASE_DIR, 'templates')], 
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'accounts.context_processors.user_info',
                'accounts.context_processors.unread_notifications',
                'accounts.context_processors.tenant_context',
                "store.context_processors.categories",
                "basket.context_processors.basket",
               
            ],
        },
    },
]

WSGI_APPLICATION = 'myproject.wsgi.application'
ASGI_APPLICATION = 'myproject.asgi.application'

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],  # Your Redis host & port
        },
    },
}




# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }



DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT'),
    }
}



# AUTH_PASSWORD_VALIDATORS = [
#     {
#         'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
#     },
# ]


from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}



OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
BASKET_SESSION_ID = "basket"

LANGUAGE_CODE = 'en'
LANGUAGES = [
    ('en', 'English'),
    ('bn', 'বাংলা'),
    ('hi', 'Hindi'),
    # Add others as needed
]

USE_I18N = True
USE_L10N = True
USE_TZ = True

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),  
]


# TIME_ZONE = 'UTC'
TIME_ZONE = 'Asia/Dhaka'
USE_TZ = True



STATIC_URL = "/static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media/")



# LOGIN_REDIRECT_URL = '/prescription/'


LOGIN_REDIRECT_URL = '/clients/tenant_expire_check/'
LOGIN_URL = 'accounts:login'





#EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'mail.e2esolutionsbd.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_HOST_USER = 'humayun@e2esolutionsbd.com'
EMAIL_HOST_PASSWORD = 'ArafaT_1234'
DEFAULT_FROM_EMAIL = 'humayun@e2esolutionsbd.com'


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


SSLZCOMMERZ_STORE_ID = "mymep684ff9c9b6d95"
SSLZCOMMERZ_STORE_PASS = "mymep684ff9c9b6d95@ssl"
SSLZCOMMERZ_IS_SANDBOX = True  # Set to False in production

import os
from logging.handlers import RotatingFileHandler

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {name} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {name} {message}',
            'style': '{',
        },
    },

    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',  # ✅ Correct
            'filename': os.path.join(BASE_DIR, 'error.log'),
            'maxBytes': 1024 * 1024 * 1,  # 1 MB
            'backupCount': 3,  # Keep last 3 files: error.log.1, error.log.2, etc.
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },

    'root': {
        'handlers': ['file', 'console'],
        'level': 'INFO',
    },

    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}
