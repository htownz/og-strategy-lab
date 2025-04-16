import os
from flask_appbuilder.security.manager import AUTH_DB

# Superset specific config
ROW_LIMIT = 5000
SUPERSET_WEBSERVER_PORT = 8088

# Database configuration
SQLALCHEMY_DATABASE_URI = os.environ.get('SUPERSET_DB_URI', 'postgresql://postgres:postgres@postgres:5432/og_strategy_lab')

# Redis configuration for caching
REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')
REDIS_PORT = os.environ.get('REDIS_PORT', '6379')
REDIS_CELERY_DB = os.environ.get('REDIS_CELERY_DB', '0')
REDIS_RESULTS_DB = os.environ.get('REDIS_RESULTS_DB', '1')

# Cache configuration
CACHE_CONFIG = {
    'CACHE_TYPE': 'RedisCache',
    'CACHE_DEFAULT_TIMEOUT': 300,
    'CACHE_KEY_PREFIX': 'superset_',
    'CACHE_REDIS_HOST': REDIS_HOST,
    'CACHE_REDIS_PORT': REDIS_PORT,
    'CACHE_REDIS_DB': REDIS_RESULTS_DB,
}

# Celery configuration
class CeleryConfig:
    BROKER_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_CELERY_DB}'
    CELERY_IMPORTS = ('superset.sql_lab', )
    CELERY_RESULT_BACKEND = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_RESULTS_DB}'
    CELERY_ANNOTATIONS = {'tasks.add': {'rate_limit': '10/s'}}
    CONCURRENCY = 4

CELERY_CONFIG = CeleryConfig

# Dashboard refresh timing
SUPERSET_DASHBOARD_POSITION_DATA_LIMIT = 65535
MAPBOX_API_KEY = os.environ.get('MAPBOX_API_KEY', '')
TALISMAN_ENABLED = False

# Feature flags
FEATURE_FLAGS = {
    'ALERT_REPORTS': True,
    'DASHBOARD_NATIVE_FILTERS': True,
    'DASHBOARD_CROSS_FILTERS': True,
    'DASHBOARD_FILTERSCOPE_MODAL': True,
    'ENABLE_TEMPLATE_PROCESSING': True,
    'GLOBAL_ASYNC_QUERIES': True,
    'SQL_VALIDATORS_BY_ENGINE': True,
    'SCHEDULED_QUERIES': True,
}

# OG Strategy Lab specific customizations
CUSTOM_TEMPLATE_PROCESSORS = {
    'postgresql': lambda: OGStrategyLabTemplateProcessor,
}

class OGStrategyLabTemplateProcessor:
    @staticmethod
    def process_template(sql, **kwargs):
        # Custom template processing for OG Strategy Lab
        return sql