# 1. 사용자 등록
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/register/" -Method Post -ContentType "application/json" -Body '{"username":"testuser3","password":"Test1234!","password2":"Test1234!","email":"test3@example.com","first_name":"Test","last_name":"User"}'

# 2. 로그인 및 JWT 토큰 발급
$token = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/token/" -Method Post -ContentType "application/json" -Body '{"username":"testuser3","password":"Test1234!"}'

# 3. 토큰 정보 확인
$token | Format-List

# 4. 인증이 필요한 엔드포인트 접근 (access 토큰 사용)
Invoke-RestMethod -Uri "http://127.0.0.1:8000/accounts/" -Method Get -Headers @{"Authorization" = "Bearer " + $token.access}

# 5. 토큰 갱신 (refresh 토큰 사용)
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/token/refresh/" -Method Post -ContentType "application/json" -Body "{`"refresh`":`"$($token.refresh)`"}"

# 6. 토큰 검증
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/token/verify/" -Method Post -ContentType "application/json" -Body "{`"token`":`"$($token.access)`"}"
