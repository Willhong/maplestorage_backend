import time
from functools import wraps
from .redis_client import redis_client
import logging

logger = logging.getLogger('maple_api')


def check_rate_limit(max_calls: int = 500):
    """
    레이트 리밋을 체크하는 함수
    1초당 max_calls를 넘으면, 다음 초까지 대기했다가 다시 시도.
    """
    current_second = int(time.time())
    key = f"rate_limit:{current_second}"

    # transaction=False로 성능 향상
    with redis_client.pipeline(transaction=False) as pipe:
        current_count = pipe.incr(key).expire(key, 2).execute()[0]

        if current_count % 10 == 0:  # 10개 요청마다 한번만 로깅
            logger.info(
                f"Rate limit check - Current count: {current_count}/{max_calls} at {current_second}"
            )

        if current_count <= max_calls:
            return True

        time.sleep(1)
        return check_rate_limit(max_calls)


def rate_limited(max_calls: int = 500):
    """
    API 호출에 레이트 리밋을 적용하는 데코레이터

    Args:
        max_calls (int): 초당 최대 허용 호출 수

    사용예시:
    @rate_limited(max_calls=100)
    def get_character():
        return requests.get("https://api.maplestory.nexon.com/...")
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            check_rate_limit(max_calls)
            return func(*args, **kwargs)
        return wrapper
    return decorator
