
from pathlib import Path
import os
from dotenv import load_dotenv
load_dotenv()  

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'django-insecure-w$lf-el7#p$%u9)bm%tnk3f8(d#x-weog&^r%xz-krd=3(#vk2'

DEBUG = True

ALLOWED_HOSTS = ['*','loclhost','152.42.231.103','www.aiha.live','aiha.live']


SHARED_APPS = [ 
    'django_tenants',    
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
   'symptom_checker'
    
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




MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware', 
    'django.contrib.auth.middleware.AuthenticationMiddleware', 
    'django_tenants.middleware.TenantMiddleware',       
    'django.contrib.messages.middleware.MessageMiddleware',  
     'django.middleware.locale.LocaleMiddleware', 
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',             
    'clients.middleware.CustomGeneralPurposeMiddleWare',         
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

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
               
            ],
        },
    },
]

WSGI_APPLICATION = 'myproject.wsgi.application'



# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }



DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',
        'NAME': 'myproject',  # your PostgreSQL database name
        'USER': 'arafat',      # the user you created for PostgreSQL
        'PASSWORD': 'Arafat_123',  # the password for your PostgreSQL user
        'HOST': 'localhost',    # default for local database
        'PORT': '5432',         # default PostgreSQL port
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


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


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


TIME_ZONE = 'UTC'

USE_TZ = True



STATIC_URL = "/static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media/")



# LOGIN_REDIRECT_URL = '/prescription/'


LOGIN_REDIRECT_URL = '/clients/tenant_expire_check/'
LOGIN_URL = 'accounts:login'






EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'



