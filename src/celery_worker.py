from celery import Celery
from celery.schedules import crontab
from src.config import get_settings
from src.database import SessionLocal
from src.models import ActivationToken, PasswordResetToken
from datetime import datetime

settings = get_settings()

celery_app = Celery(
    "online_cinema",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)


@celery_app.task
def cleanup_expired_tokens():
    """Periodic task to delete expired activation and password reset tokens"""
    db = SessionLocal()
    try:
        now = datetime.utcnow()

        expired_activation = db.query(ActivationToken).filter(
            ActivationToken.expires_at < now
        ).all()

        for token in expired_activation:
            db.delete(token)

        expired_reset = db.query(PasswordResetToken).filter(
            PasswordResetToken.expires_at < now
        ).all()

        for token in expired_reset:
            db.delete(token)

        db.commit()

        return {
            "activation_tokens_deleted": len(expired_activation),
            "password_reset_tokens_deleted": len(expired_reset)
        }
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


celery_app.conf.beat_schedule = {
    'cleanup-expired-tokens': {
        'task': 'app.celery_worker.cleanup_expired_tokens',
        'schedule': crontab(minute='0', hour='*/1'),  # Run every hour
    },
}
