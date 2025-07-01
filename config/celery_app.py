from celery import Celery

from config.settings import settings

# Celery 앱 생성
celery_app = Celery(
    "skib_ai",
    broker=f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}",
    backend=f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}",
)

# Redis 패스워드가 있다면
if settings.redis_password:
    broker_url = f"redis://:{settings.redis_password}@{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
    celery_app.conf.broker_url = broker_url
    celery_app.conf.result_backend = broker_url

# 기본 설정
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,
)
