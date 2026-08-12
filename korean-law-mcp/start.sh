#!/bin/bash
# korean-law-mcp 자동 빌드 후 실행
cd "$(dirname "$0")"
if [ ! -f "build/index.js" ]; then
  npm install --silent 2>/dev/null
  npm run build --silent 2>/dev/null
fi
exec node build/index.js
