import redis
from django.conf import settings

# 싱글톤 패턴으로 Redis 클라이언트 관리


class RedisClient:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=0,
                decode_responses=True
            )
        return cls._instance


# 편의를 위한 전역 인스턴스
redis_client = RedisClient.get_instance()
