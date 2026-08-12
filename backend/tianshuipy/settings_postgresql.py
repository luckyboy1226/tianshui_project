"""
Django settings for tianshuipy project - PostgreSQL 生产环境配置
使用 PostgreSQL 数据库（可选启用 PostGIS）
"""

from pathlib import Path
import os
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def env_list(name, default=None):
    value = os.getenv(name)
    if value is None:
        return list(default or [])
    return [item.strip() for item in value.split(',') if item.strip()]

# 加载环境变量
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured('使用 tianshuipy.settings_postgresql 时必须配置 SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env_bool('DEBUG', False)

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', ['127.0.0.1', 'localhost'])

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # 如果需要完整 GIS 功能，取消下面的注释
    # "django.contrib.gis",
    "rest_framework",
    "corsheaders",
    # 自定义应用
    "users",
    "environment",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "tianshuipy.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "tianshuipy.wsgi.application"

# Database - PostgreSQL 配置
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        # 如果需要 GIS 功能，使用：
        # "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": os.getenv('DB_NAME', 'tianshuipy'),
        "USER": os.getenv('DB_USER', 'postgres'),
        "PASSWORD": os.getenv('DB_PASSWORD', ''),
        "HOST": os.getenv('DB_HOST', 'localhost'),
        "PORT": os.getenv('DB_PORT', '5432'),
        "OPTIONS": {
            "options": "-c client_encoding=UTF8",
        },
        "CONN_MAX_AGE": 60,  # 连接池配置，保持连接 60 秒
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

# 字符编码设置
DEFAULT_CHARSET = 'utf-8'
FILE_CHARSET = 'utf-8'

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# 自定义用户模型
AUTH_USER_MODEL = 'users.User'

# 生产环境默认更严格：上传、发布、任务执行等写操作要求登录
ALLOW_PUBLIC_USER_REGISTRATION = env_bool('ALLOW_PUBLIC_USER_REGISTRATION', False)
ALLOW_ANONYMOUS_ANALYSIS_UPLOADS = env_bool('ALLOW_ANONYMOUS_ANALYSIS_UPLOADS', False)
ALLOW_ANONYMOUS_BUSINESS_LAYER_ADMIN = env_bool('ALLOW_ANONYMOUS_BUSINESS_LAYER_ADMIN', False)
ALLOW_ANONYMOUS_OVERLAY_ADMIN = env_bool('ALLOW_ANONYMOUS_OVERLAY_ADMIN', False)
ALLOW_PUBLIC_FEEDBACK_MANAGEMENT = env_bool('ALLOW_PUBLIC_FEEDBACK_MANAGEMENT', False)

# REST Framework 配置
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'environment.renderers.UTF8JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
}

# CORS 配置
CORS_ALLOW_ALL_ORIGINS = env_bool('CORS_ALLOW_ALL_ORIGINS', False)
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = env_list('CORS_ALLOWED_ORIGINS', [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
])
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS', CORS_ALLOWED_ORIGINS)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = env_bool('SESSION_COOKIE_SECURE', False)
SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
CSRF_COOKIE_SECURE = env_bool('CSRF_COOKIE_SECURE', False)
CSRF_COOKIE_HTTPONLY = env_bool('CSRF_COOKIE_HTTPONLY', False)
CSRF_COOKIE_SAMESITE = os.getenv('CSRF_COOKIE_SAMESITE', 'Lax')
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = os.getenv('SECURE_REFERRER_POLICY', 'same-origin')
X_FRAME_OPTIONS = os.getenv('X_FRAME_OPTIONS', 'DENY')

# 文件上传配置
# 大遥感栅格不能放进内存处理；超过 10MB 的上传交给 Django 临时文件处理器落盘。
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024 * 1024
MAX_UPLOAD_SIZE = 10 * 1024 * 1024 * 1024
FILE_UPLOAD_HANDLERS = [
    'django.core.files.uploadhandler.MemoryFileUploadHandler',
    'django.core.files.uploadhandler.TemporaryFileUploadHandler',
]

# 日志配置
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'WARNING',  # 生产环境建议设为 WARNING
            'propagate': False,
        },
    },
}

# 创建必要的目录
os.makedirs(BASE_DIR / 'logs', exist_ok=True)
os.makedirs(BASE_DIR / 'media' / 'remote_sensing', exist_ok=True)
os.makedirs(BASE_DIR / 'media' / 'thumbnails', exist_ok=True)
os.makedirs(BASE_DIR / 'media' / 'ecological_indices', exist_ok=True)
os.makedirs(BASE_DIR / 'media' / 'visualizations', exist_ok=True)
os.makedirs(BASE_DIR / 'media' / 'overlay_analysis' / 'rasters', exist_ok=True)

# GeoServer配置
GEOSERVER_URL = os.getenv('GEOSERVER_URL', 'http://localhost:8080/geoserver')
GEOSERVER_USERNAME = os.getenv('GEOSERVER_USERNAME', 'admin')
GEOSERVER_PASSWORD = os.getenv('GEOSERVER_PASSWORD', 'geoserver')
GEOSERVER_WORKSPACE = os.getenv('GEOSERVER_WORKSPACE', 'tianshuipy')

# 地理空间服务配置
SPATIAL_SERVICES = {
    'WMS_ENABLED': True,
    'WFS_ENABLED': True,
    'WCS_ENABLED': True,
    'DEFAULT_CRS': 'EPSG:4326',
    'MAX_FEATURES': 10000,
}

# Celery 配置（本地开发默认同步执行，避免未启动 Redis 时接口直接失败）
CELERY_TASK_ALWAYS_EAGER = os.getenv('CELERY_TASK_ALWAYS_EAGER', 'true').lower() == 'true'
CELERY_TASK_EAGER_PROPAGATES = False
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'memory://')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'cache+memory://')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30分钟
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25分钟

