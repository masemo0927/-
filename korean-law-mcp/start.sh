#!/bin/bash
# korean-law-mcp 개인 전용 시작 스크립트 (leeseungback_0927)
set -e
cd "$(dirname "$0")"

# node_modules 없으면 설치
if [ ! -d "node_modules" ]; then
  npm install --silent
fi

# 빌드 없으면 빌드
if [ ! -f "build/index.js" ]; then
  npm run build --silent
fi

exec node build/index.js
