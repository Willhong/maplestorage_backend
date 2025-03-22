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
    while True:
        current_second = int(time.time())
        key = f"rate_limit:{current_second}"

        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, 2)  # 2초 후 만료 (안전장치)
        current_count = pipe.execute()[0]  # INCR 결과값(현재 카운트)

        if current_count <= max_calls:
            logger.info(
                f"Rate limit check - Current count: {current_count}/{max_calls} at {current_second}"
            )
            return True

        # 초과 시 -> 다음 초까지 대기 (혹은 정확히 남은 시간 계산)
        logger.warning(
            f"Rate limit exceeded. Waiting 1 second."
        )
        time.sleep(1)
        # 다시 while 루프 반복, current_second가 바뀌어서 새로운 키가 생성되고
        # 카운터가 1부터 다시 시작됨


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
