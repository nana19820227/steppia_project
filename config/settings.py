import os
import dj_database_url  # データベース接続用
from pathlib import Path

# --- 1. 基本設定 ---
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-vvyo@62z3nv3jc@jtf7r1_^=b$50wxwa@gcd$4d-6@8)l!o)#h')

# Render上ではDEBUGをFalseにし、手元のMacではTrueにする設定
DEBUG = 'RENDER' not in os.environ

# RenderのURLとローカル環境を許可
ALLOWED_HOSTS = ['*']

# --- 2. アプリケーション定義 ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'steppia_app', 
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # 🆕 2番目に追加（画像表示用）
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# --- 3. データベース設定 ---
# RenderのPostgreSQLがあればそれを使い、なければSQLiteを使う
DATABASES = {
    'default': dj_database_url.config(
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
        conn_max_age=600
    )
}

# --- 4. パスワードバリデーション ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --- 5. 言語・時刻設定 ---
LANGUAGE_CODE = 'ja'
TIME_ZONE = 'Asia/Tokyo' # 🆕 ルーレットの0:00リセットに必須
USE_I18N = True
USE_TZ = True

# --- 6. 静的ファイル・メディア設定 ---
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / "static"]

# 🆕 Renderのデプロイ時にファイルをまとめる場所
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoiseで効率的に配信する設定
if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- 7. 認証・リダイレクト設定 ---
LOGIN_REDIRECT_URL = 'menu'
LOGOUT_REDIRECT_URL = 'menu'
LOGIN_URL = 'login'