#!/bin/bash
# ======================================
# 세종시설관리공단 법령분석 앱 로컬 실행
# ======================================

echo "=== 법령분석 앱 로컬 실행 스크립트 ==="

# 1. Python 버전 확인
python3 --version || { echo "Python3 설치 필요"; exit 1; }

# 2. 의존성 설치
echo "[1/3] 패키지 설치 중..."
pip install flask python-dotenv requests 2>/dev/null | tail -3

# 3. .env 파일 생성 (없는 경우)
if [ ! -f .env ]; then
    echo "[2/3] .env 파일 생성..."
    echo "LAW_OC=leeseungback_0927" > .env
    echo ".env 생성 완료: LAW_OC=leeseungback_0927"
else
    echo "[2/3] .env 파일 확인: $(cat .env)"
fi

# 4. 프록시 환경변수 해제 (로컬에서는 불필요)
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY

# 5. 앱 실행
echo "[3/3] 앱 시작..."
echo "브라우저에서 http://localhost:5000 접속하세요"
echo ""
python3 app.py
