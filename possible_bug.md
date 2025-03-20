# 발견된 잠재적 버그 목록

## 1. 캐시 관련 버그
- [ ] force_refresh 파라미터가 실제로 사용되지 않음
- [ ] 캐시된 데이터의 연관 데이터(popularity, stat 등) 누락시 처리 로직 부재
```python
# CharacterBasicView의 get_cached_data 메서드
def get_cached_data(self, character_name):
    one_hour_ago = timezone.now() - timedelta(hours=1)
    latest_character = CharacterBasic.objects.filter(
        character_name=character_name,
        date__gte=one_hour_ago
    ).order_by('-date').first()
```

## 2. 날짜 변환 관련 버그
- [ ] convert_to_local_time 메서드가 코드에 없음
- [ ] 날짜 변환 실패시 예외 처리가 불완전함
```python
# BaseAPIView의 convert_to_local_time 메서드 호출
local_time = self.convert_to_local_time(current_time)
```

## 3. 데이터 저장 관련 버그
- [ ] 날짜 변환 실패시 현재 시간으로 대체하여 데이터 정합성 문제 발생 가능
- [ ] 트랜잭션 처리 부재로 데이터 저장 실패시 롤백 안됨
```python
# CharacterBasicView의 save_to_database 메서드
def save_to_database(self, character_basic, ocid, popularity_data=None, stat_data=None):
    try:
        date = self.convert_to_local_time(date_str)
    except Exception as e:
        logger.error(f"날짜 변환 오류: {str(e)}")
        date = timezone.now()
```

## 4. API 응답 처리 버그
- [ ] API 응답이 None이거나 빈 데이터일 때 처리 로직 부재
- [ ] API 호출 실패시 재시도 로직 부재
```python
# CharacterHexaMatrixView의 get 메서드
hexa_data = MapleAPIService.get_character_hexamatrix(ocid, date)
validated_data = CharacterHexaMatrixSchema.model_validate(hexa_data)
```

## 5. 동시성 관련 버그
- [ ] 여러 API 순차 호출시 동시성 문제 발생 가능
- [ ] 데이터 정합성을 위한 락(lock) 메커니즘 부재
```python
# CharacterItemEquipmentView의 get 메서드
character_basic, current_time = MapleAPIService.get_character_basic(ocid, date)
equipment_data = MapleAPIService.get_character_item_equipment(ocid, date)
```

## 6. 메모리 누수 가능성
- [ ] 대량 데이터 처리시 메모리 관리 불충분
- [ ] bulk_create/bulk_update 미사용으로 성능 저하 가능성
```python
# CharacterSymbolView의 get 메서드
for symbol_item in validated_data.symbol:
    symbol = Symbol.objects.create(...)
    character_symbol_equipment.symbol.add(symbol)
```

## 7. 예외 처리 불충분
- [ ] 구체적인 예외 처리 부재로 디버깅 어려움
- [ ] 내부 에러 메시지가 사용자에게 그대로 노출될 수 있음
```python
except Exception as e:
    return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
```

## 8. 보안 관련 버그
- [ ] API 키가 로그에 노출될 수 있음
- [ ] 요청 검증이나 rate limiting 부재
```python
# API 키 노출
headers = {
    "accept": "application/json",
    "x-nxopen-api-key": APIKEY
}
```

## 개선 제안
- [ ] 트랜잭션 처리 추가
- [ ] 구체적인 예외 클래스 정의 및 처리
- [ ] API 재시도 로직 구현
- [ ] 데이터 정합성 검증 강화
- [ ] 캐시 처리 로직 개선
- [ ] bulk 연산 사용으로 성능 최적화
- [ ] 동시성 제어 메커니즘 추가
- [ ] 보안 강화 (API 키 관리, 요청 검증 등) 