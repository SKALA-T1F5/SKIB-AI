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
    # 큐 라우팅 설정 추가
    task_routes={
        "process_document": {"queue": "preprocessing_queue"},
        "generate_test": {"queue": "generation_queue"},
        "test_generation.question_generation": {"queue": "generation_queue"},
        "test_generation.vector_search": {"queue": "preprocessing_queue"},
    },
    # 큐 정의 추가
    task_default_queue="default",
    worker_prefetch_multiplier=1,  # 메모리 효율성
    task_acks_late=True,  # 작업 완료 후 ACK
)

# 모든 Task 모듈을 autodiscovery에 포함
celery_app.autodiscover_tasks(
    [
        "config",  # config.tasks 모듈
        "api.document.services",  # document 관련 services
        "src.pipelines.test_generation",  # pipeline task들
        "src.pipelines.document_processing",  # 문서 처리 pipeline
    ]
)
